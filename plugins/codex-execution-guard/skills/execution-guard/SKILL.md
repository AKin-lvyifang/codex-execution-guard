---
name: execution-guard
description: Control and execute one bounded Codex implementation iteration using native project and task tools, model routing, a persistent local ownership record, a real Git baseline, stable update_plan steps, opt-in lifecycle recovery, validation budgets, and a final receipt. Use whenever the user explicitly invokes $execution-guard, when deciding whether approved real-repository work qualifies for guarded feature-chain establishment or exact active-chain lane routing, when compiling or sending an execution contract, when starting guarded implementation, or when resuming it after compaction.
---

# Codex Execution Guard

Keep planning control and guarded execution distinct. This Skill and its Hooks are guardrails, not a security boundary.

## Qualify control entry

Always load and respond to this Skill when the user explicitly invokes `$execution-guard`. Invocation alone does not authorize task ownership or environment changes.

When no matching active feature-chain ownership and control identity exists, require both keys before establishing that feature chain:

1. **Explicit control intent:** the current task is explicitly designated as control for the same still-pending implementation, including by a prior explicit `$execution-guard` invocation in its unresolved clarification chain, or the current prompt explicitly invokes `$execution-guard`.
2. **Approved repository implementation:** the user has approved starting or continuing a sufficiently frozen implementation in a real Git repository.

For that new-chain candidate, if either key is missing, stay in the current task. Do not claim, create, or reuse an execution task, and do not create a branch or worktree. Research, analysis, review, and one-off Paper, Figma, or HTML exploration remain in the current task even when they generate code or use frontend-design. An approved production page may establish a feature chain when it is a real repository implementation and both keys are present.

When an explicit invocation opens clarification for a still-pending implementation, retain it as explicit-control evidence across later clarification turns in that same chain. Once ownership is finalized as active and implementation starts, end the pending designation by transferring its routing identity to that exact active ownership and control chain. Cancellation or replacement by an independent goal ends it without handoff.

A user-approved continuation, optimization, failed-acceptance repair, test, or documentation update whose active implementation ownership and native task identity match exactly reuses the original implementation lane. An isolated recheck whose existing sole approved acceptance ownership and native task identity match exactly reuses that acceptance lane. Neither requires another Guard invocation or control designation, creates a second implementation lane, or absorbs an independent goal.

When that exact active implementation chain has a concrete approved isolation need and no acceptance lane yet exists, its inherited routing identity may deterministically claim the sole `<feature-chain-key>-acceptance` lane without another Guard invocation or control designation. The first claim authorizes at most one create; every later claim reconciles or reuses existing ownership. Never create `acceptance-v2`, `acceptance-v3`, or a timestamped retry lane.

This active feature-chain identity lasts until the chain is explicitly merged or cancelled. The two-key gate applies only to first feature-chain establishment without matching active ownership and control identity. A valid marked execution contract or persisted execution resume follows the existing execution path without restating the two keys.

## Route the workflow

1. Use the **control** path when approved work still needs a create-or-reuse decision, model route, native task setup, ownership lookup, or real Git baseline. Read [control-orchestration.md](references/control-orchestration.md), [routing-policy.md](references/routing-policy.md), and [execution-contract.md](references/execution-contract.md).
2. Use the **execution** path only for an exact `CODEX_EXECUTION_GUARD_CONTRACT_V1` marker with a valid contract, or when resuming its persisted state. Read [execution-contract.md](references/execution-contract.md) and [lifecycle-and-progress.md](references/lifecycle-and-progress.md).
3. Use [examples.md](references/examples.md) only when producing a bootstrap, contract, plan update, escalation, or receipt.

Without the marker, do not create guard state, steer the task, or block tools.

## Control the iteration

- Keep uncertainty in the control task. Never let an execution task decide product scope or create another task.
- Use Codex-native project and task tools for discovery, creation, waiting, naming, and messaging. Use the bundled V2 registry only for durable iteration ownership; do not replace native tools with MCP or a project manager.
- Before the first claim, freeze one stable feature-chain key and deterministic implementation iteration ID. Keep that one implementation lane for the whole chain. Only a real environment or responsibility-separation need may freeze one deterministic acceptance iteration ID; every later recheck claims that exact ID again and reuses or reconciles its existing lane, never an `acceptance-v2` or `acceptance-v3`. Every code fix returns to implementation. This cap is control-orchestration policy, not a registry-schema hard limit; do not migrate the registry to enforce it.
- Atomically claim a new iteration before `create_thread`. Only the first claim authorizes that one call. Every later claim is `reconcile_only`, including after an error, timeout, crash, reload, or queued `clientThreadId`; never clear or expire a claim automatically.
- Finalize ownership only after reconciliation finds exactly one real `threadId` with a verified worktree, branch, `HEAD`, and status. Zero or multiple candidates stop without another create or automatic archive.
- On the same host, stage the canonical contract under private `PLUGIN_DATA` and send only a UTF-8-bounded single-line goal plus the short SHA-256 reference. Use the labeled folded-inline fallback only when target `PLUGIN_DATA` cannot be staged across hosts.

## Execute the contract

- Keep one execution task, one worktree, and one feature branch for the iteration. Do not create, fork, delegate, or hand off another task.
- Before writing code, verify the actual worktree, branch, HEAD, and status against the contract, then register every approved plan step in `update_plan` exactly as supplied.
- Preserve the complete ordered step list and stable IDs. Change only statuses and implementation notes that leave goal, scope, authorization, and acceptance unchanged. Keep at most one step `in_progress`.
- Work only on the current deliverable, an observed failure, an approved acceptance item, or a direct blocker. Record optional hardening, theoretical risks, and unrelated cleanup without turning them into plan steps.
- Run affected checks during development and the frozen final checks at integration. Do not repeat an unchanged check as progress.
- Register an evidence-backed escalation and return to the control task when a change needs a new stable step ID, changes scope or acceptance, exceeds the authorized model pool, requires a forbidden operation, or is otherwise blocked inside the approved contract.
- A completed or escalated contract locks `update_plan` and every write tool; marker-free prompts cannot reopen it. A control-approved revision may continue in the same task only through a private short reference that revalidates active V2 ownership, the same `contract_id`, worktree, and branch, and the incoming baseline. Inline V1 remains valid only for first activation. The Hook privately archives the prior terminal state and atomically installs the revision; failure keeps the old terminal state locked and retryable.

## Finish

Complete every approved step and acceptance item, make only authorized local commits, and return the execution receipt defined in the lifecycle reference. A completion receipt, acceptance failure, escalation, or phase closeout does not close ownership; control closes it only after an explicit merged or cancelled feature-chain outcome. List anything the host prevented you from verifying; never claim a fresh-session Hook trust check from fixture evidence alone.
