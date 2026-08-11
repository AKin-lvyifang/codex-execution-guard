# Codex Execution Guard Usage Guide

[简体中文](USAGE.zh-CN.md)

The README provides orientation. This guide explains how an approved plan becomes a guarded execution task, what is verified at each stage, and how to recover when something does not line up.

## 1. Prerequisites

- A current Codex CLI or ChatGPT desktop app with plugin and Hook support.
- A local `python3` executable.
- A Git repository; new-task isolation depends on a native Codex worktree environment.
- Local write access to the project.

The runtime needs no MCP server, remote service, database, account system, or additional API key. GitHub access is needed to obtain updates, while execution state remains local.

## 2. Install

```bash
codex plugin marketplace add AKin-lvyifang/codex-execution-guard --ref main
codex plugin add codex-execution-guard@codex-execution-guard
```

To inspect the source or contribute, use a local marketplace instead:

```bash
git clone https://github.com/AKin-lvyifang/codex-execution-guard.git
cd codex-execution-guard
codex plugin marketplace add "$(pwd)"
codex plugin add codex-execution-guard@codex-execution-guard
```

You may also install **Codex Execution Guard** from `/plugins`. Restart the desktop app and start a new task after adding or updating a local marketplace. Existing tasks do not reliably hot-load new Skills and Hook definitions.

Open `/hooks`, inspect the command Hooks, and trust the current version. Execution Guard handles `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SessionStart`, and `Stop`. A changed definition may require renewed trust.

## 3. Configure the trigger

Add this rule to global or project `AGENTS.md`:

```text
When the user explicitly authorizes implementation of a new feature, an independent code task, or continuation of an existing feature, the project control task must invoke $execution-guard. Task creation or reuse, model and reasoning selection, worktree and branch management, plan persistence, execution recovery, and final handoff follow that Skill. Never push, open a pull request, run remote CI, tag, release, or deploy without explicit user authorization.
```

The trigger handles routing only. Ownership, model policy, contract format, recovery, and completion stay inside the plugin instead of expanding the global prompt.

Without an `AGENTS.md` trigger, explicitly send:

```text
The plan is approved. Start implementation with $execution-guard.
```

## 4. Plan in the control task

Before implementation, freeze the user-visible outcome, allowed repositories or components, confirmed decisions, non-goals, an ordered plan with stable IDs, observable acceptance criteria, the authorized model pool, allowed local validation, and forbidden remote operations.

Material product ambiguity remains in control. The executor is not asked to invent product scope.

## 5. Create or reuse

| Evidence | Action |
| --- | --- |
| The same feature keeps its goal, scope, and implementation responsibility | Reuse the implementation task |
| Acceptance detail, recheck, optimization, failed-acceptance fix, test, or docs for the same feature | Reuse the existing task |
| Acceptance truly needs an independent environment or responsibility | Establish at most one acceptance task, then reuse it |
| A known feature chain was explicitly merged or cancelled and later restarts | Create a new task |
| The work adds independent user value | Create a new task |
| Evidence is missing or contradictory | Stop in control |

Before the first claim, control freezes one feature-chain key and deterministically derives `<key>-implementation`. It adds the sole `<key>-acceptance` only when acceptance must be isolated. Every later optimization, failure fix, and recheck claims the same ID; never mint `acceptance-v2`, `acceptance-v3`, or a timestamped retry. This cap is an orchestration rule, not a hard registry-schema limit.

The V2 ownership registry remains at the established private target-host path `PLUGIN_DATA/control/iterations.json` and is never committed. A new lane starts as `claimed` without task or Git identity and becomes `active` only after verification. A receipt, acceptance failure, escalation, or phase closeout does not close it; only an explicit `merged` or `cancelled` outcome for the feature chain makes it `closed`. A V1 file at that same path migrates in place on the next locked write.

## 6. Select an execution model

Control first inspects model and reasoning combinations advertised by the current host, then intersects them with the user's authorized pool. The included table is policy, not a live availability list.

| Frozen task shape | Preferred profile |
| --- | --- |
| Clear, mechanical, narrow | Luna Max |
| Normal feature or bounded fix | Terra Max |
| Cross-module with decisions already frozen | Sol High |
| Material ambiguity remains | Keep planning in the Sol Ultra control task |
| One bounded high-risk review | At most one Sol XHigh or Ultra pass |

If live discovery is unavailable, a local-pool fallback is allowed only when the user authorized it and must be labeled as non-live evidence. A model accepted at task creation is still only requested unless the host returns actual runtime identity.

## 7. Create and verify the worktree task

1. Resolve the real Git project with native Codex project tools.
2. Use the feature chain's frozen implementation or acceptance iteration ID and persist its locked V2 claim. The first result is one `create_once`; every later result is permanently `reconcile_only`.
3. Only for `create_once`, create one visible worktree task, with exactly one native create call.
4. Do not retry after a task, `clientThreadId`, error, or timeout response. Reconcile through the host's status surface or bounded task lists; zero or multiple candidates stop without automatic archive.
5. Treat `clientThreadId` only as a queue token and wait for the one real `threadId`.
6. Set a clear title and ask the task to report only `cwd`, linked-worktree identity, branch, full `HEAD`, and Git status.
7. If detached, create and switch exactly one `codex/<iteration>` branch.
8. Require a clean worktree unless the approved contract says otherwise.
9. Finalize the claim to `active` only after exactly one candidate returns a complete verified report. Repeating the same finalize is idempotent; conflicting ownership stops.
10. Compile and privately stage the contract against active ownership, then send its short reference.

The first bootstrap prompt contains no activation marker and does not authorize project writes, plan changes, validation, commits, or additional tasks.

## 8. The execution contract

Guarded execution activates only when this marker appears on its own line:

```text
CODEX_EXECUTION_GUARD_CONTRACT_V1
```

The default same-host handoff does not put full JSON in visible chat. Control writes canonical JSON under private `PLUGIN_DATA/contracts/`; chat contains the contract ID, a single-line task goal derived from `goal`, the marker, and one short reference:

```text
Task goal: <single-line task-goal summary>
Execution contract reference: sha256:<64 lowercase hexadecimal characters>
```

The complete visible message is capped at 599 UTF-8 bytes. A long goal is truncated on a full character boundary with an ellipsis; newlines are folded, JSON brackets are neutralized, and the exact owned worktree path is replaced before rendering.

Before creating session state, the Hook validates reference format, the 1 MiB size limit, SHA-256, contract ID, target session, V2 active ownership, and live Git baseline. A missing, oversized, malformed, tampered, or wrongly bound artifact stops without partial activation. A prompt containing both a reference and inline JSON is rejected.

The complete contract still contains version and ID, goal, scope, frozen decisions, non-goals, forbidden operations, authorized and selected model, route evidence, real Git baseline, stable plan, allowed adjustments, escalation conditions, validation budget, and stable acceptance items. Inline V1 remains compatible only for first activation. Once a contract is completed or escalated, continuation requires a private short reference that revalidates active V2 ownership; neither inline input nor the cross-host fallback can bypass the terminal write lock. A same-host artifact failure cannot use the fallback either.

In an ordinary session without a valid marker, the Hooks create no guard state and exit successfully.

## 9. Register the plan before writes

The executor reads `pwd`, worktree identity, branch, `HEAD`, and Git status; compares them with the contract baseline; sends the complete contract plan to `update_plan`; and preserves every step, order, and stable ID with at most one `in_progress` item.

The executor may change status and add a concise implementation note that does not alter scope, authorization, or acceptance. Deleting, rewriting, reordering, or adding steps returns to control.

## 10. Stay on the deliverable

New work enters the current implementation only when it is the current deliverable, an observed failure, an approved acceptance item, or a direct blocker.

Beyond the approved private-contract digest, future hardening, theoretical risk, optional capabilities, extra hashes, fingerprints, and generic gate frameworks become backlog notes. A repeated command with the same result, Git state, current step, and acceptance target is duplicate evidence, not progress.

When implementation needs a new step, wider scope, changed acceptance, an unauthorized model, or a forbidden operation, the executor records evidence and escalates to control instead of editing the contract.

## 11. Compaction and resume

Before compaction, Hooks persist the structured checkpoint. Resume injects every contract boundary, the exact current plan and acceptance arrays, worktree and Git identity, allowed deviations, escalation, and evidence into private Hook context. The plugin source does not silently truncate those fields by character count.

Git is checked again before writes resume. The plugin does not reconstruct scope from a lossy conversation summary or replay the full planning transcript. Any external host context limit remains a separate fresh-host verification item.

## 12. Completion and receipt

The `Stop` Hook asks the task to continue while approved plan or acceptance items remain incomplete and no evidence-backed escalation exists. Completion returns the contract ID, completed plan and acceptance IDs, changed paths, local commits, validation once per state, allowed deviations, unverified items, and remote-action status.

Final acceptance, local `main` integration, and every remote publishing decision remain in control.

A completion receipt or valid escalation allows the executor to hand results back; it does not close task ownership. The contract becomes terminal and write-locked, so an ordinary plain-language prompt cannot authorize another `update_plan` or code write. Control may verify the same worktree and branch, refresh the new `HEAD` baseline, and send the same task a private short reference with the same `contract_id`. The Hook archives the prior terminal state before atomically starting the revised plan. If the new state write fails, the old terminal state remains authoritative, and retrying the same reference does not duplicate its archive.

Control closes the feature chain's implementation and acceptance lanes only after the whole chain is explicitly merged or cancelled.

## 13. Update

```bash
codex plugin marketplace upgrade codex-execution-guard
codex plugin add codex-execution-guard@codex-execution-guard
```

For a locally cloned marketplace, run `git pull --ff-only` in the repository before reinstalling. Then restart the desktop app, review changed Hooks, and verify the update in a new task. Do not use a task that was already running to prove that a new version loaded.

When upgrading from `0.2.x`, an old active record may have no `host_id` and cannot directly stage a new private reference. If you will not reuse the old task, complete or close it. To continue the same task, do not close it first: reconcile exactly one real native candidate and reverify its host, `threadId`, worktree, branch, and `HEAD`. Make the registry baseline match that verified `HEAD`, then finalize the original iteration once to add the host identity. Do not create another task for the same feature to bypass this step.

## 14. Troubleshooting

### The plugin is missing from `/plugins`

Make sure `codex plugin marketplace add` targeted the repository root containing `.agents/plugins/marketplace.json` and `plugins/codex-execution-guard/`. Run `codex plugin list`, restart the desktop app, and start a new task.

### The plugin is installed but Hooks appear inert

Check `/hooks`, trust the current definitions, and use a new task created after installation. Inert behavior in an ordinary unmarked session is correct.

### The executor cannot write

Compare the contract's absolute worktree, branch, and full `HEAD` with the task and confirm that the complete plan was registered unchanged. Return a mismatch to control instead of bypassing the Hook.

### Only `clientThreadId` is available

The task is still queued and the durable claim remains `reconcile_only`. Wait for one real `threadId` and environment identity without another create call before activating the contract.

### `create_thread` reports an error or timeout

Do not retry. The host may already have produced a side effect. Reading the same iteration claim returns `reconcile_only`; inspect native tasks instead. Continue bootstrap only for exactly one candidate. Zero or multiple candidates return to human control.

### A contract reference does not activate

Check that the target session uses the same `PLUGIN_DATA`, the V2 ownership record remains active, and worktree, branch, and `HEAD` still match the artifact. Control may stage a new artifact against current active ownership. Do not paste old JSON to bypass the failure.

### The actual model is unverified

The host did not expose runtime identity. Keep “requested model” and `actual model unverified` as separate facts.

### Tests pass but host behavior is unchanged

Fixtures validate fixed payloads and local state machines. Marketplace reload, Skill discovery, Hook trust, and host capabilities require a fresh real-host check after restart.
