#!/usr/bin/env python3
"""Deterministic local control-plane helpers for Codex Execution Guard."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from contract_protocol import (
    ContractProtocolError,
    registry_path as plugin_registry_path,
    render_folded_inline_fallback,
    render_reference_prompt,
    stage_contract_artifact,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    fcntl = None  # type: ignore[assignment]


LEGACY_REGISTRY_VERSION = 1
REGISTRY_VERSION = 2
CLAIMED = "claimed"
ACTIVE = "active"
CLOSED = "closed"
VALID_STATUSES = {CLAIMED, ACTIVE, CLOSED}
CLAIM_FIELDS = {
    "iteration_id",
    "project_id",
    "title",
    "status",
}
OWNERSHIP_FIELDS = {
    "host_id",
    "thread_id",
    "worktree",
    "branch",
    "baseline",
}
REQUIRED_OWNERSHIP_FIELDS = OWNERSHIP_FIELDS - {"host_id"}
RECORD_FIELDS = CLAIM_FIELDS | OWNERSHIP_FIELDS
MUTABLE_FIELDS = {
    "project_id",
    "host_id",
    "thread_id",
    "title",
    "worktree",
    "branch",
    "baseline",
}
GIT_HEAD_PATTERN = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
SAME_ITERATION_RELATIONS = {
    "same-contract",
    "fix",
    "adjustment",
    "test",
    "documentation",
    "new-acceptance",
    "acceptance-detail",
    "retry",
    "optimization",
    "failed-acceptance-fix",
}
NEW_ITERATION_RELATIONS = {"independent-value"}
OWNERSHIP_CLOSE_OUTCOMES = {"merged", "cancelled"}
TASK_SHAPE_CANDIDATES = {
    "mechanical": (
        "gpt-5.6-luna/max",
        "gpt-5.6-terra/max",
        "gpt-5.6-sol/high",
    ),
    "normal": (
        "gpt-5.6-terra/max",
        "gpt-5.6-sol/high",
        "gpt-5.6-luna/max",
    ),
    "frozen-cross-module": (
        "gpt-5.6-sol/high",
        "gpt-5.6-terra/max",
        "gpt-5.6-sol/xhigh",
    ),
    "ambiguous": ("gpt-5.6-sol/ultra",),
    "high-risk-review": ("gpt-5.6-sol/xhigh", "gpt-5.6-sol/ultra"),
}


class ControlPlaneError(Exception):
    """A local control-plane error that must stop task orchestration."""


def decide_task(relation: str, iteration_status: str) -> str:
    """Return create, reuse, or stop from frozen ownership evidence."""
    relation = require_string(relation, "relation")
    iteration_status = require_string(iteration_status, "iteration_status")
    if relation == "ambiguous":
        return "stop"
    if relation in NEW_ITERATION_RELATIONS:
        return "create"
    if relation in SAME_ITERATION_RELATIONS:
        if iteration_status == ACTIVE:
            return "reuse"
        if iteration_status in {CLOSED, *OWNERSHIP_CLOSE_OUTCOMES, "missing"}:
            return "create"
    return "stop"


def route_model(
    task_shape: str,
    authorized_models: list[str],
    *,
    host_available: list[str] | None,
    actual_model: str | None = None,
) -> dict[str, Any]:
    """Select a requested profile without claiming unreported runtime identity."""
    task_shape = require_string(task_shape, "task_shape")
    candidates = TASK_SHAPE_CANDIDATES.get(task_shape)
    if candidates is None:
        raise ControlPlaneError(f"Unknown task shape {task_shape!r}; keep the decision in control.")
    if not authorized_models or any(
        not isinstance(model, str) or not model.strip() for model in authorized_models
    ):
        raise ControlPlaneError("authorized_models must contain non-empty model profiles.")
    authorized = set(authorized_models)
    if host_available is None:
        selectable = authorized
        evidence_source = "local authorized-pool fallback; not live host discovery"
    else:
        if any(not isinstance(model, str) or not model.strip() for model in host_available):
            raise ControlPlaneError("host_available must contain non-empty model profiles.")
        selectable = authorized.intersection(host_available)
        evidence_source = "live host-advertised intersection"
    selected = next((candidate for candidate in candidates if candidate in selectable), None)
    if selected is None:
        raise ControlPlaneError(
            f"No authorized available model matches task shape {task_shape!r}; stop in control."
        )
    if actual_model is not None:
        require_string(actual_model, "actual_model")
        if actual_model not in authorized:
            raise ControlPlaneError("Host-reported actual model is outside the authorized pool.")
        actual_status = f"actual model verified: {actual_model}"
    else:
        actual_status = "actual model unverified"
    preferred = candidates[0]
    fallback = selected != preferred
    action = "control" if task_shape == "ambiguous" else "execute"
    reason = f"{task_shape}; {'fallback from ' + preferred if fallback else 'preferred profile'}"
    return {
        "action": action,
        "requested_model": selected,
        "preferred_model": preferred,
        "fallback": fallback,
        "evidence_source": evidence_source,
        "actual_model": actual_model,
        "actual_model_status": actual_status,
        "route_reason": reason,
    }


def validate_bootstrap_report(
    report: Mapping[str, Any], *, require_clean: bool = True
) -> dict[str, Any]:
    """Validate the final native-task identity and Git baseline before activation."""
    required = {
        "thread_id",
        "host_id",
        "title",
        "worktree",
        "linked_worktree",
        "branch",
        "head",
        "status",
    }
    missing = sorted(required - set(report))
    if missing:
        if "thread_id" in missing and report.get("client_thread_id"):
            raise ControlPlaneError(
                "Queued clientThreadId is not a real threadId; wait for native task readiness."
            )
        raise ControlPlaneError("Bootstrap report is missing: " + ", ".join(missing) + ".")
    thread_id = require_string(report["thread_id"], "thread_id")
    host_id = require_string(report["host_id"], "host_id")
    title = require_string(report["title"], "title")
    branch = require_string(report["branch"], "branch")
    head = require_string(report["head"], "head").lower()
    if not GIT_HEAD_PATTERN.fullmatch(head):
        raise ControlPlaneError("Bootstrap HEAD must be a full 40- or 64-character Git object ID.")
    worktree = Path(require_string(report["worktree"], "worktree"))
    if not worktree.is_absolute():
        raise ControlPlaneError("Bootstrap worktree must be absolute.")
    if report["linked_worktree"] is not True:
        raise ControlPlaneError("Bootstrap did not prove a linked worktree.")
    status = report["status"]
    if not isinstance(status, str):
        raise ControlPlaneError("Bootstrap status must be porcelain text.")
    if require_clean and status:
        raise ControlPlaneError("Bootstrap worktree must be clean before contract activation.")
    return {
        "thread_id": thread_id,
        "host_id": host_id,
        "title": title,
        "baseline": {
            "worktree": str(worktree.resolve()),
            "branch": branch,
            "head": head,
            "require_clean": require_clean,
        },
    }


def stage_contract_handoff(
    *,
    plugin_data: Path,
    registry: "IterationRegistry",
    iteration_id: str,
    target_session_id: str,
    contract: Mapping[str, Any],
) -> dict[str, str]:
    """Stage one same-host contract privately and return only its short visible handoff."""
    plugin_data = plugin_data.resolve()
    if registry.path != plugin_registry_path(plugin_data):
        raise ControlPlaneError(
            "Same-host contract references require the V2 registry at "
            "PLUGIN_DATA/control/iterations.json."
        )
    iteration_id = require_string(iteration_id, "iteration_id")
    target_session_id = require_string(target_session_id, "target_session_id")
    record = registry.reuse(iteration_id)
    if "host_id" not in record:
        raise ControlPlaneError(
            "Same-host contract references require ownership finalized with a verified host_id."
        )
    if target_session_id != record["thread_id"]:
        raise ControlPlaneError(
            "Target session does not match the active native thread ownership."
        )
    if not isinstance(contract, Mapping) or contract.get("contract_id") != iteration_id:
        raise ControlPlaneError("Contract ID does not match the active iteration ownership.")
    baseline = contract.get("baseline")
    if not isinstance(baseline, Mapping):
        raise ControlPlaneError("Contract baseline must be an object before handoff staging.")
    try:
        worktree = str(Path(require_string(baseline.get("worktree"), "baseline.worktree")).resolve())
        branch = require_string(baseline.get("branch"), "baseline.branch")
        head = require_string(baseline.get("head"), "baseline.head").lower()
    except (OSError, RuntimeError) as exc:
        raise ControlPlaneError(f"Contract baseline cannot be resolved: {exc}") from exc
    if (
        worktree != record["worktree"]
        or branch != record["branch"]
        or head != record["baseline"]
    ):
        raise ControlPlaneError(
            "Contract baseline does not match the active iteration ownership."
        )
    try:
        staged = stage_contract_artifact(
            plugin_data=plugin_data,
            contract=contract,
            target_session_id=target_session_id,
            ownership=record,
        )
        visible_goal = require_string(contract.get("goal"), "contract.goal")
        for private_worktree in {record["worktree"], str(baseline["worktree"])}:
            visible_goal = visible_goal.replace(private_worktree, "the approved worktree")
        prompt = render_reference_prompt(iteration_id, staged["digest"], visible_goal)
    except ContractProtocolError as exc:
        raise ControlPlaneError(str(exc)) from exc
    return {**staged, "prompt": prompt}


def folded_inline_handoff(contract: Mapping[str, Any]) -> str:
    """Return the explicit cross-host fallback when target PLUGIN_DATA cannot be staged."""
    try:
        return render_folded_inline_fallback(contract)
    except ContractProtocolError as exc:
        raise ControlPlaneError(str(exc)) from exc


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ControlPlaneError(f"Field '{field}' must be a non-empty string.")
    return value


def normalize_record(record: Mapping[str, Any]) -> dict[str, str]:
    unknown = sorted(set(record) - RECORD_FIELDS)
    missing = sorted(CLAIM_FIELDS - set(record))
    if unknown or missing:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        raise ControlPlaneError("Iteration record has invalid fields: " + "; ".join(details) + ".")

    normalized = {field: require_string(record[field], field) for field in record}
    if normalized["status"] not in VALID_STATUSES:
        raise ControlPlaneError("Field 'status' must be 'claimed', 'active', or 'closed'.")
    if normalized["status"] == CLAIMED:
        unexpected = sorted(set(record).intersection(OWNERSHIP_FIELDS))
        if unexpected:
            raise ControlPlaneError(
                "A claimed iteration cannot contain native task or Git ownership fields: "
                + ", ".join(unexpected)
                + "."
            )
        return normalized

    missing_ownership = sorted(REQUIRED_OWNERSHIP_FIELDS - set(record))
    if missing_ownership:
        raise ControlPlaneError(
            "Active or closed iteration record is missing "
            + ", ".join(missing_ownership)
            + "."
        )
    worktree = Path(normalized["worktree"])
    if not worktree.is_absolute():
        raise ControlPlaneError("Field 'worktree' must be an absolute path.")
    normalized["worktree"] = str(worktree.resolve())
    normalized["baseline"] = normalized["baseline"].lower()
    if not GIT_HEAD_PATTERN.fullmatch(normalized["baseline"]):
        raise ControlPlaneError("Field 'baseline' must be a full 40- or 64-character Git object ID.")
    return normalized


def empty_registry() -> dict[str, Any]:
    return {"registry_version": REGISTRY_VERSION, "iterations": {}}


def load_registry(path: Path, *, allow_missing: bool = False) -> dict[str, Any]:
    if not path.exists():
        if allow_missing:
            return empty_registry()
        raise ControlPlaneError(f"Iteration registry does not exist at {path}.")
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControlPlaneError(
            f"Iteration registry is unreadable at {path}; do not overwrite it: {exc}"
        ) from exc
    if not isinstance(registry, dict) or set(registry) != {"registry_version", "iterations"}:
        raise ControlPlaneError(f"Iteration registry at {path} has an invalid top-level shape.")
    source_version = registry["registry_version"]
    if source_version not in {LEGACY_REGISTRY_VERSION, REGISTRY_VERSION}:
        raise ControlPlaneError(
            f"Iteration registry at {path} has unsupported version {source_version!r}."
        )
    iterations = registry["iterations"]
    if not isinstance(iterations, dict):
        raise ControlPlaneError(f"Iteration registry at {path} has a non-object iterations field.")
    normalized: dict[str, dict[str, str]] = {}
    for key, value in iterations.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise ControlPlaneError(f"Iteration registry at {path} contains an invalid record entry.")
        record = normalize_record(value)
        if record["iteration_id"] != key:
            raise ControlPlaneError(
                f"Iteration registry key {key!r} conflicts with record ID {record['iteration_id']!r}."
            )
        normalized[key] = record
    if source_version == LEGACY_REGISTRY_VERSION and any(
        record["status"] == CLAIMED for record in normalized.values()
    ):
        raise ControlPlaneError(f"Legacy iteration registry at {path} contains a V2 claim record.")
    validated = {"registry_version": REGISTRY_VERSION, "iterations": normalized}
    validate_unique_ownership(validated)
    return validated


def atomic_write(path: Path, registry: Mapping[str, Any]) -> None:
    path = path.resolve()
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
            json.dump(registry, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory = None
        if directory is not None:
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def registry_lock_path(path: Path) -> Path:
    path = path.resolve()
    return path.with_name(f".{path.name}.lock")


@contextmanager
def registry_lock(path: Path) -> Iterator[None]:
    """Serialize one registry read-modify-write transaction across processes."""
    if fcntl is None:
        raise ControlPlaneError(
            "This host lacks the Python standard-library fcntl process lock; "
            "registry mutations are disabled rather than running unlocked."
        )
    lock_path = registry_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = lock_path.open("a+b")
    except OSError as exc:
        raise ControlPlaneError(f"Cannot open iteration registry lock at {lock_path}: {exc}") from exc
    with handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            raise ControlPlaneError(
                f"Cannot acquire iteration registry lock at {lock_path}: {exc}"
            ) from exc
        yield


def ownership_keys(record: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    if record["status"] == CLAIMED:
        return ()
    return (
        ("thread_id", record["thread_id"]),
        ("worktree", str(Path(record["worktree"]).resolve())),
        ("project_branch", f"{record['project_id']}\0{record['branch']}"),
    )


def validate_unique_ownership(registry: Mapping[str, Any]) -> None:
    owners: dict[tuple[str, str], str] = {}
    for iteration_id, record in registry["iterations"].items():
        for key in ownership_keys(record):
            existing = owners.get(key)
            if existing is not None and existing != iteration_id:
                label = key[0].replace("_", " ")
                raise ControlPlaneError(
                    f"Duplicate {label} ownership between iterations {existing!r} and {iteration_id!r}."
                )
            owners[key] = iteration_id


class IterationRegistry:
    def __init__(self, path: Path):
        if not path.is_absolute():
            raise ControlPlaneError("Registry path must be absolute.")
        self.path = path.resolve()

    def create(self, record: Mapping[str, Any]) -> dict[str, str]:
        """Import one already-verified active record; orchestration must claim first."""
        with registry_lock(self.path):
            normalized = normalize_record(record)
            if normalized["status"] != ACTIVE:
                raise ControlPlaneError("A new iteration record must start active.")
            registry = load_registry(self.path, allow_missing=True)
            iteration_id = normalized["iteration_id"]
            if iteration_id in registry["iterations"]:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} already exists; read or reuse it."
                )
            registry["iterations"][iteration_id] = normalized
            validate_unique_ownership(registry)
            atomic_write(self.path, registry)
            return normalized

    def claim(
        self,
        *,
        iteration_id: str,
        project_id: str,
        title: str,
    ) -> dict[str, Any]:
        """Persist the one-shot native-create claim before any host create call."""
        candidate = normalize_record(
            {
                "iteration_id": iteration_id,
                "project_id": project_id,
                "title": title,
                "status": CLAIMED,
            }
        )
        with registry_lock(self.path):
            registry = load_registry(self.path, allow_missing=True)
            current = registry["iterations"].get(candidate["iteration_id"])
            if current is None:
                registry["iterations"][candidate["iteration_id"]] = candidate
                atomic_write(self.path, registry)
                return {"action": "create_once", "record": dict(candidate)}
            for field in ("project_id", "title"):
                if current[field] != candidate[field]:
                    raise ControlPlaneError(
                        f"Iteration {candidate['iteration_id']!r} claim conflicts on {field}; "
                        "stop and reconcile the existing ownership record."
                    )
            # A later claim can never renew or re-authorize native creation. Persisting
            # the normalized registry here also performs a locked V1 -> V2 migration.
            atomic_write(self.path, registry)
            return {"action": "reconcile_only", "record": dict(current)}

    def finalize_claim(
        self,
        iteration_id: str,
        *,
        candidates: list[Mapping[str, Any]],
        require_clean: bool = True,
    ) -> dict[str, str]:
        """Atomically bind one claimed iteration to exactly one verified native task."""
        iteration_id = require_string(iteration_id, "iteration_id")
        if not isinstance(candidates, list):
            raise ControlPlaneError("Reconciliation candidates must be an array of bootstrap reports.")
        if len(candidates) != 1:
            raise ControlPlaneError(
                "Reconcile-only recovery requires exactly one native task candidate; "
                f"found {len(candidates)}. Do not retry create_thread or archive candidates automatically."
            )
        report = candidates[0]
        if not isinstance(report, Mapping):
            raise ControlPlaneError("The reconciliation candidate must be a bootstrap report object.")
        verified = validate_bootstrap_report(report, require_clean=require_clean)
        with registry_lock(self.path):
            registry = load_registry(self.path)
            try:
                current = registry["iterations"][iteration_id]
            except KeyError as exc:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} has no durable creation claim; do not finalize it."
                ) from exc
            if current["status"] == CLOSED:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} is closed and cannot be finalized."
                )
            if current["title"] != verified["title"]:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} title conflicts with the verified native task."
                )
            baseline = verified["baseline"]
            active = normalize_record(
                {
                    "iteration_id": current["iteration_id"],
                    "project_id": current["project_id"],
                    "host_id": verified["host_id"],
                    "thread_id": verified["thread_id"],
                    "title": current["title"],
                    "worktree": baseline["worktree"],
                    "branch": baseline["branch"],
                    "baseline": baseline["head"],
                    "status": ACTIVE,
                }
            )
            if current["status"] == ACTIVE:
                comparable_fields = set(active) - {"host_id"}
                if any(current.get(field) != active[field] for field in comparable_fields):
                    raise ControlPlaneError(
                        f"Iteration {iteration_id!r} is already active with different ownership; "
                        "stop without retry or archive."
                    )
                if current.get("host_id") not in {None, active["host_id"]}:
                    raise ControlPlaneError(
                        f"Iteration {iteration_id!r} is already active on a different host; "
                        "stop without retry or archive."
                    )
            registry["iterations"][iteration_id] = active
            validate_unique_ownership(registry)
            atomic_write(self.path, registry)
            return active

    def read(self, iteration_id: str) -> dict[str, str]:
        iteration_id = require_string(iteration_id, "iteration_id")
        registry = load_registry(self.path)
        try:
            return dict(registry["iterations"][iteration_id])
        except KeyError as exc:
            raise ControlPlaneError(f"Iteration {iteration_id!r} is not registered.") from exc

    def reuse(self, iteration_id: str) -> dict[str, str]:
        record = self.read(iteration_id)
        if record["status"] != ACTIVE:
            raise ControlPlaneError(
                f"Iteration {iteration_id!r} is not active (status {record['status']!r}) "
                "and cannot be reused. Reconcile a claim or create a new iteration ID."
            )
        return record

    def update(
        self,
        iteration_id: str,
        *,
        expected_baseline: str,
        changes: Mapping[str, Any],
    ) -> dict[str, str]:
        with registry_lock(self.path):
            iteration_id = require_string(iteration_id, "iteration_id")
            expected_baseline = require_string(expected_baseline, "expected_baseline").lower()
            unknown = sorted(set(changes) - MUTABLE_FIELDS)
            if unknown:
                raise ControlPlaneError("Unsupported update fields: " + ", ".join(unknown) + ".")
            if not changes:
                raise ControlPlaneError("Update requires at least one changed field.")
            registry = load_registry(self.path)
            try:
                current = registry["iterations"][iteration_id]
            except KeyError as exc:
                raise ControlPlaneError(f"Iteration {iteration_id!r} is not registered.") from exc
            if current["status"] != ACTIVE:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} is not active (status {current['status']!r}) "
                    "and cannot be updated."
                )
            if current["baseline"] != expected_baseline:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} baseline conflict: expected {expected_baseline}, "
                    f"stored {current['baseline']}."
                )
            candidate = dict(current)
            candidate.update(changes)
            normalized = normalize_record(candidate)
            registry["iterations"][iteration_id] = normalized
            validate_unique_ownership(registry)
            atomic_write(self.path, registry)
            return normalized

    def close(
        self,
        iteration_id: str,
        *,
        expected_baseline: str,
        outcome: str,
    ) -> dict[str, str]:
        outcome = require_string(outcome, "outcome")
        if outcome not in OWNERSHIP_CLOSE_OUTCOMES:
            raise ControlPlaneError(
                "Ownership closes only after the feature chain is merged or cancelled; "
                "completion receipts, acceptance failures, escalations, and phase closeout "
                "must keep the iteration active."
            )
        with registry_lock(self.path):
            iteration_id = require_string(iteration_id, "iteration_id")
            expected_baseline = require_string(expected_baseline, "expected_baseline").lower()
            registry = load_registry(self.path)
            try:
                current = registry["iterations"][iteration_id]
            except KeyError as exc:
                raise ControlPlaneError(f"Iteration {iteration_id!r} is not registered.") from exc
            if current["status"] == CLAIMED:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} is claimed, not active, and cannot be closed "
                    "before ownership is finalized."
                )
            if current["baseline"] != expected_baseline:
                raise ControlPlaneError(
                    f"Iteration {iteration_id!r} baseline conflict: expected {expected_baseline}, "
                    f"stored {current['baseline']}."
                )
            if current["status"] == CLOSED:
                atomic_write(self.path, registry)
                return dict(current)
            closed = dict(current)
            closed["status"] = CLOSED
            registry["iterations"][iteration_id] = closed
            atomic_write(self.path, registry)
            return closed


def registry_path(value: str | None) -> Path:
    selected = value or os.environ.get("CODEX_EXECUTION_GUARD_REGISTRY")
    if not selected:
        raise ControlPlaneError(
            "Pass --registry with an absolute private local path or set "
            "CODEX_EXECUTION_GUARD_REGISTRY."
        )
    path = Path(selected)
    if not path.is_absolute():
        raise ControlPlaneError("Registry path must be absolute.")
    return path


def load_contract_file(value: str) -> dict[str, Any]:
    path = Path(require_string(value, "contract_file"))
    if not path.is_absolute():
        raise ControlPlaneError("Contract file path must be absolute.")
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControlPlaneError(f"Contract file is unreadable at {path}: {exc}") from exc
    if not isinstance(contract, dict):
        raise ControlPlaneError("Contract file must contain one JSON object.")
    return contract


def add_identity_arguments(parser: argparse.ArgumentParser, *, optional: bool = False) -> None:
    required = not optional
    parser.add_argument("--project", dest="project_id", required=required)
    parser.add_argument("--host", dest="host_id")
    parser.add_argument("--thread", dest="thread_id", required=required)
    parser.add_argument("--title", required=required)
    parser.add_argument("--worktree", required=required)
    parser.add_argument("--branch", required=required)
    parser.add_argument("--baseline", required=required)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", help="Absolute path to the private local iteration registry.")
    commands = parser.add_subparsers(dest="command", required=True)

    claim = commands.add_parser(
        "claim",
        help="Atomically claim the iteration before the one allowed native create call.",
    )
    claim.add_argument("--iteration", required=True)
    claim.add_argument("--project", dest="project_id", required=True)
    claim.add_argument("--title", required=True)

    finalize = commands.add_parser(
        "finalize",
        help="Finalize one claim from exactly one verified bootstrap candidate.",
    )
    finalize.add_argument("--iteration", required=True)
    finalize.add_argument(
        "--candidate-json",
        action="append",
        default=[],
        help="One bootstrap report JSON object; zero or repeated values fail closed.",
    )

    stage = commands.add_parser(
        "stage-contract",
        help="Stage a same-host private contract artifact and render its short reference.",
    )
    stage.add_argument("--iteration", required=True)
    stage.add_argument("--target-session", required=True)
    stage.add_argument("--plugin-data", required=True)
    stage.add_argument("--contract-file", required=True)

    fallback = commands.add_parser(
        "fold-inline",
        help="Render the labeled cross-host fallback when target PLUGIN_DATA is unavailable.",
    )
    fallback.add_argument("--contract-file", required=True)

    create = commands.add_parser(
        "create",
        help="Import one already-verified active ownership record (legacy compatibility).",
    )
    create.add_argument("--iteration", required=True)
    add_identity_arguments(create)

    for name in ("read", "reuse"):
        command = commands.add_parser(name, help=f"{name.title()} one ownership record.")
        command.add_argument("--iteration", required=True)

    update = commands.add_parser("update", help="Update an active record after baseline comparison.")
    update.add_argument("--iteration", required=True)
    update.add_argument("--expected-baseline", required=True)
    add_identity_arguments(update, optional=True)

    close = commands.add_parser(
        "close",
        help="Close ownership only after an explicit merged or cancelled outcome.",
    )
    close.add_argument("--iteration", required=True)
    close.add_argument("--expected-baseline", required=True)
    close.add_argument("--outcome", required=True, choices=sorted(OWNERSHIP_CLOSE_OUTCOMES))
    return parser


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "fold-inline":
        return {"prompt": folded_inline_handoff(load_contract_file(args.contract_file))}
    registry = IterationRegistry(registry_path(args.registry))
    if args.command == "claim":
        return registry.claim(
            iteration_id=args.iteration,
            project_id=args.project_id,
            title=args.title,
        )
    if args.command == "finalize":
        candidates: list[Mapping[str, Any]] = []
        for rendered in args.candidate_json:
            try:
                candidate = json.loads(rendered)
            except json.JSONDecodeError as exc:
                raise ControlPlaneError(f"Bootstrap candidate JSON is invalid: {exc}") from exc
            if not isinstance(candidate, dict):
                raise ControlPlaneError("Each bootstrap candidate must be a JSON object.")
            candidates.append(candidate)
        return registry.finalize_claim(args.iteration, candidates=candidates)
    if args.command == "stage-contract":
        plugin_data = Path(args.plugin_data)
        if not plugin_data.is_absolute():
            raise ControlPlaneError("PLUGIN_DATA path must be absolute.")
        return stage_contract_handoff(
            plugin_data=plugin_data,
            registry=registry,
            iteration_id=args.iteration,
            target_session_id=args.target_session,
            contract=load_contract_file(args.contract_file),
        )
    if args.command == "create":
        record = {
            "iteration_id": args.iteration,
            "project_id": args.project_id,
            "thread_id": args.thread_id,
            "title": args.title,
            "worktree": args.worktree,
            "branch": args.branch,
            "baseline": args.baseline,
            "status": ACTIVE,
        }
        if args.host_id is not None:
            record["host_id"] = args.host_id
        return registry.create(record)
    if args.command == "read":
        return registry.read(args.iteration)
    if args.command == "reuse":
        return registry.reuse(args.iteration)
    if args.command == "close":
        return registry.close(
            args.iteration,
            expected_baseline=args.expected_baseline,
            outcome=args.outcome,
        )
    if args.command == "update":
        changes = {
            field: getattr(args, field)
            for field in MUTABLE_FIELDS
            if getattr(args, field, None) is not None
        }
        return registry.update(
            args.iteration,
            expected_baseline=args.expected_baseline,
            changes=changes,
        )
    raise ControlPlaneError(f"Unsupported command {args.command!r}.")


def main() -> int:
    try:
        record = execute(build_parser().parse_args())
        json.dump(record, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    except ControlPlaneError as exc:
        print(f"control-plane error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
