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

Use `scripts/control_plane.py` with one explicit absolute registry path outside the repository. Prefer a host-provided writable plugin-data path; otherwise choose a private local state path and state it. Never commit the registry. The script supports `create`, `read`, `reuse`, `update`, and `close`. Every mutation acquires the stable sidecar process lock before reloading and validating state, holds it through mutation and atomic replacement, then releases it. This prevents concurrent control tasks from losing committed records while preserving safe failure for corrupt state, duplicate ownership, stale baselines, and incomplete records. Never delete or replace the sidecar lock file during normal operation.

Create a record only after the native task has a real `threadId` and the bootstrap returned a verified baseline. Read or reuse a record before sending follow-up work. Close it only after the control task accepts the iteration as closed or merged.

## Create a native worktree task

Follow this order exactly. Stop before implementation if any step fails.

1. Call the current host's native `list_projects`. Select the real repository project and require `isGitRepository=true` for a worktree flow.
2. Apply the create-or-reuse table. For reuse, resolve the active registry record against `list_threads`; send follow-up work only to that real `threadId` and skip creation.
3. Inspect the current native `create_thread` or equivalent tool schema for host-advertised model and reasoning combinations. Intersect that evidence with the user's authorized pool and apply [routing-policy.md](routing-policy.md).
4. Call native `create_thread` with `target.type="project"`, the discovered `projectId`, and `target.environment.type="worktree"`. Send a marker-free bootstrap that authorizes only environment setup and reporting. Do not fork or use a local environment as a substitute.
5. Treat `clientThreadId` only as queued setup. Use the host's supported readiness/status surface or bounded `list_threads` snapshots until a real `threadId` and host identity are available. Never pass `clientThreadId` to tools requiring `threadId`, write it to the ownership registry, or activate a contract from it.
6. Set a clear title on the real task with native `set_thread_title`.
7. Obtain the task's absolute worktree path. Have the bootstrap report `cwd`, linked-worktree identity, branch, `HEAD`, and porcelain status.
8. Require a clean worktree unless the approved contract says otherwise. If `git branch --show-current` is empty, create and switch exactly one unique `codex/<iteration>` branch inside that target task, then report the new branch and unchanged `HEAD`.
9. Return the real baseline to control. Validate the bootstrap report before persisting an active ownership record.
10. Compile the baseline into the complete contract and send the exact marker plus contract to the same real `threadId`. Only then may execution register `update_plan` and implement.

Do not guess a project, task identifier, path, branch, commit, cleanliness, or runtime model. If the host exposes no way to turn queued setup into a real task identity, report that host limitation and stop.

## Bootstrap prompt requirements

Include the goal and proposed iteration identifier, then state all of these boundaries:

- The task is the iteration's intended worktree and must not create, fork, delegate, hand off, or add a worktree.
- Only inspect and report environment identity; establish the one named feature branch only when detached.
- Do not modify project files, register or change a plan, implement, validate, commit, or publish.
- Return exact `cwd`, linked-worktree status, branch, full `HEAD`, and Git status.

Keep the execution marker out of this prompt.

## Reuse and close

For reuse, require an active registry record, a matching native `threadId`, and matching project/worktree/branch ownership. Send the next contract or approved follow-up to that task; do not create a parallel task for fixes, tests, or docs belonging to the iteration.

For close, record status `closed` after control accepts completion or confirms merge. A later iteration always gets a new task, worktree, branch, and baseline.
