from __future__ import annotations

import importlib.util
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROL_SCRIPT = (
    ROOT / "plugins" / "codex-execution-guard" / "scripts" / "control_plane.py"
)
EXECUTION_SCRIPT = (
    ROOT / "plugins" / "codex-execution-guard" / "scripts" / "execution_guard.py"
)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control = load_module("control_plane", CONTROL_SCRIPT)
execution = load_module("execution_guard", EXECUTION_SCRIPT)


def create_with_paused_atomic_write(
    registry_path: str,
    record: dict[str, str],
    lock_held: Any,
    release_first: Any,
    results: Any,
) -> None:
    real_atomic_write = control.atomic_write

    def paused_atomic_write(path: Path, registry: dict[str, Any]) -> None:
        lock_held.set()
        if not release_first.wait(10):
            raise RuntimeError("Timed out waiting to release the first registry writer.")
        real_atomic_write(path, registry)

    control.atomic_write = paused_atomic_write
    try:
        created = control.IterationRegistry(Path(registry_path)).create(record)
        results.put(("first", "ok", created["iteration_id"]))
    except BaseException as exc:
        results.put(("first", "error", repr(exc)))
        raise


def create_after_observing_lock_attempt(
    registry_path: str,
    record: dict[str, str],
    lock_attempted: Any,
    write_complete: Any,
    results: Any,
) -> None:
    real_flock = control.fcntl.flock

    def observed_flock(file_descriptor: int, operation: int) -> None:
        if operation == control.fcntl.LOCK_EX:
            lock_attempted.set()
        real_flock(file_descriptor, operation)

    control.fcntl.flock = observed_flock
    try:
        created = control.IterationRegistry(Path(registry_path)).create(record)
        results.put(("second", "ok", created["iteration_id"]))
    except BaseException as exc:
        results.put(("second", "error", repr(exc)))
        raise
    finally:
        write_complete.set()


class ControlRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.path = self.root / "private" / "iterations.json"
        self.registry = control.IterationRegistry(self.path)
        self.head_a = "a" * 40
        self.head_b = "b" * 40

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def record(self, iteration: str = "feature-v1", **changes: Any) -> dict[str, str]:
        record = {
            "iteration_id": iteration,
            "project_id": "project-1",
            "thread_id": f"thread-{iteration}",
            "title": f"Implement {iteration}",
            "worktree": str(self.root / iteration),
            "branch": f"codex/{iteration}",
            "baseline": self.head_a,
            "status": "active",
        }
        record.update(changes)
        return record

    def test_create_read_update_reuse_and_close(self) -> None:
        created = self.registry.create(self.record())
        self.assertEqual(created, self.registry.read("feature-v1"))
        self.assertEqual(created, self.registry.reuse("feature-v1"))
        updated = self.registry.update(
            "feature-v1",
            expected_baseline=self.head_a,
            changes={"title": "Renamed iteration", "baseline": self.head_b},
        )
        self.assertEqual(updated["title"], "Renamed iteration")
        self.assertEqual(updated["baseline"], self.head_b)
        closed = self.registry.close("feature-v1", expected_baseline=self.head_b)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed, self.registry.close("feature-v1", expected_baseline=self.head_b))
        with self.assertRaisesRegex(control.ControlPlaneError, "cannot be reused"):
            self.registry.reuse("feature-v1")
        self.assertFalse(list(self.path.parent.glob(".*.tmp")))

    def test_duplicate_iteration_and_ownership_are_rejected(self) -> None:
        original = self.registry.create(self.record())
        with self.assertRaisesRegex(control.ControlPlaneError, "already exists"):
            self.registry.create(self.record())
        conflicts = (
            {"thread_id": original["thread_id"]},
            {"worktree": original["worktree"]},
            {"project_id": original["project_id"], "branch": original["branch"]},
        )
        for index, conflict in enumerate(conflicts, start=1):
            candidate = self.record(f"other-{index}", project_id=f"project-{index + 1}")
            candidate.update(conflict)
            with self.subTest(conflict=conflict):
                with self.assertRaisesRegex(control.ControlPlaneError, "Duplicate"):
                    self.registry.create(candidate)

    def test_stale_baseline_and_corrupt_state_fail_without_overwrite(self) -> None:
        self.registry.create(self.record())
        with self.assertRaisesRegex(control.ControlPlaneError, "baseline conflict"):
            self.registry.update(
                "feature-v1",
                expected_baseline=self.head_b,
                changes={"title": "must not apply"},
            )
        self.assertNotEqual(self.registry.read("feature-v1")["title"], "must not apply")
        corrupt = "{not json"
        self.path.write_text(corrupt, encoding="utf-8")
        with self.assertRaisesRegex(control.ControlPlaneError, "do not overwrite"):
            self.registry.create(self.record("other"))
        self.assertEqual(self.path.read_text(encoding="utf-8"), corrupt)

    def test_second_process_waits_then_reloads_without_losing_first_write(self) -> None:
        context = multiprocessing.get_context("spawn")
        lock_held = context.Event()
        lock_attempted = context.Event()
        release_first = context.Event()
        second_complete = context.Event()
        results = context.Queue()
        first = context.Process(
            target=create_with_paused_atomic_write,
            args=(str(self.path), self.record("first"), lock_held, release_first, results),
        )
        second = context.Process(
            target=create_after_observing_lock_attempt,
            args=(
                str(self.path),
                self.record("second"),
                lock_attempted,
                second_complete,
                results,
            ),
        )
        try:
            first.start()
            self.assertTrue(lock_held.wait(5), "first writer never reached its locked write")
            second.start()
            self.assertTrue(lock_attempted.wait(5), "second writer never attempted the process lock")
            self.assertFalse(
                second_complete.wait(0.25),
                "second writer completed while the first process still held the registry lock",
            )
            release_first.set()
            first.join(10)
            second.join(10)
            self.assertEqual(first.exitcode, 0)
            self.assertEqual(second.exitcode, 0)
            outcomes = {results.get(timeout=2), results.get(timeout=2)}
            self.assertEqual(
                outcomes,
                {("first", "ok", "first"), ("second", "ok", "second")},
            )
            registry = control.load_registry(self.path)
            self.assertEqual(set(registry["iterations"]), {"first", "second"})
            self.assertTrue(control.registry_lock_path(self.path).exists())
        finally:
            release_first.set()
            for process in (first, second):
                if process.pid is None:
                    continue
                process.join(1)
                if process.is_alive():
                    process.terminate()
                    process.join(5)

    def test_create_reuse_decision_table_stops_ambiguity(self) -> None:
        cases = {
            ("same-contract", "active"): "reuse",
            ("fix", "active"): "reuse",
            ("adjustment", "active"): "reuse",
            ("test", "active"): "reuse",
            ("documentation", "active"): "reuse",
            ("same-contract", "closed"): "create",
            ("same-contract", "merged"): "create",
            ("same-contract", "missing"): "create",
            ("independent-value", "active"): "create",
            ("new-acceptance", "active"): "create",
            ("ambiguous", "active"): "stop",
            ("unknown", "active"): "stop",
        }
        for evidence, expected in cases.items():
            with self.subTest(evidence=evidence):
                self.assertEqual(control.decide_task(*evidence), expected)

    def test_bootstrap_requires_real_thread_and_verified_clean_baseline(self) -> None:
        queued = {"client_thread_id": "queued-1"}
        with self.assertRaisesRegex(control.ControlPlaneError, "not a real threadId"):
            control.validate_bootstrap_report(queued)
        report = {
            "thread_id": "thread-real",
            "host_id": "local",
            "title": "Execution Guard V2",
            "worktree": str(self.root / "worktree"),
            "linked_worktree": True,
            "branch": "codex/execution-guard-v2",
            "head": self.head_a,
            "status": "",
        }
        validated = control.validate_bootstrap_report(report)
        self.assertEqual(validated["thread_id"], "thread-real")
        self.assertEqual(validated["baseline"]["head"], self.head_a)
        detached = dict(report, branch="")
        with self.assertRaisesRegex(control.ControlPlaneError, "branch"):
            control.validate_bootstrap_report(detached)
        dirty = dict(report, status=" M README.md")
        with self.assertRaisesRegex(control.ControlPlaneError, "must be clean"):
            control.validate_bootstrap_report(dirty)

    def test_model_route_intersects_live_evidence_and_labels_fallback(self) -> None:
        authorized = [
            "gpt-5.6-luna/max",
            "gpt-5.6-terra/max",
            "gpt-5.6-sol/high",
            "gpt-5.6-sol/ultra",
        ]
        live = control.route_model(
            "frozen-cross-module",
            authorized,
            host_available=["gpt-5.6-terra/max"],
        )
        self.assertEqual(live["requested_model"], "gpt-5.6-terra/max")
        self.assertTrue(live["fallback"])
        self.assertEqual(live["evidence_source"], "live host-advertised intersection")
        self.assertEqual(live["actual_model_status"], "actual model unverified")
        local = control.route_model("normal", authorized, host_available=None)
        self.assertEqual(
            local["evidence_source"],
            "local authorized-pool fallback; not live host discovery",
        )
        verified = control.route_model(
            "normal",
            authorized,
            host_available=["gpt-5.6-terra/max"],
            actual_model="gpt-5.6-terra/max",
        )
        self.assertEqual(
            verified["actual_model_status"],
            "actual model verified: gpt-5.6-terra/max",
        )
        ambiguous = control.route_model(
            "ambiguous",
            authorized,
            host_available=["gpt-5.6-sol/ultra"],
        )
        self.assertEqual(ambiguous["action"], "control")

    def test_validated_bootstrap_compiles_into_v1_execution_contract(self) -> None:
        report = {
            "thread_id": "thread-real",
            "host_id": "local",
            "title": "Execution Guard V2",
            "worktree": str(self.root / "worktree"),
            "linked_worktree": True,
            "branch": "codex/execution-guard-v2",
            "head": self.head_a,
            "status": "",
        }
        baseline = control.validate_bootstrap_report(report)["baseline"]
        contract = {
            "contract_version": 1,
            "contract_id": "control-compatible-v1",
            "role": "execution",
            "goal": "Implement approved work",
            "scope": ["src/**"],
            "decisions": ["Use the approved behavior"],
            "non_goals": ["Remote release"],
            "forbidden_operations": ["push"],
            "authorized_models": ["gpt-5.6-sol/high"],
            "selected_model": "gpt-5.6-sol/high",
            "route_reason": "Frozen cross-module work",
            "baseline": baseline,
            "plan": [{"id": "P1", "step": "P1 Implement", "status": "in_progress"}],
            "allowed_adjustments": ["Internal names"],
            "escalation_conditions": ["Scope changes"],
            "validation_budget": {"development": ["focused test"], "final": ["full test"]},
            "acceptance": [{"id": "A1", "criterion": "Tests pass", "status": "pending"}],
        }
        execution.validate_contract(contract)
        rendered = f"{execution.MARKER}\n{json.dumps(contract)}"
        self.assertEqual(execution.parse_contract(rendered), contract)


if __name__ == "__main__":
    unittest.main()
