from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "codex-execution-guard" / "scripts" / "execution_guard.py"
MARKER = "CODEX_EXECUTION_GUARD_CONTRACT_V1"


class LifecycleFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.data = self.root / "plugin-data"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture User")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-m", "fixture baseline")
        self.head = self.git("rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return completed.stdout.strip()

    def contract(self, **overrides: Any) -> dict[str, Any]:
        contract: dict[str, Any] = {
            "contract_version": 1,
            "contract_id": "fixture-v1",
            "role": "execution",
            "goal": "Implement the frozen fixture behavior",
            "scope": ["tracked.txt"],
            "decisions": ["Use the approved lifecycle"],
            "non_goals": ["Remote publication"],
            "forbidden_operations": ["push", "pull-request", "tag", "release", "deploy"],
            "authorized_models": ["gpt-5.6-sol/high"],
            "selected_model": "gpt-5.6-sol/high",
            "route_reason": "Frozen cross-module fixture",
            "baseline": {
                "worktree": str(self.repo),
                "branch": "main",
                "head": self.head,
                "require_clean": True,
            },
            "plan": [
                {"id": "P1", "step": "P1 Scaffold: build the fixture", "status": "in_progress"},
                {"id": "P2", "step": "P2 Verify: run the fixture", "status": "pending"},
            ],
            "allowed_adjustments": ["Implementation notes only"],
            "escalation_conditions": ["A new stable ID is required"],
            "validation_budget": {
                "development": ["python3 -m unittest tests.test_lifecycle"],
                "final": ["official validators"],
            },
            "acceptance": [
                {"id": "A1", "criterion": "Lifecycle passes", "status": "pending"},
                {"id": "A2", "criterion": "Stop allows completion", "status": "pending"},
            ],
        }
        contract.update(overrides)
        return contract

    def event(self, session_id: str, hook_event_name: str, **fields: Any) -> dict[str, Any]:
        event: dict[str, Any] = {
            "session_id": session_id,
            "transcript_path": None,
            "cwd": str(self.repo),
            "hook_event_name": hook_event_name,
            "model": "gpt-5.6-sol",
        }
        event.update(fields)
        return event

    def run_hook(self, event: dict[str, Any], *, with_plugin_data: bool = True) -> dict[str, Any] | None:
        environment = dict(os.environ)
        if with_plugin_data:
            environment["PLUGIN_DATA"] = str(self.data)
        else:
            environment.pop("PLUGIN_DATA", None)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(event),
            cwd=self.repo,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = completed.stdout.strip()
        return json.loads(output) if output else None

    def activate(self, session_id: str = "guarded") -> dict[str, Any]:
        prompt = f"{MARKER}\n{json.dumps(self.contract())}"
        result = self.run_hook(
            self.event(session_id, "UserPromptSubmit", turn_id="turn-1", prompt=prompt)
        )
        self.assertEqual(
            result["hookSpecificOutput"]["hookEventName"],  # type: ignore[index]
            "UserPromptSubmit",
        )
        return self.contract()

    def approved_plan(self, *, complete: bool = False, explanation: str | None = None) -> dict[str, Any]:
        status = "completed" if complete else None
        tool_input: dict[str, Any] = {
            "plan": [
                {"step": "P1 Scaffold: build the fixture", "status": status or "in_progress"},
                {"step": "P2 Verify: run the fixture", "status": status or "pending"},
            ]
        }
        if explanation is not None:
            tool_input["explanation"] = explanation
        return tool_input

    def register(self, session_id: str = "guarded") -> None:
        tool_input = self.approved_plan()
        allowed = self.run_hook(
            self.event(
                session_id,
                "PreToolUse",
                turn_id="turn-2",
                tool_name="update_plan",
                tool_use_id="plan-1",
                tool_input=tool_input,
            )
        )
        self.assertIsNone(allowed)
        accepted = self.run_hook(
            self.event(
                session_id,
                "PostToolUse",
                turn_id="turn-2",
                tool_name="update_plan",
                tool_use_id="plan-1",
                tool_input=tool_input,
                tool_response={"ok": True},
            )
        )
        self.assertIn("accepted", accepted["hookSpecificOutput"]["additionalContext"])  # type: ignore[index]

    def state(self, session_id: str = "guarded") -> dict[str, Any]:
        return json.loads((self.data / "sessions" / f"{session_id}.json").read_text(encoding="utf-8"))

    def test_ordinary_session_is_inert_and_creates_no_state(self) -> None:
        prompt = self.run_hook(
            self.event("ordinary", "UserPromptSubmit", turn_id="turn-1", prompt="Fix the typo")
        )
        write = self.run_hook(
            self.event(
                "ordinary",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="apply_patch",
                tool_use_id="write-1",
                tool_input={"command": "*** Begin Patch"},
            )
        )
        stop = self.run_hook(
            self.event(
                "ordinary",
                "Stop",
                turn_id="turn-1",
                stop_hook_active=False,
                last_assistant_message="Done",
            )
        )
        self.assertIsNone(prompt)
        self.assertIsNone(write)
        self.assertIsNone(stop)
        self.assertFalse((self.data / "sessions").exists())

    def test_ordinary_session_without_plugin_data_is_fail_open(self) -> None:
        prompt = self.run_hook(
            self.event("ordinary-no-data", "UserPromptSubmit", turn_id="turn-1", prompt="Fix the typo"),
            with_plugin_data=False,
        )
        write = self.run_hook(
            self.event(
                "ordinary-no-data",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="apply_patch",
                tool_use_id="write-1",
                tool_input={"command": "*** Begin Patch"},
            ),
            with_plugin_data=False,
        )
        stop = self.run_hook(
            self.event(
                "ordinary-no-data",
                "Stop",
                turn_id="turn-1",
                stop_hook_active=False,
                last_assistant_message="Done",
            ),
            with_plugin_data=False,
        )
        contract_prompt = f"{MARKER}\n{json.dumps(self.contract())}"
        activation = self.run_hook(
            self.event(
                "guarded-no-data",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=contract_prompt,
            ),
            with_plugin_data=False,
        )
        self.assertIsNone(prompt)
        self.assertIsNone(write)
        self.assertIsNone(stop)
        self.assertEqual(activation["decision"], "block")  # type: ignore[index]
        self.assertIn("PLUGIN_DATA", activation["reason"])  # type: ignore[index]

    def test_inline_marker_text_is_inert(self) -> None:
        prompt = f"Please explain {MARKER} {{not a contract}}"
        result = self.run_hook(
            self.event("inline", "UserPromptSubmit", turn_id="turn-1", prompt=prompt)
        )
        self.assertIsNone(result)
        self.assertFalse((self.data / "sessions" / "inline.json").exists())

    def test_guarded_write_waits_for_environment_and_exact_plan(self) -> None:
        self.activate()
        denied = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-2",
                tool_name="apply_patch",
                tool_use_id="write-1",
                tool_input={"command": "*** Begin Patch"},
            )
        )
        self.assertEqual(
            denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
            "deny",
        )
        self.register()
        allowed = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-3",
                tool_name="apply_patch",
                tool_use_id="write-2",
                tool_input={"command": "*** Begin Patch"},
            )
        )
        self.assertIsNone(allowed)
        state = self.state()
        self.assertTrue(state["environment_verified"])
        self.assertTrue(state["plan_registered"])

    def test_branch_change_and_branch_drift_are_rejected(self) -> None:
        self.activate()
        self.register()
        switch = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-3",
                tool_name="Bash",
                tool_use_id="switch-1",
                tool_input={"command": "git switch other"},
            )
        )
        self.assertEqual(switch["hookSpecificOutput"]["permissionDecision"], "deny")  # type: ignore[index]
        self.git("switch", "-c", "drift")
        drift = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-3",
                tool_name="apply_patch",
                tool_use_id="write-drift",
                tool_input={"command": "*** Begin Patch"},
            )
        )
        self.assertEqual(drift["hookSpecificOutput"]["permissionDecision"], "deny")  # type: ignore[index]
        self.assertIn("drifted", drift["hookSpecificOutput"]["permissionDecisionReason"])  # type: ignore[index]
        plan_drift = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-3",
                tool_name="update_plan",
                tool_use_id="plan-drift",
                tool_input=self.approved_plan(complete=True),
            )
        )
        self.assertEqual(plan_drift["hookSpecificOutput"]["permissionDecision"], "deny")  # type: ignore[index]
        self.assertIn("drifted", plan_drift["hookSpecificOutput"]["permissionDecisionReason"])  # type: ignore[index]

    def test_new_plan_id_is_rejected_and_legal_status_update_passes(self) -> None:
        self.activate()
        self.register()
        expanded = self.approved_plan()
        expanded["plan"].append({"step": "P3 Unapproved: expand scope", "status": "pending"})
        denied = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-3",
                tool_name="update_plan",
                tool_use_id="plan-2",
                tool_input=expanded,
            )
        )
        self.assertEqual(
            denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
            "deny",
        )
        legal = {
            "plan": [
                {"step": "P1 Scaffold: build the fixture", "status": "completed"},
                {"step": "P2 Verify: run the fixture", "status": "in_progress"},
            ]
        }
        self.assertIsNone(
            self.run_hook(
                self.event(
                    "guarded",
                    "PreToolUse",
                    turn_id="turn-3",
                    tool_name="update_plan",
                    tool_use_id="plan-3",
                    tool_input=legal,
                )
            )
        )

    def test_compaction_restores_contract_step_git_and_evidence(self) -> None:
        self.activate()
        self.register()
        validation = self.event(
            "guarded",
            "PostToolUse",
            turn_id="turn-3",
            tool_name="Bash",
            tool_use_id="test-1",
            tool_input={"command": "python3 -m unittest tests.test_lifecycle"},
            tool_response="Exit code: 0",
        )
        self.assertIsNone(self.run_hook(validation))
        self.assertIsNone(
            self.run_hook(
                self.event("guarded", "PreCompact", turn_id="turn-3", trigger="auto")
            )
        )
        restored = self.run_hook(
            self.event("guarded", "SessionStart", source="compact", permission_mode="default")
        )
        message = restored["hookSpecificOutput"]["additionalContext"]  # type: ignore[index]
        self.assertIn("fixture-v1", message)
        self.assertIn("P1=in_progress", message)
        self.assertIn("branch=main", message)
        self.assertIn("python3 -m unittest", message)
        self.assertIn("Selected model: gpt-5.6-sol/high", message)
        self.assertIn('Scope: ["tracked.txt"]', message)
        self.assertIn('Decisions: ["Use the approved lifecycle"]', message)
        self.assertIn('Non-goals: ["Remote publication"]', message)
        self.assertIn('Forbidden operations: ["push","pull-request","tag","release","deploy"]', message)

    def test_incomplete_stop_continues_and_complete_stop_allows_receipt(self) -> None:
        self.activate()
        self.register()
        incomplete = self.run_hook(
            self.event(
                "guarded",
                "Stop",
                turn_id="turn-3",
                stop_hook_active=False,
                last_assistant_message="Done",
            )
        )
        self.assertEqual(incomplete["decision"], "block")  # type: ignore[index]
        (self.repo / "tracked.txt").write_text("implemented\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-m", "fixture implementation")
        implementation_head = self.git("rev-parse", "HEAD")
        missing_evidence = self.approved_plan(
            complete=True,
            explanation='execution_guard: {"acceptance_complete":["A1"]}',
        )
        denied = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-4",
                tool_name="update_plan",
                tool_use_id="plan-no-evidence",
                tool_input=missing_evidence,
            )
        )
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")  # type: ignore[index]
        self.assertIn("requires non-empty evidence", denied["hookSpecificOutput"]["permissionDecisionReason"])  # type: ignore[index]
        control = (
            'execution_guard: {"acceptance_complete":["A1","A2"],'
            '"evidence":"Frozen lifecycle fixtures passed"}'
        )
        complete_plan = self.approved_plan(complete=True, explanation=control)
        self.assertIsNone(
            self.run_hook(
                self.event(
                    "guarded",
                    "PreToolUse",
                    turn_id="turn-4",
                    tool_name="update_plan",
                    tool_use_id="plan-final",
                    tool_input=complete_plan,
                )
            )
        )
        final_context = self.run_hook(
            self.event(
                "guarded",
                "PostToolUse",
                turn_id="turn-4",
                tool_name="update_plan",
                tool_use_id="plan-final",
                tool_input=complete_plan,
                tool_response={"ok": True},
            )
        )
        self.assertIn("receipt", final_context["hookSpecificOutput"]["additionalContext"])  # type: ignore[index]
        self.assertIn("tracked.txt", final_context["hookSpecificOutput"]["additionalContext"])  # type: ignore[index]
        self.assertIn(implementation_head, final_context["hookSpecificOutput"]["additionalContext"])  # type: ignore[index]
        allowed = self.run_hook(
            self.event(
                "guarded",
                "Stop",
                turn_id="turn-4",
                stop_hook_active=False,
                last_assistant_message="Execution receipt",
            )
        )
        self.assertNotIn("decision", allowed)  # type: ignore[operator]
        self.assertTrue(allowed["continue"])  # type: ignore[index]

    def test_registered_escalation_allows_incomplete_return_to_control(self) -> None:
        self.activate()
        self.register()
        reason = "The approved API has no behavior for case X"
        control = (
            'execution_guard: {"escalation":{"reason":"A required scope decision is missing",'
            f'"evidence":"{reason}"}}}}'
        )
        tool_input = self.approved_plan(explanation=control)
        self.assertIsNone(
            self.run_hook(
                self.event(
                    "guarded",
                    "PreToolUse",
                    turn_id="turn-3",
                    tool_name="update_plan",
                    tool_use_id="plan-escalate",
                    tool_input=tool_input,
                )
            )
        )
        registered = self.run_hook(
            self.event(
                "guarded",
                "PostToolUse",
                turn_id="turn-3",
                tool_name="update_plan",
                tool_use_id="plan-escalate",
                tool_input=tool_input,
                tool_response={"ok": True},
            )
        )
        self.assertIn("escalation is registered", registered["hookSpecificOutput"]["additionalContext"])  # type: ignore[index]
        restored = self.run_hook(
            self.event("guarded", "SessionStart", source="compact", permission_mode="default")
        )
        restored_context = restored["hookSpecificOutput"]["additionalContext"]  # type: ignore[index]
        self.assertIn("A required scope decision is missing", restored_context)
        self.assertIn(reason, restored_context)
        allowed = self.run_hook(
            self.event(
                "guarded",
                "Stop",
                turn_id="turn-3",
                stop_hook_active=False,
                last_assistant_message="Blocked",
            )
        )
        self.assertNotIn("decision", allowed)  # type: ignore[operator]
        self.assertIn("incomplete plan ['P1', 'P2']", allowed["systemMessage"])  # type: ignore[index]
        self.assertIn(reason, allowed["systemMessage"])  # type: ignore[index]

    def test_validation_outcome_change_is_new_evidence_then_duplicate_is_not(self) -> None:
        self.activate()
        self.register()
        validation = self.event(
            "guarded",
            "PostToolUse",
            turn_id="turn-3",
            tool_name="Bash",
            tool_use_id="test-1",
            tool_input={"command": "python3 -m unittest tests.test_lifecycle"},
            tool_response="Exit code: 1",
        )
        self.assertIsNone(self.run_hook(validation))
        validation["tool_use_id"] = "test-2"
        validation["tool_response"] = "Exit code: 0"
        self.assertIsNone(self.run_hook(validation))
        before = list(self.state()["evidence"])
        self.assertEqual(
            [item["outcome"] for item in before if item["kind"] == "validation"],
            ["failed", "passed"],
        )
        validation["tool_use_id"] = "test-3"
        duplicate = self.run_hook(validation)
        after = self.state()["evidence"]
        self.assertEqual(before, after)
        self.assertIn("not new progress", duplicate["hookSpecificOutput"]["additionalContext"])  # type: ignore[index]

    def test_baseline_mismatch_and_corrupt_state_fail_with_recovery(self) -> None:
        bad = self.contract()
        bad["baseline"]["branch"] = "codex/expected"
        prompt = f"{MARKER}\n{json.dumps(bad)}"
        self.run_hook(self.event("mismatch", "UserPromptSubmit", turn_id="turn-1", prompt=prompt))
        denied = self.run_hook(
            self.event(
                "mismatch",
                "PreToolUse",
                turn_id="turn-2",
                tool_name="update_plan",
                tool_use_id="plan-1",
                tool_input=self.approved_plan(),
            )
        )
        self.assertIn(
            "branch expected",
            denied["hookSpecificOutput"]["permissionDecisionReason"],  # type: ignore[index]
        )

        self.activate("corrupt")
        path = self.data / "sessions" / "corrupt.json"
        path.write_text("{not json", encoding="utf-8")
        recovery = self.run_hook(
            self.event(
                "corrupt",
                "PreToolUse",
                turn_id="turn-2",
                tool_name="apply_patch",
                tool_use_id="write-1",
                tool_input={"command": "*** Begin Patch"},
            )
        )
        reason = recovery["hookSpecificOutput"]["permissionDecisionReason"]  # type: ignore[index]
        self.assertIn("repair or remove", reason)


if __name__ == "__main__":
    unittest.main()
