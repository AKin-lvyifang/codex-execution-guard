#!/usr/bin/env python3
"""Canonical private-contract artifacts shared by the Guard control and Hook paths."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping


MARKER = "CODEX_EXECUTION_GUARD_CONTRACT_V1"
REFERENCE_LABEL = "Execution contract reference:"
REFERENCE_PATTERN = re.compile(
    rf"^{re.escape(REFERENCE_LABEL)} sha256:([0-9a-f]{{64}})$"
)
CONTRACT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ARTIFACT_VERSION = 1
REGISTRY_VERSION = 2
ARTIFACT_DIRECTORY = "contracts"
CONTROL_DIRECTORY = "control"
REGISTRY_FILENAME = "iterations.json"
MAX_CONTRACT_ARTIFACT_BYTES = 1024 * 1024
MAX_VISIBLE_HANDOFF_BYTES = 599
MAX_REGISTRY_BYTES = 4 * 1024 * 1024
OWNERSHIP_FIELDS = {
    "iteration_id",
    "project_id",
    "host_id",
    "thread_id",
    "title",
    "worktree",
    "branch",
    "baseline",
    "status",
}
ARTIFACT_FIELDS = {
    "artifact_version",
    "contract_id",
    "target_session_id",
    "ownership",
    "contract",
}


class ContractProtocolError(Exception):
    """A staged contract is unsafe, malformed, unavailable, or no longer bound."""


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractProtocolError(f"Contract artifact field '{field}' must be a non-empty string.")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ContractProtocolError(f"Contract artifact is not canonical JSON: {exc}") from exc
    return rendered.encode("utf-8")


def artifact_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def contract_artifact_path(plugin_data: Path, digest: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ContractProtocolError("Execution contract reference must contain one lowercase SHA-256 digest.")
    return plugin_data.resolve() / ARTIFACT_DIRECTORY / f"{digest}.json"


def registry_path(plugin_data: Path) -> Path:
    return plugin_data.resolve() / CONTROL_DIRECTORY / REGISTRY_FILENAME


def normalize_ownership(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != OWNERSHIP_FIELDS:
        raise ContractProtocolError(
            "Contract artifact ownership must contain exactly the active V2 ownership fields."
        )
    normalized = {field: require_string(value[field], f"ownership.{field}") for field in OWNERSHIP_FIELDS}
    if normalized["status"] != "active":
        raise ContractProtocolError("Contract artifact ownership is not active.")
    worktree = Path(normalized["worktree"])
    if not worktree.is_absolute():
        raise ContractProtocolError("Contract artifact ownership worktree must be absolute.")
    normalized["worktree"] = str(worktree.resolve())
    return normalized


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
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


def stage_contract_artifact(
    *,
    plugin_data: Path,
    contract: Mapping[str, Any],
    target_session_id: str,
    ownership: Mapping[str, Any],
) -> dict[str, str]:
    contract_id = require_string(contract.get("contract_id"), "contract.contract_id")
    if not CONTRACT_ID_PATTERN.fullmatch(contract_id):
        raise ContractProtocolError(
            "Referenced contract IDs must use 1-128 ASCII letters, digits, dots, underscores, or hyphens."
        )
    session_id = require_string(target_session_id, "target_session_id")
    active = normalize_ownership(ownership)
    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "contract_id": contract_id,
        "target_session_id": session_id,
        "ownership": active,
        "contract": dict(contract),
    }
    payload = canonical_json_bytes(artifact)
    if len(payload) > MAX_CONTRACT_ARTIFACT_BYTES:
        raise ContractProtocolError(
            f"Canonical contract artifact exceeds {MAX_CONTRACT_ARTIFACT_BYTES} bytes."
        )
    digest = artifact_digest(payload)
    path = contract_artifact_path(plugin_data, digest)
    if path.exists():
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise ContractProtocolError(f"Cannot read existing contract artifact at {path}: {exc}") from exc
        if not hmac.compare_digest(existing, payload):
            raise ContractProtocolError(
                f"Contract artifact digest collision or conflicting file at {path}; do not overwrite it."
            )
    else:
        atomic_write_bytes(path, payload)
    return {"digest": digest, "artifact_path": str(path)}


def truncate_utf8(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    ellipsis = "…"
    budget = limit - len(ellipsis.encode("utf-8"))
    if budget <= 0:
        raise ContractProtocolError("Visible handoff has no room for a task-goal summary.")
    rendered: list[str] = []
    used = 0
    for character in value:
        size = len(character.encode("utf-8"))
        if used + size > budget:
            break
        rendered.append(character)
        used += size
    return "".join(rendered).rstrip() + ellipsis


def single_line_goal(goal: str) -> str:
    printable = "".join(character if character.isprintable() else " " for character in goal)
    flattened = " ".join(printable.split())
    if not flattened:
        raise ContractProtocolError("Contract goal has no printable single-line summary.")
    return flattened.translate(str.maketrans({"{": "(", "}": ")", "[": "(", "]": ")"}))


def render_reference_prompt(contract_id: str, digest: str, goal: str) -> str:
    if not CONTRACT_ID_PATTERN.fullmatch(contract_id):
        raise ContractProtocolError("Cannot render an unsafe referenced contract ID.")
    contract_artifact_path(Path("/"), digest)
    goal = single_line_goal(require_string(goal, "contract.goal"))
    prefix = (
        f"Execution Guard is ready for contract {contract_id}.\n"
        "Task goal: "
    )
    suffix = f"\n{MARKER}\n{REFERENCE_LABEL} sha256:{digest}"
    available = MAX_VISIBLE_HANDOFF_BYTES - len(prefix.encode("utf-8")) - len(
        suffix.encode("utf-8")
    )
    summary = truncate_utf8(goal, available)
    prompt = prefix + summary + suffix
    if len(prompt.encode("utf-8")) > MAX_VISIBLE_HANDOFF_BYTES:
        raise ContractProtocolError("Visible handoff exceeds its UTF-8 byte limit.")
    return prompt


def render_folded_inline_fallback(contract: Mapping[str, Any]) -> str:
    """Render the explicit cross-host fallback when control cannot stage target PLUGIN_DATA."""
    payload = canonical_json_bytes(contract).decode("utf-8")
    return (
        "Target PLUGIN_DATA is unavailable across hosts; using the labeled inline fallback.\n"
        "<details>\n"
        "<summary>Execution contract inline fallback (cross-host)</summary>\n\n"
        f"{MARKER}\n"
        f"{payload}\n"
        "</details>"
    )


def reference_digest(prompt: str, *, marker_end: int) -> str | None:
    labeled = [
        line.strip()
        for line in prompt[marker_end:].splitlines()
        if line.strip().startswith(REFERENCE_LABEL)
    ]
    if not labeled:
        return None
    if len(labeled) != 1:
        raise ContractProtocolError("Execution contract prompt contains multiple reference lines.")
    match = REFERENCE_PATTERN.fullmatch(labeled[0])
    if match is None:
        raise ContractProtocolError("Execution contract reference has an invalid format.")
    return match.group(1)


def read_bounded(path: Path, limit: int, label: str) -> bytes:
    if path.is_symlink():
        raise ContractProtocolError(f"{label} must not be a symbolic link: {path}")
    try:
        with path.open("rb") as handle:
            payload = handle.read(limit + 1)
    except FileNotFoundError as exc:
        raise ContractProtocolError(f"{label} is missing at {path}.") from exc
    except OSError as exc:
        raise ContractProtocolError(f"Cannot read {label.lower()} at {path}: {exc}") from exc
    if len(payload) > limit:
        raise ContractProtocolError(f"{label} exceeds {limit} bytes.")
    return payload


def load_contract_artifact(plugin_data: Path, digest: str) -> dict[str, Any]:
    path = contract_artifact_path(plugin_data, digest)
    payload = read_bounded(path, MAX_CONTRACT_ARTIFACT_BYTES, "Execution contract artifact")
    if not hmac.compare_digest(artifact_digest(payload), digest):
        raise ContractProtocolError("Execution contract artifact SHA-256 does not match its reference.")
    try:
        artifact = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ContractProtocolError(f"Execution contract artifact JSON is malformed: {exc}") from exc
    if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_FIELDS:
        raise ContractProtocolError("Execution contract artifact has an invalid top-level shape.")
    if artifact.get("artifact_version") != ARTIFACT_VERSION:
        raise ContractProtocolError("Execution contract artifact has an unsupported version.")
    if canonical_json_bytes(artifact) != payload:
        raise ContractProtocolError("Execution contract artifact is not canonical JSON.")
    contract_id = require_string(artifact.get("contract_id"), "contract_id")
    require_string(artifact.get("target_session_id"), "target_session_id")
    artifact["ownership"] = normalize_ownership(artifact.get("ownership"))
    contract = artifact.get("contract")
    if not isinstance(contract, dict):
        raise ContractProtocolError("Execution contract artifact contract must be an object.")
    if contract.get("contract_id") != contract_id:
        raise ContractProtocolError("Execution contract artifact contract ID does not match its envelope.")
    return artifact


def load_active_ownership(plugin_data: Path, iteration_id: str) -> dict[str, str]:
    path = registry_path(plugin_data)
    payload = read_bounded(path, MAX_REGISTRY_BYTES, "Execution Guard ownership registry")
    try:
        registry = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ContractProtocolError(f"Execution Guard ownership registry JSON is malformed: {exc}") from exc
    if (
        not isinstance(registry, dict)
        or set(registry) != {"registry_version", "iterations"}
        or registry.get("registry_version") != REGISTRY_VERSION
        or not isinstance(registry.get("iterations"), dict)
    ):
        raise ContractProtocolError("Execution Guard ownership registry is not a V2 registry.")
    try:
        record = registry["iterations"][iteration_id]
    except KeyError as exc:
        raise ContractProtocolError(
            f"Execution contract {iteration_id!r} has no active ownership record."
        ) from exc
    return normalize_ownership(record)
