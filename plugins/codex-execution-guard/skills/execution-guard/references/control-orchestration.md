# Control orchestration

## Boundary

Keep product decisions, task ownership, model routing, native task creation or reuse, and baseline acquisition in the control task. Send implementation to exactly one execution task only after every material decision is frozen. Never activate the execution marker while ownership or baseline is uncertain.

Hooks guard only a marked execution session. They do not create, select, rename, wait for, close, or recover Codex tasks.

## Decide create or reuse

Check the local ownership registry and current native task state before acting.

| Evidence | Decision |
| --- | --- |
| Same user goal, scope, and acceptance | Reuse the active task |
| Fix, adjustment, test, or documentation for that same iteration | Reuse the active task |
| Prior iteration is closed or merged | Create a new task |
| Independent user value | Create a new task |
| New acceptance criteria | Create a new task |
| Missing or contradictory evidence | Stop in control |

Do not infer that similar files mean the same iteration. Do not reopen a closed mapping as reuse. If the registry and native task state disagree, stop and reconcile them without starting implementation.

## Persist ownership

Use `scripts/control_plane.py` with the V2 registry at the established target-host private path `PLUGIN_DATA/control/iterations.json`. Never commit the registry or its `contracts/` artifacts. The registry has three durable states: `claimed`, `active`, and `closed`. Every mutation acquires the stable sidecar process lock before reloading and validating state, holds it through mutation and atomic replacement, then releases it. A V1 registry at the same path remains readable and migrates in place as one unit on the next locked write.

Call `claim` before the native create tool. The first claim returns `create_once`; that is the only authorization for one `create_thread` call. A later claim for the same iteration returns `reconcile_only` forever. An error, timeout, crash, reload, or queued `clientThreadId` never clears, expires, or renews the claim.

Finalize a claim to `active` only after native reconciliation returns exactly one real task and its bootstrap proves the worktree, branch, full `HEAD`, and status. Zero or multiple candidates stop. Do not retry creation, pick a candidate by guesswork, or archive candidates automatically. Read or reuse an active record before follow-up work. Close it only after control accepts the iteration as closed or merged.

The control helper exposes the protocol directly:

```text
python3 scripts/control_plane.py --registry /absolute/private/plugin-data/control/iterations.json claim --iteration feature-v1 --project project-id --title "Feature title"
python3 scripts/control_plane.py --registry /absolute/private/plugin-data/control/iterations.json finalize --iteration feature-v1 --candidate-json '<one verified bootstrap report object>'
python3 scripts/control_plane.py --registry /absolute/private/plugin-data/control/iterations.json stage-contract --plugin-data /absolute/private/plugin-data --iteration feature-v1 --target-session thread-id --contract-file /absolute/private/contract.json
```

`stage-contract` prints the artifact location for control and the short prompt for the target task. Do not paste the artifact location into chat. `fold-inline --contract-file /absolute/private/contract.json` is the explicit cross-host fallback and does not require a registry argument.

## Create a native worktree task

Follow this order exactly. Stop before implementation if any step fails.

1. Call the current host's native `list_projects`. Select the real repository project and require `isGitRepository=true` for a worktree flow.
2. Apply the create-or-reuse table. For reuse, resolve the active registry record against `list_threads`; send follow-up work only to that real `threadId` and skip creation.
3. Inspect the current native `create_thread` or equivalent tool schema for host-advertised model and reasoning combinations. Intersect that evidence with the user's authorized pool and apply [routing-policy.md](routing-policy.md).
4. Atomically `claim` the iteration. If the result is `reconcile_only`, do not call `create_thread`; reconcile native task state instead. Continue only when exactly one candidate can be verified.
5. Only for `create_once`, call native `create_thread` once with `target.type="project"`, the discovered `projectId`, and `target.environment.type="worktree"`. Send a marker-free bootstrap that authorizes only environment setup and reporting. Do not fork or use a local environment as a substitute.
6. Whether the create call returns a task, a queue token, an error, or times out, never call it again for this claim. Use the host's supported readiness surface or bounded `list_threads` snapshots. Zero or multiple candidates stop without retry or archive.
7. Treat `clientThreadId` only as queued setup. Never pass it to tools requiring `threadId`, persist it as ownership, or activate a contract from it.
8. Set a clear title on the one real task with native `set_thread_title`.
9. Obtain the task's absolute worktree path. Have the bootstrap report `cwd`, linked-worktree identity, branch, `HEAD`, and porcelain status.
10. Require a clean worktree unless the approved contract says otherwise. If `git branch --show-current` is empty, create and switch exactly one unique `codex/<iteration>` branch inside that target task, then report the new branch and unchanged `HEAD`.
11. Validate the complete bootstrap report, then atomically `finalize` the claim to `active`. Repeating finalize with the same ownership is idempotent; conflicting ownership stops.
12. Compile the complete contract. On the same host, stage it in target `PLUGIN_DATA`, send only the short reference prompt to the active `threadId`, and keep the full JSON out of visible chat. Only then may execution register `update_plan` and implement.

Do not guess a project, task identifier, path, branch, commit, cleanliness, or runtime model. If the host exposes no way to turn queued setup into a real task identity, report that host limitation and stop.

## Bootstrap prompt requirements

Include the goal and proposed iteration identifier, then state all of these boundaries:

- The task is the iteration's intended worktree and must not create, fork, delegate, hand off, or add a worktree.
- Only inspect and report environment identity; establish the one named feature branch only when detached.
- Do not modify project files, register or change a plan, implement, validate, commit, or publish.
- Return exact `cwd`, linked-worktree status, branch, full `HEAD`, and Git status.

Keep the execution marker out of this prompt.

## Reuse and close

For reuse, require an active V2 registry record, a matching native `threadId`, and matching project/worktree/branch ownership. Stage the next same-host contract against that ownership and send its short reference; do not create a parallel task for fixes, tests, or docs belonging to the iteration.

For close, record status `closed` after control accepts completion or confirms merge. A later iteration always gets a new task, worktree, branch, and baseline.
