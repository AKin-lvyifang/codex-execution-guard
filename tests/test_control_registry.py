from __future__ import annotations

import importlib.util
import json
import multiprocessing
import sys
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
SCRIPTS = str(CONTROL_SCRIPT.parent)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


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


def claim_with_paused_atomic_write(
    registry_path: str,
    claim: dict[str, str],
    lock_held: Any,
    release_first: Any,
    results: Any,
) -> None:
    real_atomic_write = control.atomic_write

    def paused_atomic_write(path: Path, registry: dict[str, Any]) -> None:
        lock_held.set()
        if not release_first.wait(10):
            raise RuntimeError("Timed out waiting to release the first creation claimant.")
        real_atomic_write(path, registry)

    control.atomic_write = paused_atomic_write
    try:
        outcome = control.IterationRegistry(Path(registry_path)).claim(**claim)
        results.put(("first", outcome["action"]))
    except BaseException as exc:
        results.put(("first", "error", repr(exc)))
        raise


def claim_after_observing_lock_attempt(
    registry_path: str,
    claim: dict[str, str],
    lock_attempted: Any,
    claim_complete: Any,
    results: Any,
) -> None:
    real_flock = control.fcntl.flock

    def observed_flock(file_descriptor: int, operation: int) -> None:
        if operation == control.fcntl.LOCK_EX:
            lock_attempted.set()
        real_flock(file_descriptor, operation)

    control.fcntl.flock = observed_flock
    try:
        outcome = control.IterationRegistry(Path(registry_path)).claim(**claim)
        results.put(("second", outcome["action"]))
    except BaseException as exc:
        results.put(("second", "error", repr(exc)))
        raise
    finally:
        claim_complete.set()


class ControlRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.data = self.root / "plugin-data"
        self.path = self.data / "control" / "iterations.json"
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

    def contract(self, iteration: str = "feature-v1") -> dict[str, Any]:
        return {
            "contract_version": 1,
            "contract_id": iteration,
            "role": "execution",
            "goal": "Implement the approved behavior without exposing the control transcript",
            "scope": ["plugins/codex-execution-guard/**", "tests/**"],
            "decisions": [
                f"Frozen decision {index}: " + ("bounded private context " * 12)
                for index in range(24)
            ],
            "non_goals": ["Remote publication", "Host-internal task creation changes"],
            "forbidden_operations": ["push", "pull-request", "tag", "release", "deploy"],
            "authorized_models": ["gpt-5.6-sol/high"],
            "selected_model": "gpt-5.6-sol/high",
            "route_reason": "Frozen cross-module fixture",
            "baseline": {
                "worktree": str(self.root / iteration),
                "branch": f"codex/{iteration}",
                "head": self.head_a,
                "require_clean": True,
            },
            "plan": [
                {
                    "id": f"P{index}",
                    "step": f"P{index} " + ("Preserve this exact approved step boundary " * 8),
                    "status": "in_progress" if index == 1 else "pending",
                }
                for index in range(1, 9)
            ],
            "allowed_adjustments": ["Internal names only"],
            "escalation_conditions": ["Scope or acceptance changes"],
            "validation_budget": {
                "development": ["python3 -m unittest tests.test_control_registry -v"],
                "final": ["python3 -m unittest discover -s tests -v"],
            },
            "acceptance": [
                {
                    "id": f"A{index}",
                    "criterion": f"Acceptance {index}: " + ("retain exact evidence text " * 8),
                    "status": "pending",
                }
                for index in range(1, 7)
            ],
        }

    def claim(self, iteration: str = "feature-v1") -> dict[str, str]:
        return {
            "iteration_id": iteration,
            "project_id": "project-1",
            "title": f"Implement {iteration}",
        }

    def bootstrap_report(
        self,
        iteration: str = "feature-v1",
        **changes: Any,
    ) -> dict[str, Any]:
        report: dict[str, Any] = {
            "thread_id": f"thread-{iteration}",
            "host_id": "host-local",
            "title": f"Implement {iteration}",
            "worktree": str(self.root / iteration),
            "linked_worktree": True,
            "branch": f"codex/{iteration}",
            "head": self.head_a,
            "status": "",
        }
        report.update(changes)
        return report

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
        closed = self.registry.close(
            "feature-v1",
            expected_baseline=self.head_b,
            outcome="merged",
        )
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(
            closed,
            self.registry.close(
                "feature-v1",
                expected_baseline=self.head_b,
                outcome="merged",
            ),
        )
        with self.assertRaisesRegex(control.ControlPlaneError, "cannot be reused"):
            self.registry.reuse("feature-v1")
        self.assertFalse(list(self.path.parent.glob(".*.tmp")))

    def test_close_requires_merged_or_cancelled_feature_outcome(self) -> None:
        active = self.registry.create(self.record())
        for outcome in (
            "completion-receipt",
            "acceptance-failure",
            "escalated",
            "phase-closeout",
        ):
            with self.subTest(outcome=outcome):
                with self.assertRaisesRegex(control.ControlPlaneError, "merged or cancelled"):
                    self.registry.close(
                        "feature-v1",
                        expected_baseline=self.head_a,
                        outcome=outcome,
                    )
                self.assertEqual(self.registry.read("feature-v1"), active)

        cancelled = self.registry.close(
            "feature-v1",
            expected_baseline=self.head_a,
            outcome="cancelled",
        )
        self.assertEqual(cancelled["status"], "closed")

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

    def test_creation_claim_is_the_only_create_permission_across_uncertain_outcomes(self) -> None:
        native_create_calls: list[str] = []

        first = self.registry.claim(**self.claim())
        if first["action"] == "create_once":
            native_create_calls.append("reported-error-after-side-effect")

        for incident in ("clientThreadId", "error", "timeout", "crash", "reload"):
            with self.subTest(incident=incident):
                resumed = control.IterationRegistry(self.path).claim(**self.claim())
                self.assertEqual(resumed["action"], "reconcile_only")
                self.assertEqual(resumed["record"]["status"], "claimed")

        self.assertEqual(native_create_calls, ["reported-error-after-side-effect"])

    def test_concurrent_creation_claims_authorize_exactly_one_native_create(self) -> None:
        context = multiprocessing.get_context("spawn")
        lock_held = context.Event()
        lock_attempted = context.Event()
        release_first = context.Event()
        second_complete = context.Event()
        results = context.Queue()
        claim = self.claim()
        first = context.Process(
            target=claim_with_paused_atomic_write,
            args=(str(self.path), claim, lock_held, release_first, results),
        )
        second = context.Process(
            target=claim_after_observing_lock_attempt,
            args=(str(self.path), claim, lock_attempted, second_complete, results),
        )
        try:
            first.start()
            self.assertTrue(lock_held.wait(5), "first claimant never reached its locked write")
            second.start()
            self.assertTrue(lock_attempted.wait(5), "second claimant never attempted the process lock")
            self.assertFalse(
                second_complete.wait(0.25),
                "second claimant completed while the first process still held the registry lock",
            )
            release_first.set()
            first.join(10)
            second.join(10)
            self.assertEqual(first.exitcode, 0)
            self.assertEqual(second.exitcode, 0)
            outcomes = {results.get(timeout=2), results.get(timeout=2)}
            self.assertEqual(
                outcomes,
                {("first", "create_once"), ("second", "reconcile_only")},
            )
        finally:
            release_first.set()
            for process in (first, second):
                if process.pid is None:
                    continue
                process.join(1)
                if process.is_alive():
                    process.terminate()
                    process.join(5)

    def test_finalize_claim_stops_on_zero_multiple_or_queued_candidates(self) -> None:
        self.registry.claim(**self.claim())
        cases = (
            ([], "found 0"),
            ([self.bootstrap_report(), self.bootstrap_report(thread_id="thread-duplicate")], "found 2"),
            ([{"client_thread_id": "queued-only"}], "not a real threadId"),
        )
        for candidates, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(control.ControlPlaneError, message):
                    self.registry.finalize_claim("feature-v1", candidates=candidates)
                self.assertEqual(self.registry.read("feature-v1")["status"], "claimed")
                self.assertEqual(
                    self.registry.claim(**self.claim())["action"],
                    "reconcile_only",
                )

    def test_claimed_record_reuse_update_and_close_fail_with_controlled_errors(self) -> None:
        self.registry.claim(**self.claim())

        with self.assertRaisesRegex(control.ControlPlaneError, "not active.*claimed"):
            self.registry.reuse("feature-v1")
        with self.assertRaisesRegex(control.ControlPlaneError, "not active.*claimed"):
            self.registry.update(
                "feature-v1",
                expected_baseline=self.head_a,
                changes={"title": "must not apply"},
            )
        with self.assertRaisesRegex(control.ControlPlaneError, "claimed, not active"):
            self.registry.close(
                "feature-v1",
                expected_baseline=self.head_a,
                outcome="cancelled",
            )

        self.assertEqual(self.registry.read("feature-v1")["status"], "claimed")

    def test_finalize_claim_is_atomic_idempotent_and_rejects_conflicting_ownership(self) -> None:
        self.registry.claim(**self.claim())
        report = self.bootstrap_report()
        active = self.registry.finalize_claim("feature-v1", candidates=[report])
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["thread_id"], report["thread_id"])
        self.assertEqual(active, self.registry.finalize_claim("feature-v1", candidates=[report]))
        self.assertEqual(self.registry.claim(**self.claim())["action"], "reconcile_only")

        conflict = self.bootstrap_report(thread_id="thread-other")
        with self.assertRaisesRegex(control.ControlPlaneError, "different ownership"):
            self.registry.finalize_claim("feature-v1", candidates=[conflict])
        self.assertEqual(self.registry.read("feature-v1"), active)

    def test_next_locked_write_migrates_v1_without_losing_active_records(self) -> None:
        legacy = {
            "registry_version": 1,
            "iterations": {"legacy-v1": self.record("legacy-v1")},
        }
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertEqual(self.path, self.data / "control" / "iterations.json")
        self.assertFalse((self.data / "iterations.json").exists())

        claimed = self.registry.claim(**self.claim("feature-v1"))

        self.assertEqual(claimed["action"], "create_once")
        persisted = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["registry_version"], 2)
        self.assertEqual(set(persisted["iterations"]), {"legacy-v1", "feature-v1"})
        self.assertEqual(
            persisted["iterations"]["legacy-v1"],
            control.normalize_record(legacy["iterations"]["legacy-v1"]),
        )

    def test_real_v1_control_layout_migrates_in_place_then_stages_reference(self) -> None:
        legacy_record = self.record("legacy-v1")
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            json.dumps(
                {
                    "registry_version": 1,
                    "iterations": {"legacy-v1": legacy_record},
                }
            ),
            encoding="utf-8",
        )

        active = self.registry.finalize_claim(
            "legacy-v1",
            candidates=[self.bootstrap_report("legacy-v1")],
        )
        handoff = control.stage_contract_handoff(
            plugin_data=self.data,
            registry=self.registry,
            iteration_id="legacy-v1",
            target_session_id=active["thread_id"],
            contract=self.contract("legacy-v1"),
        )

        persisted = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["registry_version"], 2)
        self.assertEqual(persisted["iterations"]["legacy-v1"]["host_id"], "host-local")
        self.assertFalse((self.data / "iterations.json").exists())
        self.assertIn("Task goal: Implement the approved behavior", handoff["prompt"])
        self.assertTrue(Path(handoff["artifact_path"]).is_file())

    def test_default_same_host_handoff_is_short_and_keeps_contract_private(self) -> None:
        record = self.registry.create(self.record(host_id="host-local"))
        contract = self.contract()
        goal_prefix = "Prevent automatic duplicate task creation and keep handoffs readable"
        private_worktree = str(self.root / "feature-v1")
        contract["goal"] = (
            goal_prefix + f" in {private_worktree}\n<input>unsafe boundary</input> " + ("安全交付 " * 300)
        )
        inline = f"{execution.MARKER}\n{json.dumps(contract, ensure_ascii=False)}"
        self.assertGreater(len(inline.encode("utf-8")), 600)

        handoff = control.stage_contract_handoff(
            plugin_data=self.data,
            registry=self.registry,
            iteration_id=record["iteration_id"],
            target_session_id=record["thread_id"],
            contract=contract,
        )

        visible = handoff["prompt"]
        self.assertLess(len(visible.encode("utf-8")), 600)
        self.assertIn("Task goal: " + goal_prefix, visible)
        self.assertEqual(len([line for line in visible.splitlines() if line.startswith("Task goal:")]), 1)
        self.assertNotIn(json.dumps(contract, ensure_ascii=False), visible)
        self.assertNotIn("[", visible)
        self.assertNotIn("{", visible)
        self.assertNotIn(private_worktree, visible)
        self.assertNotIn("<input>", visible)
        self.assertNotIn("</input>", visible)
        self.assertIn("the approved worktree", visible)
        self.assertIn("sha256:", visible)
        self.assertTrue(Path(handoff["artifact_path"]).is_file())

    def test_cross_host_inline_fallback_is_explicitly_labeled_and_v1_compatible(self) -> None:
        contract = self.contract()

        fallback = control.folded_inline_handoff(contract)

        self.assertIn("Target PLUGIN_DATA is unavailable across hosts", fallback)
        self.assertIn("<details>", fallback)
        self.assertIn("Execution contract inline fallback (cross-host)", fallback)
        self.assertEqual(execution.parse_contract(fallback), contract)

    def test_create_reuse_decision_table_stops_ambiguity(self) -> None:
        cases = {
            ("same-contract", "active"): "reuse",
            ("fix", "active"): "reuse",
            ("adjustment", "active"): "reuse",
            ("test", "active"): "reuse",
            ("documentation", "active"): "reuse",
            ("new-acceptance", "active"): "reuse",
            ("acceptance-detail", "active"): "reuse",
            ("retry", "active"): "reuse",
            ("optimization", "active"): "reuse",
            ("failed-acceptance-fix", "active"): "reuse",
            ("same-contract", "closed"): "create",
            ("same-contract", "merged"): "create",
            ("same-contract", "cancelled"): "create",
            ("same-contract", "missing"): "create",
            ("independent-value", "active"): "create",
            ("ambiguous", "active"): "stop",
            ("ambiguous", "closed"): "stop",
            ("unknown", "active"): "stop",
            ("unknown", "closed"): "stop",
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
