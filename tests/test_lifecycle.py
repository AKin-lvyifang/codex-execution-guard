from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "codex-execution-guard" / "scripts"
SCRIPT = SCRIPTS / "execution_guard.py"
CONTROL_SCRIPT = SCRIPTS / "control_plane.py"
MARKER = "CODEX_EXECUTION_GUARD_CONTRACT_V1"


def load_module(name: str, path: Path) -> Any:
    scripts = str(path.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control = load_module("lifecycle_control_plane", CONTROL_SCRIPT)
execution = load_module("lifecycle_execution_guard", SCRIPT)


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
            "host_id": "host-fixture",
        }
        event.update(fields)
        return event

    def guard_bootstrap_create_input(
        self,
        *,
        starting_state: dict[str, Any] | None = None,
        top_level_project_id: bool = False,
    ) -> dict[str, Any]:
        environment: dict[str, Any] = {"type": "worktree"}
        if starting_state is not None:
            environment["startingState"] = starting_state
        tool_input: dict[str, Any] = {
            "title": "Fixture implementation",
            "model": "gpt-5.6-sol",
            "thinking": "high",
            "target": {
                "type": "project",
                "projectId": "project-fixture",
                "environment": environment,
            },
            "prompt": (
                f"{execution.BOOTSTRAP_MARKER}\n"
                "Bootstrap only for iteration fixture-v1-implementation."
            ),
        }
        if top_level_project_id:
            tool_input["projectId"] = "project-fixture"
        return tool_input

    def run_hook(
        self,
        event: dict[str, Any],
        *,
        with_plugin_data: bool = True,
        plugin_data: Path | None = None,
    ) -> dict[str, Any] | None:
        environment = dict(os.environ)
        if with_plugin_data:
            environment["PLUGIN_DATA"] = str(plugin_data or self.data)
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

    def stage_reference(
        self,
        contract: dict[str, Any],
        *,
        session_id: str,
        plugin_data: Path | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        data = plugin_data or self.data
        registry = control.IterationRegistry(data / "control" / "iterations.json")
        title = f"Execute {contract['contract_id']}"
        claim = registry.claim(
            iteration_id=contract["contract_id"],
            project_id="project-fixture",
            title=title,
        )
        if claim["action"] == "create_once":
            registry.finalize_claim(
                contract["contract_id"],
                candidates=[
                    {
                        "thread_id": session_id,
                        "host_id": "host-fixture",
                        "title": title,
                        "worktree": str(self.repo),
                        "linked_worktree": True,
                        "branch": "main",
                        "head": self.head,
                        "status": "",
                    }
                ],
            )
        handoff = control.stage_contract_handoff(
            plugin_data=data,
            registry=registry,
            iteration_id=contract["contract_id"],
            target_session_id=session_id,
            contract=contract,
        )
        return registry, handoff

    def rewrite_artifact(
        self,
        handoff: dict[str, Any],
        mutate: Any,
    ) -> dict[str, Any]:
        original = Path(handoff["artifact_path"])
        artifact = json.loads(original.read_text(encoding="utf-8"))
        mutate(artifact)
        payload = json.dumps(
            artifact,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        rewritten = original.with_name(f"{digest}.json")
        rewritten.write_bytes(payload)
        return {
            **handoff,
            "digest": digest,
            "artifact_path": str(rewritten),
            "prompt": handoff["prompt"].replace(handoff["digest"], digest),
        }

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

    def apply_plan_update(
        self,
        session_id: str,
        tool_input: dict[str, Any],
        *,
        plugin_data: Path | None = None,
        tool_use_id: str,
    ) -> dict[str, Any]:
        allowed = self.run_hook(
            self.event(
                session_id,
                "PreToolUse",
                turn_id="turn-2",
                tool_name="update_plan",
                tool_use_id=tool_use_id,
                tool_input=tool_input,
            ),
            plugin_data=plugin_data,
        )
        self.assertIsNone(allowed)
        accepted = self.run_hook(
            self.event(
                session_id,
                "PostToolUse",
                turn_id="turn-2",
                tool_name="update_plan",
                tool_use_id=tool_use_id,
                tool_input=tool_input,
                tool_response={"ok": True},
            ),
            plugin_data=plugin_data,
        )
        self.assertIsNotNone(accepted)
        return accepted  # type: ignore[return-value]

    def register(
        self,
        session_id: str = "guarded",
        *,
        plugin_data: Path | None = None,
    ) -> None:
        accepted = self.apply_plan_update(
            session_id,
            self.approved_plan(),
            plugin_data=plugin_data,
            tool_use_id="plan-1",
        )
        self.assertIn("accepted", accepted["hookSpecificOutput"]["additionalContext"])  # type: ignore[index]

    def state(
        self,
        session_id: str = "guarded",
        *,
        plugin_data: Path | None = None,
    ) -> dict[str, Any]:
        data = plugin_data or self.data
        return json.loads((data / "sessions" / f"{session_id}.json").read_text(encoding="utf-8"))

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
        delegated_contract = (
            "<codex_delegation>\n"
            "  <source_thread_id>control-task</source_thread_id>\n"
            f"  <input>{contract_prompt}</input>\n"
            "</codex_delegation>"
        )
        delegated_activation = self.run_hook(
            self.event(
                "guarded-no-data-delegated",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=delegated_contract,
            ),
            with_plugin_data=False,
        )
        self.assertIsNone(prompt)
        self.assertIsNone(write)
        self.assertIsNone(stop)
        self.assertEqual(activation["decision"], "block")  # type: ignore[index]
        self.assertIn("PLUGIN_DATA", activation["reason"])  # type: ignore[index]
        self.assertEqual(delegated_activation["decision"], "block")  # type: ignore[index]
        self.assertIn("PLUGIN_DATA", delegated_activation["reason"])  # type: ignore[index]

    def test_inline_marker_text_is_inert(self) -> None:
        prompt = f"Please explain {MARKER} {{not a contract}}"
        result = self.run_hook(
            self.event("inline", "UserPromptSubmit", turn_id="turn-1", prompt=prompt)
        )
        tag_like = self.run_hook(
            self.event(
                "inline-tag-like",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=f"<input>{MARKER}\n{{not a contract}}</input>",
            )
        )
        self.assertIsNone(result)
        self.assertIsNone(tag_like)
        self.assertFalse((self.data / "sessions" / "inline.json").exists())
        self.assertFalse((self.data / "sessions" / "inline-tag-like.json").exists())

    def test_reference_activation_and_resume_preserve_exact_untruncated_contract(self) -> None:
        tail_decision = "DECISION_TAIL_SENTINEL"
        tail_step = "PLAN_TAIL_SENTINEL"
        tail_acceptance = "ACCEPTANCE_TAIL_SENTINEL"
        contract = self.contract(
            contract_id="reference-exact-v1",
            decisions=["long boundary " * 1200 + tail_decision],
            plan=[
                {"id": "P1", "step": "P1 First exact boundary", "status": "in_progress"},
                {"id": "P2", "step": "P2 " + "exact step " * 400 + tail_step, "status": "pending"},
            ],
            acceptance=[
                {"id": "A1", "criterion": "First exact acceptance", "status": "pending"},
                {
                    "id": "A2",
                    "criterion": "exact criterion " * 400 + tail_acceptance,
                    "status": "pending",
                },
            ],
        )
        _, handoff = self.stage_reference(contract, session_id="reference-exact")
        visible = handoff["prompt"]
        self.assertLess(len(visible.encode("utf-8")), 600)
        self.assertNotIn("{", visible)
        self.assertNotIn("[", visible)
        self.assertNotIn(str(self.repo), visible)

        activated = self.run_hook(
            self.event(
                "reference-exact",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=visible,
            )
        )
        activation_context = activated["hookSpecificOutput"]["additionalContext"]  # type: ignore[index]
        self.assertIn(tail_decision, activation_context)
        self.assertIn(tail_step, activation_context)
        self.assertIn(tail_acceptance, activation_context)
        self.assertEqual(self.state("reference-exact")["contract"], contract)

        restored = self.run_hook(
            self.event(
                "reference-exact",
                "SessionStart",
                source="compact",
                permission_mode="default",
            )
        )
        restore_context = restored["hookSpecificOutput"]["additionalContext"]  # type: ignore[index]
        self.assertIn(tail_decision, restore_context)
        self.assertIn(tail_step, restore_context)
        self.assertIn(tail_acceptance, restore_context)

    def test_native_delegation_envelope_preserves_private_reference(self) -> None:
        contract = self.contract(contract_id="native-envelope-v1")
        _, handoff = self.stage_reference(contract, session_id="native-task")
        delegated = (
            "<codex_delegation>\n"
            "  <source_thread_id>control-task</source_thread_id>\n"
            f"  <input>{handoff['prompt']}</input>\n"
            "</codex_delegation>"
        )

        activated = self.run_hook(
            self.event(
                "native-task",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=delegated,
            )
        )

        self.assertIn(
            "activated contract native-envelope-v1",
            activated["hookSpecificOutput"]["additionalContext"],  # type: ignore[index]
        )
        self.assertEqual(self.state("native-task")["contract"], contract)

        inline_contract = self.contract(contract_id="native-envelope-inline-v1")
        inline = (
            "<codex_delegation>\n"
            "  <source_thread_id>control-task</source_thread_id>\n"
            f"  <input>{MARKER}\n{json.dumps(inline_contract)}</input>\n"
            "</codex_delegation>"
        )
        inline_activated = self.run_hook(
            self.event(
                "native-inline-task",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=inline,
            )
        )
        self.assertIn(
            "activated contract native-envelope-inline-v1",
            inline_activated["hookSpecificOutput"]["additionalContext"],  # type: ignore[index]
        )
        self.assertEqual(self.state("native-inline-task")["contract"], inline_contract)

    def test_completed_contract_rolls_over_same_session_and_archives_prior_state(self) -> None:
        session_id = "rollover-complete"
        contract = self.contract(contract_id="rollover-v1")
        registry, handoff = self.stage_reference(contract, session_id=session_id)
        self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=handoff["prompt"],
            )
        )
        self.register(session_id)
        completion = self.approved_plan(
            complete=True,
            explanation=(
                'execution_guard: {"acceptance_complete":["A1","A2"],'
                '"evidence":"Initial contract fixtures passed"}'
            ),
        )
        self.assertIsNone(
            self.run_hook(
                self.event(
                    session_id,
                    "PreToolUse",
                    turn_id="turn-2",
                    tool_name="update_plan",
                    tool_use_id="complete-initial",
                    tool_input=completion,
                )
            )
        )
        self.run_hook(
            self.event(
                session_id,
                "PostToolUse",
                turn_id="turn-2",
                tool_name="update_plan",
                tool_use_id="complete-initial",
                tool_input=completion,
                tool_response={"ok": True},
            )
        )
        prior = self.state(session_id)

        (self.repo / "tracked.txt").write_text("completed baseline\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-m", "complete initial contract")
        revised_head = self.git("rev-parse", "HEAD")
        registry.update(
            contract["contract_id"],
            expected_baseline=self.head,
            changes={"baseline": revised_head},
        )
        revised = self.contract(
            contract_id=contract["contract_id"],
            goal="Apply the approved revision in the same implementation lane",
            baseline={**contract["baseline"], "head": revised_head},
        )
        _, revised_handoff = self.stage_reference(revised, session_id=session_id)

        rolled_over = self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-3",
                prompt=revised_handoff["prompt"],
            )
        )

        self.assertIn(
            "activated contract rollover-v1",
            rolled_over["hookSpecificOutput"]["additionalContext"],  # type: ignore[index]
        )
        current = self.state(session_id)
        self.assertEqual(current["contract"], revised)
        self.assertFalse(current["environment_verified"])
        self.assertFalse(current["plan_registered"])
        archives = list((self.data / "session-archive" / session_id).glob("*.json"))
        self.assertEqual(len(archives), 1)
        canonical = json.dumps(
            prior,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.assertEqual(archives[0].stem, hashlib.sha256(canonical).hexdigest())
        self.assertEqual(json.loads(archives[0].read_text(encoding="utf-8")), prior)

    def test_escalated_contract_can_roll_over_with_same_verified_baseline(self) -> None:
        session_id = "rollover-escalated"
        contract = self.contract(contract_id="rollover-escalated-v1")
        _, handoff = self.stage_reference(contract, session_id=session_id)
        self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=handoff["prompt"],
            )
        )
        self.register(session_id)
        escalation = self.approved_plan(
            explanation=(
                'execution_guard: {"escalation":{"reason":"Revision required",'
                '"evidence":"The first acceptance contract was incomplete"}}'
            )
        )
        self.assertIsNone(
            self.run_hook(
                self.event(
                    session_id,
                    "PreToolUse",
                    turn_id="turn-2",
                    tool_name="update_plan",
                    tool_use_id="escalate-initial",
                    tool_input=escalation,
                )
            )
        )
        self.run_hook(
            self.event(
                session_id,
                "PostToolUse",
                turn_id="turn-2",
                tool_name="update_plan",
                tool_use_id="escalate-initial",
                tool_input=escalation,
                tool_response={"ok": True},
            )
        )
        prior = self.state(session_id)
        revised = self.contract(
            contract_id=contract["contract_id"],
            goal="Apply the approved post-escalation revision",
        )
        _, revised_handoff = self.stage_reference(revised, session_id=session_id)

        rolled_over = self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-3",
                prompt=revised_handoff["prompt"],
            )
        )

        self.assertIn(
            "activated contract rollover-escalated-v1",
            rolled_over["hookSpecificOutput"]["additionalContext"],  # type: ignore[index]
        )
        self.assertEqual(self.state(session_id)["contract"], revised)
        archives = list((self.data / "session-archive" / session_id).glob("*.json"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(json.loads(archives[0].read_text(encoding="utf-8")), prior)

    def test_non_terminal_or_different_contract_cannot_replace_active_state(self) -> None:
        session_id = "rollover-rejected"
        contract = self.contract(contract_id="rollover-rejected-v1")
        _, handoff = self.stage_reference(contract, session_id=session_id)
        self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=handoff["prompt"],
            )
        )
        original = self.state(session_id)
        revised = self.contract(
            contract_id=contract["contract_id"],
            goal="Attempt to replace a non-terminal contract",
        )
        _, revised_handoff = self.stage_reference(revised, session_id=session_id)

        non_terminal = self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-2",
                prompt=revised_handoff["prompt"],
            )
        )
        self.assertEqual(non_terminal["decision"], "block")  # type: ignore[index]
        self.assertIn("non-terminal", non_terminal["reason"])  # type: ignore[index]
        self.assertEqual(self.state(session_id), original)

        different = self.contract(contract_id="different-v1")
        different_prompt = f"{MARKER}\n{json.dumps(different)}"
        different_result = self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-3",
                prompt=different_prompt,
            )
        )
        self.assertEqual(different_result["decision"], "block")  # type: ignore[index]
        self.assertIn("different contract_id", different_result["reason"])  # type: ignore[index]
        self.assertEqual(self.state(session_id), original)
        self.assertFalse((self.data / "session-archive" / session_id).exists())

    def test_terminal_marker_free_prompt_keeps_plan_and_write_tools_locked(self) -> None:
        for terminal in ("complete", "escalated"):
            with self.subTest(terminal=terminal):
                data = self.root / f"plugin-data-terminal-{terminal}"
                session_id = f"terminal-{terminal}"
                contract = self.contract(contract_id=f"terminal-{terminal}-v1")
                _, handoff = self.stage_reference(
                    contract,
                    session_id=session_id,
                    plugin_data=data,
                )
                self.run_hook(
                    self.event(
                        session_id,
                        "UserPromptSubmit",
                        turn_id="turn-1",
                        prompt=handoff["prompt"],
                    ),
                    plugin_data=data,
                )
                self.register(session_id, plugin_data=data)
                if terminal == "complete":
                    terminal_update = self.approved_plan(
                        complete=True,
                        explanation=(
                            'execution_guard: {"acceptance_complete":["A1","A2"],'
                            '"evidence":"Terminal fixture passed"}'
                        ),
                    )
                else:
                    terminal_update = self.approved_plan(
                        explanation=(
                            'execution_guard: {"escalation":{"reason":"Revision required",'
                            '"evidence":"Terminal fixture escalated"}}'
                        )
                    )
                self.apply_plan_update(
                    session_id,
                    terminal_update,
                    plugin_data=data,
                    tool_use_id=f"terminal-{terminal}",
                )
                prior = self.state(session_id, plugin_data=data)

                marker_free = self.run_hook(
                    self.event(
                        session_id,
                        "UserPromptSubmit",
                        turn_id="turn-3",
                        prompt="Continue with one more same-feature fix",
                    ),
                    plugin_data=data,
                )
                self.assertIn(
                    "terminal and write-locked",
                    marker_free["hookSpecificOutput"]["additionalContext"],  # type: ignore[index]
                )
                self.assertEqual(self.state(session_id, plugin_data=data), prior)

                guarded_tools = (
                    ("update_plan", self.approved_plan(complete=True)),
                    ("apply_patch", {"command": "*** Begin Patch"}),
                    ("Edit", {"path": "tracked.txt"}),
                    ("Write", {"path": "tracked.txt"}),
                    ("Bash", {"command": "python3 -c 'print(1)'"}),
                )
                for index, (tool_name, tool_input) in enumerate(guarded_tools):
                    with self.subTest(terminal=terminal, tool_name=tool_name):
                        denied = self.run_hook(
                            self.event(
                                session_id,
                                "PreToolUse",
                                turn_id="turn-4",
                                tool_name=tool_name,
                                tool_use_id=f"terminal-lock-{terminal}-{index}",
                                tool_input=tool_input,
                            ),
                            plugin_data=data,
                        )
                        self.assertEqual(
                            denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
                            "deny",
                        )
                        self.assertIn(
                            "terminal",
                            denied["hookSpecificOutput"]["permissionDecisionReason"],  # type: ignore[index]
                        )

    def test_terminal_inline_rollover_is_rejected_after_ownership_closes(self) -> None:
        for outcome in ("merged", "cancelled"):
            with self.subTest(outcome=outcome):
                data = self.root / f"plugin-data-inline-closed-{outcome}"
                session_id = f"inline-closed-{outcome}"
                contract = self.contract(contract_id=f"inline-closed-{outcome}-v1")
                registry, handoff = self.stage_reference(
                    contract,
                    session_id=session_id,
                    plugin_data=data,
                )
                self.run_hook(
                    self.event(
                        session_id,
                        "UserPromptSubmit",
                        turn_id="turn-1",
                        prompt=handoff["prompt"],
                    ),
                    plugin_data=data,
                )
                self.register(session_id, plugin_data=data)
                completion = self.approved_plan(
                    complete=True,
                    explanation=(
                        'execution_guard: {"acceptance_complete":["A1","A2"],'
                        '"evidence":"Initial contract complete"}'
                    ),
                )
                self.apply_plan_update(
                    session_id,
                    completion,
                    plugin_data=data,
                    tool_use_id=f"complete-before-{outcome}",
                )
                prior = self.state(session_id, plugin_data=data)
                closed = registry.close(
                    contract["contract_id"],
                    expected_baseline=self.head,
                    outcome=outcome,
                )
                self.assertEqual(closed["status"], "closed")
                revised = self.contract(
                    contract_id=contract["contract_id"],
                    goal="Attempt terminal continuation through inline V1",
                )

                denied = self.run_hook(
                    self.event(
                        session_id,
                        "UserPromptSubmit",
                        turn_id="turn-3",
                        prompt=f"{MARKER}\n{json.dumps(revised)}",
                    ),
                    plugin_data=data,
                )

                self.assertEqual(denied["decision"], "block")  # type: ignore[index]
                self.assertIn("private reference", denied["reason"])  # type: ignore[index]
                self.assertEqual(self.state(session_id, plugin_data=data), prior)
                self.assertFalse((data / "session-archive" / session_id).exists())

    def test_rollover_session_write_failure_preserves_terminal_state_and_retries(self) -> None:
        data = self.root / "plugin-data-rollover-write-failure"
        session_id = "rollover-write-failure"
        contract = self.contract(contract_id="rollover-write-failure-v1")
        _, handoff = self.stage_reference(
            contract,
            session_id=session_id,
            plugin_data=data,
        )
        self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=handoff["prompt"],
            ),
            plugin_data=data,
        )
        self.register(session_id, plugin_data=data)
        completion = self.approved_plan(
            complete=True,
            explanation=(
                'execution_guard: {"acceptance_complete":["A1","A2"],'
                '"evidence":"Initial contract complete"}'
            ),
        )
        self.apply_plan_update(
            session_id,
            completion,
            plugin_data=data,
            tool_use_id="complete-before-write-failure",
        )
        prior = self.state(session_id, plugin_data=data)
        revised = self.contract(
            contract_id=contract["contract_id"],
            goal="Retry an atomically failed terminal rollover",
        )
        _, revised_handoff = self.stage_reference(
            revised,
            session_id=session_id,
            plugin_data=data,
        )
        session_path = data / "sessions" / f"{session_id}.json"
        real_atomic_write = execution.atomic_write

        def fail_revised_session_write(path: Path, state: dict[str, Any]) -> None:
            if path == session_path and state.get("contract") == revised:
                raise OSError("simulated revised session write failure")
            real_atomic_write(path, state)

        original_stdin = execution.sys.stdin
        original_stdout = execution.sys.stdout
        original_plugin_data = os.environ.get("PLUGIN_DATA")
        output = io.StringIO()
        execution.atomic_write = fail_revised_session_write
        execution.sys.stdin = io.StringIO(
            json.dumps(
                self.event(
                    session_id,
                    "UserPromptSubmit",
                    turn_id="turn-3",
                    prompt=revised_handoff["prompt"],
                )
            )
        )
        execution.sys.stdout = output
        os.environ["PLUGIN_DATA"] = str(data)
        try:
            self.assertEqual(execution.main(), 0)
        finally:
            execution.atomic_write = real_atomic_write
            execution.sys.stdin = original_stdin
            execution.sys.stdout = original_stdout
            if original_plugin_data is None:
                os.environ.pop("PLUGIN_DATA", None)
            else:
                os.environ["PLUGIN_DATA"] = original_plugin_data

        failed = json.loads(output.getvalue())
        self.assertEqual(failed["decision"], "block")
        self.assertIn("prior terminal state remains active", failed["reason"])
        self.assertEqual(self.state(session_id, plugin_data=data), prior)
        archives = list((data / "session-archive" / session_id).glob("*.json"))
        self.assertEqual(len(archives), 1)

        frozen_state = session_path.read_bytes()
        runtime_only = self.repo / "runtime-only.txt"
        runtime_only.write_text("live git context\n", encoding="utf-8")
        resumed = self.run_hook(
            self.event(
                session_id,
                "SessionStart",
                source="resume",
                permission_mode="default",
            ),
            plugin_data=data,
        )
        self.assertIn(
            "runtime-only.txt",
            resumed["hookSpecificOutput"]["additionalContext"],  # type: ignore[index]
        )
        self.assertEqual(session_path.read_bytes(), frozen_state)
        runtime_only.unlink()

        write_denied = self.run_hook(
            self.event(
                session_id,
                "PreToolUse",
                turn_id="turn-4",
                tool_name="apply_patch",
                tool_use_id="write-after-rollover-failure",
                tool_input={"command": "*** Begin Patch"},
            ),
            plugin_data=data,
        )
        self.assertEqual(
            write_denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
            "deny",
        )
        self.assertIn(
            "terminal",
            write_denied["hookSpecificOutput"]["permissionDecisionReason"],  # type: ignore[index]
        )

        retried = self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-5",
                prompt=revised_handoff["prompt"],
            ),
            plugin_data=data,
        )
        self.assertIn(
            "activated contract rollover-write-failure-v1",
            retried["hookSpecificOutput"]["additionalContext"],  # type: ignore[index]
        )
        self.assertEqual(self.state(session_id, plugin_data=data)["contract"], revised)
        self.assertEqual(
            len(list((data / "session-archive" / session_id).glob("*.json"))),
            1,
        )

    def test_terminal_recovery_and_read_only_bash_do_not_rewrite_persisted_state(self) -> None:
        data = self.root / "plugin-data-terminal-read-only"
        session_id = "terminal-read-only"
        contract = self.contract(contract_id="terminal-read-only-v1")
        _, handoff = self.stage_reference(
            contract,
            session_id=session_id,
            plugin_data=data,
        )
        self.run_hook(
            self.event(
                session_id,
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=handoff["prompt"],
            ),
            plugin_data=data,
        )
        self.register(session_id, plugin_data=data)
        completion = self.approved_plan(
            complete=True,
            explanation=(
                'execution_guard: {"acceptance_complete":["A1","A2"],'
                '"evidence":"Terminal read-only fixture passed"}'
            ),
        )
        self.apply_plan_update(
            session_id,
            completion,
            plugin_data=data,
            tool_use_id="complete-before-read-only-events",
        )
        session_path = data / "sessions" / f"{session_id}.json"
        frozen_state = session_path.read_bytes()

        self.assertIsNone(
            self.run_hook(
                self.event(session_id, "PreCompact", turn_id="turn-3", trigger="auto"),
                plugin_data=data,
            )
        )
        self.assertEqual(session_path.read_bytes(), frozen_state)

        read_only = {"command": "git status --porcelain=v1"}
        self.assertIsNone(
            self.run_hook(
                self.event(
                    session_id,
                    "PreToolUse",
                    turn_id="turn-3",
                    tool_name="Bash",
                    tool_use_id="terminal-read-only-bash",
                    tool_input=read_only,
                ),
                plugin_data=data,
            )
        )
        self.assertIsNone(
            self.run_hook(
                self.event(
                    session_id,
                    "PostToolUse",
                    turn_id="turn-3",
                    tool_name="Bash",
                    tool_use_id="terminal-read-only-bash",
                    tool_input=read_only,
                    tool_response={"exit_code": 0},
                ),
                plugin_data=data,
            )
        )
        self.assertEqual(session_path.read_bytes(), frozen_state)

    def test_malformed_native_delegation_envelope_fails_closed(self) -> None:
        data = self.root / "plugin-data-envelope-malformed"
        contract = self.contract(contract_id="native-envelope-malformed-v1")
        _, handoff = self.stage_reference(
            contract,
            session_id="native-envelope-malformed",
            plugin_data=data,
        )
        valid = (
            "<codex_delegation>\n"
            "  <source_thread_id>control-task</source_thread_id>\n"
            f"  <input>{handoff['prompt']}</input>\n"
            "</codex_delegation>"
        )
        input_open = "<input>"
        cases = {
            "unexpected-metadata": valid.replace(
                "  <input>",
                "  <unexpected>metadata</unexpected>\n  <input>",
            ),
            "nested": valid.replace(input_open, input_open + "<codex_delegation>", 1),
            "repeated-input": valid.replace(input_open, input_open + input_open, 1),
            "trailing": valid + "junk",
            "reference-suffix": valid.replace("</input>", "junk</input>", 1),
        }
        for case, delegated in cases.items():
            with self.subTest(case=case):
                denied = self.run_hook(
                    self.event(
                        "native-envelope-malformed",
                        "UserPromptSubmit",
                        turn_id="turn-1",
                        prompt=delegated,
                    ),
                    plugin_data=data,
                )
                self.assertEqual(denied["decision"], "block")  # type: ignore[index]
                self.assertFalse(
                    (data / "sessions" / "native-envelope-malformed.json").exists()
                )

        marker_free = cases["unexpected-metadata"].replace(
            handoff["prompt"],
            "Please inspect the typo",
        )
        inert = self.run_hook(
            self.event(
                "native-envelope-marker-free",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=marker_free,
            ),
            plugin_data=data,
        )
        self.assertIsNone(inert)
        self.assertFalse((data / "sessions" / "native-envelope-marker-free.json").exists())

    def test_reference_rejects_missing_oversized_tampered_and_ambiguous_artifacts(self) -> None:
        cases = ("missing", "oversized", "tampered", "ambiguous")
        for case in cases:
            with self.subTest(case=case):
                data = self.root / f"plugin-data-artifact-{case}"
                contract = self.contract(contract_id=f"reference-{case}-v1")
                _, handoff = self.stage_reference(
                    contract,
                    session_id=f"reference-{case}",
                    plugin_data=data,
                )
                artifact = Path(handoff["artifact_path"])
                prompt = handoff["prompt"]
                if case == "missing":
                    artifact.unlink()
                elif case == "oversized":
                    artifact.write_bytes(b"x" * (1024 * 1024 + 1))
                elif case == "tampered":
                    artifact.write_bytes(artifact.read_bytes() + b" ")
                else:
                    prompt += "\n" + json.dumps(contract)
                result = self.run_hook(
                    self.event(
                        f"reference-{case}",
                        "UserPromptSubmit",
                        turn_id="turn-1",
                        prompt=prompt,
                    ),
                    plugin_data=data,
                )
                self.assertEqual(result["decision"], "block")  # type: ignore[index]
                self.assertFalse((data / "sessions" / f"reference-{case}.json").exists())

    def test_reference_rejects_wrong_id_session_ownership_and_baseline(self) -> None:
        cases = ("id", "session", "ownership", "baseline")
        for case in cases:
            with self.subTest(case=case):
                data = self.root / f"plugin-data-binding-{case}"
                session_id = f"reference-binding-{case}"
                contract = self.contract(contract_id=f"binding-{case}-v1")
                registry, handoff = self.stage_reference(
                    contract,
                    session_id=session_id,
                    plugin_data=data,
                )
                event_session = session_id
                if case == "id":
                    handoff = self.rewrite_artifact(
                        handoff,
                        lambda artifact: artifact.__setitem__("contract_id", "wrong-contract-v1"),
                    )
                elif case == "session":
                    event_session += "-other"
                elif case == "ownership":
                    registry.update(
                        contract["contract_id"],
                        expected_baseline=self.head,
                        changes={"title": "Ownership changed after staging"},
                    )
                else:
                    handoff = self.rewrite_artifact(
                        handoff,
                        lambda artifact: artifact["contract"]["baseline"].__setitem__(
                            "head", "b" * 40
                        ),
                    )
                result = self.run_hook(
                    self.event(
                        event_session,
                        "UserPromptSubmit",
                        turn_id="turn-1",
                        prompt=handoff["prompt"],
                    ),
                    plugin_data=data,
                )
                self.assertEqual(result["decision"], "block")  # type: ignore[index]
                self.assertFalse((data / "sessions" / f"{event_session}.json").exists())

    def test_malformed_reference_fails_closed_while_inline_v1_still_activates(self) -> None:
        malformed = (
            "Use the approved private contract.\n"
            f"{MARKER}\n"
            "Execution contract reference: sha256:not-a-digest"
        )
        denied = self.run_hook(
            self.event(
                "malformed-reference",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=malformed,
            )
        )
        self.assertEqual(denied["decision"], "block")  # type: ignore[index]
        self.assertFalse((self.data / "sessions" / "malformed-reference.json").exists())

        delegated_marker_only = (
            "<codex_delegation>\n"
            "  <source_thread_id>control-task</source_thread_id>\n"
            f"  <input>{MARKER}</input>\n"
            "</codex_delegation>"
        )
        marker_only = self.run_hook(
            self.event(
                "delegated-marker-only",
                "UserPromptSubmit",
                turn_id="turn-1",
                prompt=delegated_marker_only,
            )
        )
        self.assertEqual(marker_only["decision"], "block")  # type: ignore[index]
        self.assertIn("must be followed", marker_only["reason"])  # type: ignore[index]
        self.assertFalse((self.data / "sessions" / "delegated-marker-only.json").exists())

        inline = self.activate("inline-v1-compatible")
        self.assertEqual(self.state("inline-v1-compatible")["contract"], inline)

    def test_bootstrap_allows_only_exact_commands_across_semicolon_or_newline_sequences(self) -> None:
        self.activate()
        allowed_commands = (
            "pwd; git branch --show-current\n"
            "git rev-parse HEAD; git status --porcelain=v1"
        )
        allowed = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-2",
                tool_name="Bash",
                tool_use_id="bootstrap-allowed",
                tool_input={"command": allowed_commands},
            )
        )
        self.assertIsNone(allowed)

        rejected_commands = (
            "pwd; touch /tmp/execution-guard-regression",
            "pwd > /tmp/execution-guard-regression",
            "pwd | cat",
            "pwd && git status --short",
            "pwd || git status --short",
            "pwd; $(touch /tmp/execution-guard-regression)",
        )
        for index, command in enumerate(rejected_commands):
            with self.subTest(command=command):
                denied = self.run_hook(
                    self.event(
                        "guarded",
                        "PreToolUse",
                        turn_id="turn-2",
                        tool_name="Bash",
                        tool_use_id=f"bootstrap-denied-{index}",
                        tool_input={"command": command},
                    )
                )
                self.assertEqual(
                    denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
                    "deny",
                )

    def test_guard_bootstrap_create_rejects_top_level_project_id_before_dispatch(self) -> None:
        denied = self.run_hook(
            self.event(
                "control",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="create_thread",
                tool_use_id="create-invalid-project",
                tool_input=self.guard_bootstrap_create_input(top_level_project_id=True),
            )
        )
        self.assertEqual(
            denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
            "deny",
        )
        reason = denied["hookSpecificOutput"]["permissionDecisionReason"]  # type: ignore[index]
        self.assertIn("target.projectId", reason)
        self.assertIn("before host dispatch", reason)

    def test_guard_bootstrap_create_rejects_incomplete_branch_starting_state(self) -> None:
        denied = self.run_hook(
            self.event(
                "control",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="create_thread",
                tool_use_id="create-invalid-branch",
                tool_input=self.guard_bootstrap_create_input(
                    starting_state={"branchName": "main"}
                ),
            )
        )
        self.assertEqual(
            denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
            "deny",
        )
        reason = denied["hookSpecificOutput"]["permissionDecisionReason"]  # type: ignore[index]
        self.assertIn('"type":"branch"', reason)
        self.assertIn("before host dispatch", reason)

    def test_guard_bootstrap_create_rejects_noncanonical_project_worktree_targets(self) -> None:
        cases = (
            ("missing-target", lambda payload: payload.pop("target"), "target must be an object"),
            (
                "wrong-target-type",
                lambda payload: payload["target"].__setitem__("type", "local"),
                'target.type must be "project"',
            ),
            (
                "missing-project-id",
                lambda payload: payload["target"].pop("projectId"),
                "target.projectId must be a non-empty string",
            ),
            (
                "wrong-environment-type",
                lambda payload: payload["target"]["environment"].__setitem__(
                    "type", "local"
                ),
                'target.environment.type must be "worktree"',
            ),
        )
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                tool_input = self.guard_bootstrap_create_input()
                mutate(tool_input)
                denied = self.run_hook(
                    self.event(
                        "control",
                        "PreToolUse",
                        turn_id="turn-1",
                        tool_name="create_thread",
                        tool_use_id=f"create-{name}",
                        tool_input=tool_input,
                    )
                )
                self.assertEqual(
                    denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
                    "deny",
                )
                reason = denied["hookSpecificOutput"]["permissionDecisionReason"]  # type: ignore[index]
                self.assertIn(expected, reason)
                self.assertIn("before host dispatch", reason)

    def test_guard_bootstrap_create_accepts_minimal_and_complete_branch_payloads(self) -> None:
        payloads = (
            self.guard_bootstrap_create_input(),
            self.guard_bootstrap_create_input(
                starting_state={"type": "branch", "branchName": "main"}
            ),
        )
        for index, tool_input in enumerate(payloads):
            with self.subTest(index=index):
                allowed = self.run_hook(
                    self.event(
                        "control",
                        "PreToolUse",
                        turn_id="turn-1",
                        tool_name="create_thread",
                        tool_use_id=f"create-valid-{index}",
                        tool_input=tool_input,
                    )
                )
                self.assertIsNone(allowed)

    def test_non_guard_create_thread_payload_is_not_preflighted(self) -> None:
        allowed = self.run_hook(
            self.event(
                "ordinary",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="create_thread",
                tool_use_id="create-ordinary",
                tool_input={
                    "projectId": "legacy-top-level-shape",
                    "target": {
                        "type": "project",
                        "environment": {
                            "type": "worktree",
                            "startingState": {"branchName": "main"},
                        },
                    },
                    "prompt": "Create an ordinary task without the Guard bootstrap marker.",
                },
            )
        )
        self.assertIsNone(allowed)

    def test_guard_bootstrap_marker_must_be_the_first_prompt_line(self) -> None:
        tool_input = self.guard_bootstrap_create_input(top_level_project_id=True)
        tool_input["prompt"] = (
            "Ordinary task instructions.\n"
            f"{execution.BOOTSTRAP_MARKER}\n"
            "Mentioning the marker later must not opt this call into preflight."
        )
        allowed = self.run_hook(
            self.event(
                "ordinary-marker-mention",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="create_thread",
                tool_use_id="create-marker-later",
                tool_input=tool_input,
            )
        )
        self.assertIsNone(allowed)

    def test_guard_preflight_denial_allows_payload_correction_without_host_retry(self) -> None:
        denied = self.run_hook(
            self.event(
                "control",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="create_thread",
                tool_use_id="create-correctable-invalid",
                tool_input=self.guard_bootstrap_create_input(
                    starting_state={"branchName": "main"}
                ),
            )
        )
        self.assertEqual(
            denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
            "deny",
        )
        corrected = self.run_hook(
            self.event(
                "control",
                "PreToolUse",
                turn_id="turn-1",
                tool_name="create_thread",
                tool_use_id="create-corrected",
                tool_input=self.guard_bootstrap_create_input(),
            )
        )
        self.assertIsNone(corrected)

    def test_active_execution_create_uses_unique_task_denial_before_payload_preflight(self) -> None:
        self.activate()
        denied = self.run_hook(
            self.event(
                "guarded",
                "PreToolUse",
                turn_id="turn-2",
                tool_name="create_thread",
                tool_use_id="create-active-invalid",
                tool_input=self.guard_bootstrap_create_input(top_level_project_id=True),
            )
        )
        self.assertEqual(
            denied["hookSpecificOutput"]["permissionDecision"],  # type: ignore[index]
            "deny",
        )
        reason = denied["hookSpecificOutput"]["permissionDecisionReason"]  # type: ignore[index]
        self.assertIn("unique execution task", reason)
        self.assertNotIn("target.projectId", reason)

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

    def test_structured_exit_code_and_legacy_outcomes_are_classified(self) -> None:
        self.activate()
        self.register()
        cases = (
            ({"exit_code": 0}, "passed"),
            ({"exit_code": 1}, "failed"),
            ({"exit_code": -9}, "failed"),
            ("Exit code: 0", "passed"),
            ({"returncode": 2}, "failed"),
        )
        for index, (tool_response, _) in enumerate(cases):
            validation = self.event(
                "guarded",
                "PostToolUse",
                turn_id="turn-3",
                tool_name="Bash",
                tool_use_id=f"structured-outcome-{index}",
                tool_input={"command": f"python3 -m unittest structured_outcome_{index}"},
                tool_response=tool_response,
            )
            self.assertIsNone(self.run_hook(validation))

        outcomes = [
            item["outcome"]
            for item in self.state()["evidence"]
            if item["kind"] == "validation"
        ]
        self.assertEqual(outcomes, [expected for _, expected in cases])

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
