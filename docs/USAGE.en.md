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
| Goal, scope, and acceptance are unchanged | Reuse the active task |
| Fix, adjustment, test, or docs for the same iteration | Reuse the active task |
| The previous iteration is closed or merged | Create a new task |
| The work adds independent user value | Create a new task |
| The work introduces new acceptance criteria | Create a new task |
| Evidence is missing or contradictory | Stop in control |

A private local ownership registry records the real task, worktree, branch, and baseline for each iteration. It is never committed to the project.

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
2. Create one visible task whose environment type is `worktree`.
3. Treat `clientThreadId` only as a queue token and wait for a real `threadId`.
4. Set a clear title.
5. Ask the task to report only `cwd`, worktree identity, branch, full `HEAD`, and Git status.
6. If detached, create and switch exactly one `codex/<iteration>` branch.
7. Require a clean worktree unless the approved contract says otherwise.
8. Send the execution contract only after control verifies and persists the real baseline.

The first bootstrap prompt contains no activation marker and does not authorize project writes, plan changes, validation, commits, or additional tasks.

## 8. The execution contract

Guarded execution activates only when this marker appears on its own line:

```text
CODEX_EXECUTION_GUARD_CONTRACT_V1
```

It is followed by a JSON contract containing the version and ID, goal, scope, frozen decisions, non-goals, forbidden operations, authorized and selected model, route evidence, real Git baseline, stable plan, allowed adjustments, escalation conditions, validation budget, and stable acceptance items.

In an ordinary session without a valid marker, the Hooks create no guard state and exit successfully.

## 9. Register the plan before writes

The executor reads `pwd`, worktree identity, branch, `HEAD`, and Git status; compares them with the contract baseline; sends the complete contract plan to `update_plan`; and preserves every step, order, and stable ID with at most one `in_progress` item.

The executor may change status and add a concise implementation note that does not alter scope, authorization, or acceptance. Deleting, rewriting, reordering, or adding steps returns to control.

## 10. Stay on the deliverable

New work enters the current implementation only when it is the current deliverable, an observed failure, an approved acceptance item, or a direct blocker.

Future hardening, theoretical risk, optional capabilities, extra hashes, fingerprints, and generic gate frameworks become backlog notes. A repeated command with the same result, Git state, current step, and acceptance target is duplicate evidence, not progress.

When implementation needs a new step, wider scope, changed acceptance, an unauthorized model, or a forbidden operation, the executor records evidence and escalates to control instead of editing the contract.

## 11. Compaction and resume

Before compaction, Hooks persist the structured checkpoint. Resume restores only the contract and goal, model route, scope, decisions, non-goals, forbidden operations, complete plan and acceptance state, worktree and Git identity, allowed deviations, and concise evidence.

Git is checked again before writes resume. The plugin does not reconstruct scope from a lossy conversation summary or replay the full planning transcript.

## 12. Completion and receipt

The `Stop` Hook asks the task to continue while approved plan or acceptance items remain incomplete and no evidence-backed escalation exists. Completion returns the contract ID, completed plan and acceptance IDs, changed paths, local commits, validation once per state, allowed deviations, unverified items, and remote-action status.

Final acceptance, local `main` integration, and every remote publishing decision remain in control.

## 13. Update

```bash
codex plugin marketplace upgrade codex-execution-guard
codex plugin add codex-execution-guard@codex-execution-guard
```

For a locally cloned marketplace, run `git pull --ff-only` in the repository before reinstalling. Then restart the desktop app, review changed Hooks, and verify the update in a new task. Do not use a task that was already running to prove that a new version loaded.

## 14. Troubleshooting

### The plugin is missing from `/plugins`

Make sure `codex plugin marketplace add` targeted the repository root containing `.agents/plugins/marketplace.json` and `plugins/codex-execution-guard/`. Run `codex plugin list`, restart the desktop app, and start a new task.

### The plugin is installed but Hooks appear inert

Check `/hooks`, trust the current definitions, and use a new task created after installation. Inert behavior in an ordinary unmarked session is correct.

### The executor cannot write

Compare the contract's absolute worktree, branch, and full `HEAD` with the task and confirm that the complete plan was registered unchanged. Return a mismatch to control instead of bypassing the Hook.

### Only `clientThreadId` is available

The task is still queued. Wait for a real `threadId` and environment identity before activating the contract.

### The actual model is unverified

The host did not expose runtime identity. Keep “requested model” and `actual model unverified` as separate facts.

### Tests pass but host behavior is unchanged

Fixtures validate fixed payloads and local state machines. Marketplace reload, Skill discovery, Hook trust, and host capabilities require a fresh real-host check after restart.
