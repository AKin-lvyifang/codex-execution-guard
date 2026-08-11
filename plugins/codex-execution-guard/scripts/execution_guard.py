#!/usr/bin/env python3
"""Stateful, opt-in lifecycle guard for approved Codex execution contracts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from contract_protocol import (
    ContractProtocolError,
    MARKER,
    canonical_json_bytes,
    load_active_ownership,
    load_contract_artifact,
    reference_digest,
)

MARKER_PATTERN = re.compile(rf"(?m)^{re.escape(MARKER)}\r?$")
STATE_VERSION = 1
VALID_STATUSES = {"pending", "in_progress", "completed"}
CONTROL_PREFIX = "execution_guard:"
VALIDATION_PATTERN = re.compile(
    r"(^|[\s/&|;])(pytest|unittest|npm\s+(run\s+)?test|pnpm\s+(run\s+)?test|"
    r"yarn\s+test|cargo\s+test|go\s+test|swift\s+test|[\w./-]*(validate|check|lint)[\w./-]*)\b",
    re.IGNORECASE,
)
REMOTE_ACTION_PATTERN = re.compile(
    r"(^|[\s;&|])(git\s+(push|pull|fetch|tag)\b|gh\s+(pr|release)\b)",
    re.IGNORECASE,
)
GIT_ENV_MUTATION_PATTERN = re.compile(
    r"(^|[\s;&|])git\s+(?:worktree\s+add|switch|checkout)\b",
    re.IGNORECASE,
)
BOOTSTRAP_COMMANDS = (
    re.compile(r"^pwd$"),
    re.compile(r"^git\s+worktree\s+list(?:\s+--porcelain)?$"),
    re.compile(r"^git\s+branch\s+--show-current$"),
    re.compile(r"^git\s+rev-parse\s+(?:HEAD|--show-toplevel)$"),
    re.compile(r"^git\s+status(?:\s+--short)?(?:\s+--branch)?$"),
    re.compile(r"^git\s+status\s+--porcelain(?:=v1)?$"),
)


class GuardError(Exception):
    """A contract or local-state error that needs a concrete recovery action."""


def emit(payload: dict[str, Any] | None = None) -> None:
    if payload:
        json.dump(payload, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")


def block_pre_tool(reason: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def context(event: str, message: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": message,
            }
        }
    )


def safe_session_name(session_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)
    if not cleaned:
        raise GuardError("The hook input has no usable session_id.")
    return cleaned


def state_path(event: dict[str, Any]) -> Path | None:
    session_id = event.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise GuardError("The hook input is missing session_id.")
    data_root = os.environ.get("PLUGIN_DATA")
    if not data_root:
        return None
    return Path(data_root) / "sessions" / f"{safe_session_name(session_id)}.json"


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardError(f"Guard state is unreadable at {path}; repair or remove this session state: {exc}") from exc
    if not isinstance(state, dict) or state.get("state_version") != STATE_VERSION:
        raise GuardError(f"Guard state at {path} has an unsupported version; repair or remove this session state.")
    return state


def atomic_write(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def contract_marker(prompt: str) -> re.Match[str] | None:
    return MARKER_PATTERN.search(prompt)


def parse_contract(
    prompt: str,
    *,
    event: dict[str, Any] | None = None,
    data_root: Path | None = None,
) -> dict[str, Any] | None:
    marker = contract_marker(prompt)
    if marker is None:
        return None
    try:
        digest = reference_digest(prompt, marker_end=marker.end())
    except ContractProtocolError as exc:
        raise GuardError(str(exc)) from exc
    object_at = prompt.find("{", marker.end())
    if digest is not None and object_at >= 0:
        raise GuardError("Execution contract prompt cannot contain both a private reference and inline JSON.")
    if digest is not None:
        if event is None or data_root is None:
            raise GuardError(
                "Execution contract reference requires the target session and its private PLUGIN_DATA."
            )
        try:
            artifact = load_contract_artifact(data_root, digest)
        except ContractProtocolError as exc:
            raise GuardError(str(exc)) from exc
        contract = artifact["contract"]
        validate_contract(contract)
        validate_reference_binding(artifact, event, data_root)
        return contract
    if object_at < 0:
        raise GuardError(
            f"{MARKER} must be followed by one valid private reference or a JSON contract object."
        )
    try:
        contract, _ = json.JSONDecoder().raw_decode(prompt[object_at:])
    except json.JSONDecodeError as exc:
        raise GuardError(f"The execution contract JSON is invalid: {exc}") from exc
    validate_contract(contract)
    return contract


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GuardError(f"Contract field '{field}' must be a non-empty string.")
    return value


def require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise GuardError(f"Contract field '{field}' must be an array of non-empty strings.")
    return value


def validate_items(items: Any, field: str, text_field: str) -> None:
    if not isinstance(items, list) or not items:
        raise GuardError(f"Contract field '{field}' must be a non-empty array.")
    seen: set[str] = set()
    in_progress = 0
    for item in items:
        if not isinstance(item, dict):
            raise GuardError(f"Each '{field}' item must be an object.")
        item_id = require_string(item.get("id"), f"{field}.id")
        require_string(item.get(text_field), f"{field}.{text_field}")
        status = item.get("status")
        if status not in VALID_STATUSES:
            raise GuardError(f"Contract item '{item_id}' has an invalid status.")
        if item_id in seen:
            raise GuardError(f"Contract field '{field}' repeats stable ID '{item_id}'.")
        seen.add(item_id)
        in_progress += status == "in_progress"
    if in_progress > 1:
        raise GuardError(f"Contract field '{field}' has more than one in_progress item.")


def validate_contract(contract: Any) -> None:
    if not isinstance(contract, dict):
        raise GuardError("The execution contract must be a JSON object.")
    if contract.get("contract_version") != 1:
        raise GuardError("Only contract_version 1 is supported.")
    require_string(contract.get("contract_id"), "contract_id")
    if contract.get("role") != "execution":
        raise GuardError("This Hook accepts only role 'execution'.")
    require_string(contract.get("goal"), "goal")
    for field in (
        "scope",
        "decisions",
        "non_goals",
        "forbidden_operations",
        "authorized_models",
        "allowed_adjustments",
        "escalation_conditions",
    ):
        require_string_list(contract.get(field), field)
    selected = require_string(contract.get("selected_model"), "selected_model")
    if selected not in contract["authorized_models"]:
        raise GuardError("selected_model is outside authorized_models.")
    require_string(contract.get("route_reason"), "route_reason")
    baseline = contract.get("baseline")
    if not isinstance(baseline, dict):
        raise GuardError("Contract field 'baseline' must be an object.")
    for field in ("worktree", "branch", "head"):
        require_string(baseline.get(field), f"baseline.{field}")
    if not os.path.isabs(baseline["worktree"]):
        raise GuardError("Contract field 'baseline.worktree' must be absolute.")
    if not isinstance(baseline.get("require_clean"), bool):
        raise GuardError("Contract field 'baseline.require_clean' must be boolean.")
    validate_items(contract.get("plan"), "plan", "step")
    validate_items(contract.get("acceptance"), "acceptance", "criterion")
    budget = contract.get("validation_budget")
    if not isinstance(budget, dict):
        raise GuardError("Contract field 'validation_budget' must be an object.")
    require_string_list(budget.get("development"), "validation_budget.development")
    require_string_list(budget.get("final"), "validation_budget.final")


def new_state(event: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "state_version": STATE_VERSION,
        "active": True,
        "session_id": event["session_id"],
        "contract": contract,
        "plan": [dict(item) for item in contract["plan"]],
        "acceptance": [dict(item) for item in contract["acceptance"]],
        "environment_verified": False,
        "plan_registered": False,
        "git": None,
        "evidence": [],
        "deviations": [],
        "escalation": None,
        "last_event": "UserPromptSubmit",
    }


def run_git(cwd: str, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown Git error"
        raise GuardError(f"Git {' '.join(args)} failed: {detail}")
    return completed.stdout.rstrip("\n")


def git_identity(cwd: str) -> dict[str, Any]:
    root = run_git(cwd, "rev-parse", "--show-toplevel")
    return {
        "worktree": str(Path(root).resolve()),
        "branch": run_git(cwd, "branch", "--show-current"),
        "head": run_git(cwd, "rev-parse", "HEAD"),
        "status": run_git(cwd, "status", "--porcelain=v1"),
    }


def verify_baseline(state: dict[str, Any], cwd: str) -> dict[str, Any]:
    actual = git_identity(cwd)
    expected = state["contract"]["baseline"]
    failures: list[str] = []
    if actual["worktree"] != str(Path(expected["worktree"]).resolve()):
        failures.append(f"worktree expected {expected['worktree']!r}, got {actual['worktree']!r}")
    if actual["branch"] != expected["branch"]:
        failures.append(f"branch expected {expected['branch']!r}, got {actual['branch']!r}")
    if actual["head"] != expected["head"]:
        failures.append(f"HEAD expected {expected['head']!r}, got {actual['head']!r}")
    if expected["require_clean"] and actual["status"]:
        failures.append("worktree must be clean before execution")
    if failures:
        raise GuardError("Environment verification failed: " + "; ".join(failures))
    return actual


def validate_reference_binding(
    artifact: dict[str, Any],
    event: dict[str, Any],
    data_root: Path,
) -> None:
    session_id = event.get("session_id")
    if not isinstance(session_id, str) or session_id != artifact["target_session_id"]:
        raise GuardError("Execution contract reference is bound to a different target session.")
    ownership = artifact["ownership"]
    if artifact["target_session_id"] != ownership["thread_id"]:
        raise GuardError("Execution contract reference target does not match native thread ownership.")
    event_host = event.get("host_id")
    if event_host is not None and event_host != ownership["host_id"]:
        raise GuardError("Execution contract reference is bound to a different host.")
    contract = artifact["contract"]
    if artifact["contract_id"] != ownership["iteration_id"]:
        raise GuardError("Execution contract ID does not match active iteration ownership.")
    try:
        active = load_active_ownership(data_root, artifact["contract_id"])
    except ContractProtocolError as exc:
        raise GuardError(str(exc)) from exc
    if active != ownership:
        raise GuardError("Execution contract ownership changed after the private artifact was staged.")
    baseline = contract["baseline"]
    if (
        str(Path(baseline["worktree"]).resolve()) != ownership["worktree"]
        or baseline["branch"] != ownership["branch"]
        or baseline["head"].lower() != ownership["baseline"]
    ):
        raise GuardError("Execution contract baseline does not match active iteration ownership.")
    verify_baseline({"contract": contract}, event["cwd"])


def verify_execution_location(state: dict[str, Any], cwd: str) -> None:
    expected = state["contract"]["baseline"]
    actual_root = str(Path(run_git(cwd, "rev-parse", "--show-toplevel")).resolve())
    actual_branch = run_git(cwd, "branch", "--show-current")
    if actual_root != str(Path(expected["worktree"]).resolve()) or actual_branch != expected["branch"]:
        raise GuardError(
            "Execution environment drifted from the approved location: "
            f"expected worktree={expected['worktree']!r}, branch={expected['branch']!r}; "
            f"got worktree={actual_root!r}, branch={actual_branch!r}. Return to the control task."
        )


def validate_plan_update(state: dict[str, Any], tool_input: Any) -> list[dict[str, str]]:
    if not isinstance(tool_input, dict) or not isinstance(tool_input.get("plan"), list):
        raise GuardError("update_plan must include the complete approved plan array.")
    proposed = tool_input["plan"]
    approved = state["contract"]["plan"]
    if len(proposed) != len(approved):
        raise GuardError("Plan update changed the approved step count; return to the control task.")
    normalized: list[dict[str, str]] = []
    in_progress = 0
    for index, (candidate, original) in enumerate(zip(proposed, approved)):
        if not isinstance(candidate, dict):
            raise GuardError(f"Plan item {index + 1} must be an object.")
        if candidate.get("step") != original["step"]:
            raise GuardError(
                f"Plan item {index + 1} changed stable ID or approved text; return to the control task."
            )
        status = candidate.get("status")
        if status not in VALID_STATUSES:
            raise GuardError(f"Plan item {original['id']} has an invalid status.")
        prior = state["plan"][index]["status"]
        if prior == "completed" and status != "completed":
            raise GuardError(f"Completed plan item {original['id']} cannot be reopened without control-task approval.")
        in_progress += status == "in_progress"
        normalized.append({"id": original["id"], "step": original["step"], "status": status})
    if in_progress > 1:
        raise GuardError("Plan update has more than one in_progress item.")
    parse_control(tool_input.get("explanation"), state, apply=False)
    return normalized


def parse_control(explanation: Any, state: dict[str, Any], *, apply: bool) -> None:
    if explanation is None or not isinstance(explanation, str):
        return
    stripped = explanation.strip()
    if not stripped.startswith(CONTROL_PREFIX):
        return
    try:
        control = json.loads(stripped[len(CONTROL_PREFIX) :].strip())
    except json.JSONDecodeError as exc:
        raise GuardError(f"The execution_guard control line is invalid JSON: {exc}") from exc
    if not isinstance(control, dict):
        raise GuardError("The execution_guard control value must be an object.")
    allowed = {"acceptance_complete", "evidence", "implementation_note", "deviation", "escalation"}
    unknown = sorted(set(control) - allowed)
    if unknown:
        raise GuardError(f"Unknown execution_guard control fields: {', '.join(unknown)}")
    completed = control.get("acceptance_complete", [])
    if not isinstance(completed, list) or any(not isinstance(item, str) for item in completed):
        raise GuardError("acceptance_complete must be an array of stable IDs.")
    known = {item["id"] for item in state["acceptance"]}
    unknown_ids = [item for item in completed if item not in known]
    if unknown_ids:
        raise GuardError(
            "Unapproved acceptance IDs require control-task approval: " + ", ".join(unknown_ids)
        )
    for field in ("evidence", "implementation_note", "deviation"):
        value = control.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise GuardError(f"Control field '{field}' must be a non-empty string when present.")
    if completed and not isinstance(control.get("evidence"), str):
        raise GuardError("Completing acceptance IDs requires non-empty evidence.")
    escalation = control.get("escalation")
    if escalation is not None:
        if not isinstance(escalation, dict) or set(escalation) != {"reason", "evidence"}:
            raise GuardError("Control field 'escalation' must contain exactly reason and evidence.")
        for field in ("reason", "evidence"):
            if not isinstance(escalation.get(field), str) or not escalation[field].strip():
                raise GuardError(f"Escalation field '{field}' must be a non-empty string.")
    if not apply:
        return
    for item in state["acceptance"]:
        if item["id"] in completed:
            item["status"] = "completed"
    if control.get("deviation") and control["deviation"] not in state["deviations"]:
        state["deviations"].append(control["deviation"])
    if escalation is not None:
        state["escalation"] = dict(escalation)
        record = {
            "kind": "escalation",
            "reason": escalation["reason"],
            "outcome": escalation["evidence"],
        }
        if record not in state["evidence"]:
            state["evidence"].append(record)
    if control.get("evidence"):
        record = {
            "kind": "acceptance",
            "acceptance": completed,
            "outcome": control["evidence"],
        }
        if record not in state["evidence"]:
            state["evidence"].append(record)


def is_bootstrap_command(command: str) -> bool:
    segments = [
        segment.strip()
        for line in command.splitlines()
        for segment in line.split(";")
        if segment.strip()
    ]
    return bool(segments) and all(
        any(pattern.fullmatch(segment) for pattern in BOOTSTRAP_COMMANDS)
        for segment in segments
    )


def is_write_tool(tool_name: str, tool_input: Any) -> bool:
    if tool_name in {"apply_patch", "Edit", "Write"}:
        return True
    if tool_name == "Bash" and isinstance(tool_input, dict):
        command = tool_input.get("command")
        return isinstance(command, str) and not is_bootstrap_command(command)
    return False


def changed_paths(status: str) -> list[str]:
    paths: list[str] = []
    for line in status.splitlines():
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and path not in paths:
            paths.append(path)
    return paths


def execution_changes(state: dict[str, Any], cwd: str, actual: dict[str, Any]) -> tuple[list[str], list[str]]:
    baseline_head = state["contract"]["baseline"]["head"]
    committed_paths = run_git(cwd, "diff", "--name-only", f"{baseline_head}..{actual['head']}").splitlines()
    paths = list(dict.fromkeys([*committed_paths, *changed_paths(actual["status"])]))
    commits = run_git(cwd, "rev-list", "--reverse", f"{baseline_head}..{actual['head']}").splitlines()
    return paths, commits


def current_step(state: dict[str, Any]) -> str | None:
    for status in ("in_progress", "pending"):
        for item in state["plan"]:
            if item["status"] == status:
                return item["id"]
    return None


def response_outcome(response: Any) -> str:
    if isinstance(response, dict):
        exit_code = response.get("exit_code")
        if isinstance(exit_code, int):
            return "passed" if exit_code == 0 else "failed"
    text = json.dumps(response, sort_keys=True) if not isinstance(response, str) else response
    nonzero = re.search(r"(?:exit code|returncode)[^0-9-]*(-?\d+)", text, re.IGNORECASE)
    if nonzero:
        return "passed" if int(nonzero.group(1)) == 0 else "failed"
    return "completed"


def record_validation(state: dict[str, Any], event: dict[str, Any]) -> bool:
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict) or not isinstance(tool_input.get("command"), str):
        return False
    command = tool_input["command"].strip()
    if not VALIDATION_PATTERN.search(command):
        return False
    actual = git_identity(event["cwd"])
    record = {
        "kind": "validation",
        "command": command,
        "outcome": response_outcome(event.get("tool_response")),
        "head": actual["head"],
        "changed_paths": changed_paths(actual["status"]),
        "current_step": current_step(state),
        "acceptance": [item["id"] for item in state["acceptance"] if item["status"] == "completed"],
    }
    identity_fields = ("command", "outcome", "head", "changed_paths", "current_step", "acceptance")
    duplicate = any(
        existing.get("kind") == "validation"
        and all(existing.get(field) == record.get(field) for field in identity_fields)
        for existing in state["evidence"]
    )
    if not duplicate:
        state["evidence"].append(record)
        state["evidence"] = state["evidence"][-20:]
    return duplicate


def complete(state: dict[str, Any]) -> bool:
    return all(item["status"] == "completed" for item in state["plan"]) and all(
        item["status"] == "completed" for item in state["acceptance"]
    )


def receipt(state: dict[str, Any], cwd: str) -> str:
    verify_execution_location(state, cwd)
    actual = git_identity(cwd)
    paths, commits = execution_changes(state, cwd, actual)
    plan_ids = ", ".join(item["id"] for item in state["plan"] if item["status"] == "completed")
    acceptance_ids = ", ".join(
        item["id"] for item in state["acceptance"] if item["status"] == "completed"
    )
    validation = [
        f"{item['command']} ({item['outcome']})"
        for item in state["evidence"]
        if item.get("kind") == "validation"
    ]
    return (
        "Execution Guard contract is complete. Deliver an execution receipt with "
        f"contract {state['contract']['contract_id']}; completed plan [{plan_ids}]; "
        f"completed acceptance [{acceptance_ids}]; changed paths {paths}; "
        f"local commits {commits}; current HEAD {actual['head']}; validations {validation}; "
        f"deviations {state['deviations']}; "
        "explicitly unverified host checks; and confirmation that no unauthorized remote or release action occurred."
    )


def escalation_receipt(state: dict[str, Any]) -> str:
    incomplete_plan = [item["id"] for item in state["plan"] if item["status"] != "completed"]
    incomplete_acceptance = [item["id"] for item in state["acceptance"] if item["status"] != "completed"]
    escalation = state["escalation"]
    return (
        "Execution Guard escalation is registered. Return to the control task with "
        f"contract {state['contract']['contract_id']}; incomplete plan {incomplete_plan}; "
        f"incomplete acceptance {incomplete_acceptance}; blocker {escalation['reason']}; "
        f"evidence {escalation['evidence']}; and no claim of completion."
    )


def exact_json(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def activation_context(state: dict[str, Any]) -> str:
    contract = state["contract"]
    return (
        f"Execution Guard activated contract {contract['contract_id']}. "
        f"Route: {contract['selected_model']} ({contract['route_reason']}).\n"
        f"Exact contract JSON: {exact_json(contract)}\n"
        f"Exact current plan JSON: {exact_json(state['plan'])}\n"
        f"Exact current acceptance JSON: {exact_json(state['acceptance'])}\n"
        "Verify worktree, branch, HEAD, and status; then register the exact approved plan "
        "with update_plan before any write."
    )


def concise_restore(state: dict[str, Any], cwd: str) -> str:
    actual = git_identity(cwd)
    contract = state["contract"]
    plan = ", ".join(f"{item['id']}={item['status']}" for item in state["plan"])
    acceptance = ", ".join(f"{item['id']}={item['status']}" for item in state["acceptance"])
    evidence = []
    for item in state["evidence"][-8:]:
        label = item.get("command") or item.get("acceptance") or item.get("reason") or item.get("kind")
        evidence.append(f"{label}: {item.get('outcome')}")
    restored = (
        f"Execution Guard restored contract {contract['contract_id']}: {contract['goal']}\n"
        f"Selected model: {contract['selected_model']} ({contract['route_reason']})\n"
        f"Scope: {exact_json(contract['scope'])}\n"
        f"Decisions: {exact_json(contract['decisions'])}\n"
        f"Non-goals: {exact_json(contract['non_goals'])}\n"
        f"Forbidden operations: {exact_json(contract['forbidden_operations'])}\n"
        f"Authorized models: {exact_json(contract['authorized_models'])}\n"
        f"Allowed adjustments: {exact_json(contract['allowed_adjustments'])}\n"
        f"Escalation conditions: {exact_json(contract['escalation_conditions'])}\n"
        f"Validation budget: {exact_json(contract['validation_budget'])}\n"
        f"Plan: {plan}; current step: {current_step(state) or 'none'}\n"
        f"Exact plan: {exact_json(state['plan'])}\n"
        f"Acceptance: {acceptance}\n"
        f"Exact acceptance: {exact_json(state['acceptance'])}\n"
        f"Baseline: {exact_json(state['contract']['baseline'])}\n"
        f"Current Git: worktree={actual['worktree']}, branch={actual['branch']}, HEAD={actual['head']}, "
        f"changed_paths={changed_paths(actual['status'])}\n"
        f"Escalation: {exact_json(state.get('escalation'))}\n"
        f"Evidence summary: {evidence}\n"
        f"Exact evidence: {exact_json(state['evidence'])}; deviations: {exact_json(state['deviations'])}\n"
        f"Exact contract JSON: {exact_json(contract)}\n"
        "Re-check Git identity, preserve the exact approved plan, and continue only the current approved step."
    )
    return restored


def on_user_prompt(event: dict[str, Any], path: Path, state: dict[str, Any] | None) -> None:
    prompt = event.get("prompt")
    if not isinstance(prompt, str):
        raise GuardError("UserPromptSubmit is missing prompt text.")
    contract = parse_contract(prompt, event=event, data_root=path.parent.parent)
    if contract is None:
        if state:
            context("UserPromptSubmit", f"Execution Guard remains active for {state['contract']['contract_id']}.")
        return
    if state:
        if state["contract"] != contract:
            emit({"decision": "block", "reason": "A different execution contract is already active in this session."})
            return
    else:
        state = new_state(event, contract)
        atomic_write(path, state)
    context("UserPromptSubmit", activation_context(state))


def on_pre_tool(event: dict[str, Any], state: dict[str, Any]) -> None:
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if state.get("escalation") is not None and (tool_name == "update_plan" or is_write_tool(str(tool_name), tool_input)):
        block_pre_tool("An escalation is already registered; return the recorded blocker to the control task.")
        return
    if tool_name in {"Agent", "spawn_agent", "create_thread", "fork_thread"}:
        block_pre_tool("This guarded iteration already has its unique execution task; return new work to the control task.")
        return
    if tool_name == "update_plan":
        try:
            validate_plan_update(state, tool_input)
            if not state["environment_verified"]:
                verify_baseline(state, event["cwd"])
            else:
                verify_execution_location(state, event["cwd"])
        except GuardError as exc:
            block_pre_tool(str(exc))
        return
    if not state["plan_registered"] or not state["environment_verified"]:
        if is_write_tool(str(tool_name), tool_input):
            block_pre_tool(
                "Guarded writes are disabled until the Git baseline is verified and the exact approved plan is registered."
            )
        return
    if is_write_tool(str(tool_name), tool_input):
        try:
            verify_execution_location(state, event["cwd"])
        except GuardError as exc:
            block_pre_tool(str(exc))
            return
    if tool_name == "Bash" and isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            if GIT_ENV_MUTATION_PATTERN.search(command):
                block_pre_tool("Changing branch or adding another worktree is outside the approved execution environment.")
            elif REMOTE_ACTION_PATTERN.search(command):
                block_pre_tool("Remote Git, PR, tag, and release actions are outside the guarded execution contract.")


def on_post_tool(event: dict[str, Any], path: Path, state: dict[str, Any]) -> None:
    tool_name = event.get("tool_name")
    if tool_name == "update_plan":
        normalized = validate_plan_update(state, event.get("tool_input"))
        if not state["environment_verified"]:
            state["git"] = verify_baseline(state, event["cwd"])
            state["environment_verified"] = True
        state["plan"] = normalized
        state["plan_registered"] = True
        parse_control(event.get("tool_input", {}).get("explanation"), state, apply=True)
        state["last_event"] = "PostToolUse:update_plan"
        atomic_write(path, state)
        if state.get("escalation") is not None:
            context("PostToolUse", escalation_receipt(state))
        elif complete(state):
            context("PostToolUse", receipt(state, event["cwd"]))
        else:
            context(
                "PostToolUse",
                f"Execution Guard accepted the exact plan. Current approved step: {current_step(state)}.",
            )
        return
    if tool_name == "Bash" and state["plan_registered"]:
        duplicate = record_validation(state, event)
        state["last_event"] = "PostToolUse:Bash"
        atomic_write(path, state)
        if duplicate:
            context(
                "PostToolUse",
                "This validation repeated with unchanged Git and acceptance state; it is not new progress.",
            )


def main() -> int:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise GuardError("Hook input must be a JSON object.")
        event_name = event.get("hook_event_name")
        path = state_path(event)
        if path is None:
            prompt = event.get("prompt")
            if event_name == "UserPromptSubmit" and isinstance(prompt, str) and contract_marker(prompt):
                parse_contract(prompt)
                emit(
                    {
                        "decision": "block",
                        "reason": "A valid execution contract cannot activate because PLUGIN_DATA is unavailable; "
                        "review the plugin installation and Hook trust state.",
                    }
                )
            return 0
        try:
            state = load_state(path)
        except GuardError as exc:
            if event_name == "PreToolUse":
                tool_name = str(event.get("tool_name"))
                if is_write_tool(tool_name, event.get("tool_input")) or tool_name == "update_plan":
                    block_pre_tool(str(exc))
                return 0
            if event_name == "Stop":
                emit({"decision": "block", "reason": str(exc)})
                return 0
            if event_name == "SessionStart":
                context("SessionStart", str(exc))
                return 0
            raise

        if event_name == "UserPromptSubmit":
            on_user_prompt(event, path, state)
            return 0
        if state is None or not state.get("active"):
            return 0
        if event_name == "PreToolUse":
            on_pre_tool(event, state)
        elif event_name == "PostToolUse":
            on_post_tool(event, path, state)
        elif event_name == "PreCompact":
            state["git"] = git_identity(event["cwd"])
            state["last_event"] = "PreCompact"
            atomic_write(path, state)
        elif event_name == "SessionStart":
            state["git"] = git_identity(event["cwd"])
            state["last_event"] = f"SessionStart:{event.get('source')}"
            atomic_write(path, state)
            context("SessionStart", concise_restore(state, event["cwd"]))
        elif event_name == "Stop":
            if state.get("escalation") is not None:
                emit({"continue": True, "systemMessage": escalation_receipt(state)})
            elif complete(state):
                emit({"continue": True, "systemMessage": receipt(state, event["cwd"])})
            else:
                incomplete_plan = [item["id"] for item in state["plan"] if item["status"] != "completed"]
                incomplete_acceptance = [
                    item["id"] for item in state["acceptance"] if item["status"] != "completed"
                ]
                emit(
                    {
                        "decision": "block",
                        "reason": "Execution contract remains incomplete. Continue approved work only: "
                        f"plan={incomplete_plan}, acceptance={incomplete_acceptance}.",
                    }
                )
        return 0
    except GuardError as exc:
        event_name = locals().get("event_name")
        if event_name == "PreToolUse":
            block_pre_tool(str(exc))
            return 0
        if event_name in {"UserPromptSubmit", "Stop"}:
            emit({"decision": "block", "reason": str(exc)})
            return 0
        emit({"continue": True, "systemMessage": str(exc)})
        return 0
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        emit({"continue": True, "systemMessage": f"Execution Guard hook failed locally: {exc}"})
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
