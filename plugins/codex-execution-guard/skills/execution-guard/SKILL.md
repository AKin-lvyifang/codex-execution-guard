---
name: execution-guard
description: Control and execute one bounded Codex implementation iteration using native project and task tools, model routing, a persistent local ownership record, a real Git baseline, stable update_plan steps, opt-in lifecycle recovery, validation budgets, and a final receipt. Use when deciding whether approved work should create or reuse a Codex task, compiling or sending an execution contract, starting guarded implementation, or resuming it after compaction.
---

# Codex Execution Guard

Keep planning control and guarded execution distinct. This Skill and its Hooks are guardrails, not a security boundary.

## Route the workflow

1. Use the **control** path when approved work still needs a create-or-reuse decision, model route, native task setup, ownership lookup, or real Git baseline. Read [control-orchestration.md](references/control-orchestration.md), [routing-policy.md](references/routing-policy.md), and [execution-contract.md](references/execution-contract.md).
2. Use the **execution** path only for an exact `CODEX_EXECUTION_GUARD_CONTRACT_V1` marker with a valid contract, or when resuming its persisted state. Read [execution-contract.md](references/execution-contract.md) and [lifecycle-and-progress.md](references/lifecycle-and-progress.md).
3. Use [examples.md](references/examples.md) only when producing a bootstrap, contract, plan update, escalation, or receipt.

Without the marker, do not create guard state, steer the task, or block tools.

## Control the iteration

- Keep uncertainty in the control task. Never let an execution task decide product scope or create another task.
- Use Codex-native project and task tools for discovery, creation, waiting, naming, and messaging. Use the bundled local registry only for durable iteration ownership; do not replace native tools with MCP or a project manager.
- Activate execution only after a real `threadId` and a verified worktree, branch, `HEAD`, and status have returned to control.

## Execute the contract

- Keep one execution task, one worktree, and one feature branch for the iteration. Do not create, fork, delegate, or hand off another task.
- Before writing code, verify the actual worktree, branch, HEAD, and status against the contract, then register every approved plan step in `update_plan` exactly as supplied.
- Preserve the complete ordered step list and stable IDs. Change only statuses and implementation notes that leave goal, scope, authorization, and acceptance unchanged. Keep at most one step `in_progress`.
- Work only on the current deliverable, an observed failure, an approved acceptance item, or a direct blocker. Record optional hardening, theoretical risks, and unrelated cleanup without turning them into plan steps.
- Run affected checks during development and the frozen final checks at integration. Do not repeat an unchanged check as progress.
- Register an evidence-backed escalation and return to the control task when a change needs a new stable step ID, changes scope or acceptance, exceeds the authorized model pool, requires a forbidden operation, or is otherwise blocked inside the approved contract.

## Finish

Complete every approved step and acceptance item, make only authorized local commits, and return the execution receipt defined in the lifecycle reference. List anything the host prevented you from verifying; never claim a fresh-session Hook trust check from fixture evidence alone.
