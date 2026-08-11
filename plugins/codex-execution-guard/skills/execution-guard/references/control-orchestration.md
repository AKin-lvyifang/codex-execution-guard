# Control orchestration

## Boundary

Keep product decisions, task ownership, model routing, native task creation or reuse, and baseline acquisition in the control task. Send implementation to exactly one execution task only after every material decision is frozen. Never activate the execution marker while ownership or baseline is uncertain.

Hooks guard only a marked execution session. They do not create, select, rename, wait for, close, or recover Codex tasks.

## Decide create or reuse

Check the local ownership registry and current native task state before acting.

| Evidence | Decision |
| --- | --- |
| Same user goal, scope, and acceptance | Reuse the active task |
| Acceptance detail, retry, optimization, failed-acceptance fix, test, or documentation for the same feature chain | Reuse the active lane |
| Independent acceptance environment or responsibility is required | Establish at most one acceptance lane, then reuse it |
| Known same-chain work restarts after the prior feature chain is merged or cancelled | Create a new task |
| Independent user value | Create a new task |
| Missing or contradictory evidence | Stop in control |

New acceptance criteria alone are not independent user value. Keep one implementation task, worktree, and branch for the feature chain. When ordinary acceptance can run there, reuse it. Only a concrete isolation need permits one separate acceptance task, worktree, and branch; reuse that same lane for every later recheck, and return any code fix to the implementation lane. Do not infer that similar files mean the same iteration, create a second lane of either kind, or reopen a closed mapping as reuse. If the registry and native task state disagree, stop and reconcile them without starting implementation.

### Freeze feature-chain and lane identities

Before the first ownership claim, freeze one stable feature-chain key in the control decision and derive exact lane IDs deterministically. For a new chain, use `<feature-chain-key>-implementation` for its implementation iteration and, only when isolation is approved, `<feature-chain-key>-acceptance` for its sole acceptance iteration. For an already-active chain, preserve its current implementation iteration ID as the frozen mapping instead of renaming or migrating it, and freeze only the one acceptance ID if that lane is later needed.

Every optimization, fix, or implementation follow-up resolves or claims the same implementation ID. Every independent recheck resolves or claims the same acceptance ID; an existing claim returns `reconcile_only`, and an active record routes to reuse. Never derive `acceptance-v2`, `acceptance-v3`, a timestamped acceptance ID, or another retry-specific ID. The V2 registry does not store a feature-chain key or enforce lane counts: the one-implementation/one-acceptance cap is an orchestration policy, not a registry-schema hard limit, and requires no schema migration.

## Persist ownership

Use `scripts/control_plane.py` with the V2 registry at the established target-host private path `PLUGIN_DATA/control/iterations.json`. Never commit the registry or its `contracts/` artifacts. The registry has three durable states: `claimed`, `active`, and `closed`. Every mutation acquires the stable sidecar process lock before reloading and validating state, holds it through mutation and atomic replacement, then releases it. A V1 registry at the same path remains readable and migrates in place as one unit on the next locked write.

Call `claim` before the native create tool. The first claim returns `create_once`; that is the only authorization for one `create_thread` call. A later claim for the same iteration returns `reconcile_only` forever. An error, timeout, crash, reload, or queued `clientThreadId` never clears, expires, or renews the claim.

Finalize a claim to `active` only after native reconciliation returns exactly one real task and its bootstrap proves the worktree, branch, full `HEAD`, and status. Zero or multiple candidates stop. Do not retry creation, pick a candidate by guesswork, or archive candidates automatically. Read or reuse an active record before follow-up work. Keep ownership active through completion receipts, acceptance failures, escalations, and phase closeout; close it only after the whole feature chain is explicitly merged or cancelled.

The control helper exposes the protocol directly:

```text
python3 scripts/control_plane.py --registry /absolute/private/plugin-data/control/iterations.json claim --iteration feature-v1 --project project-id --title "Feature title"
python3 scripts/control_plane.py --registry /absolute/private/plugin-data/control/iterations.json finalize --iteration feature-v1 --candidate-json '<one verified bootstrap report object>'
python3 scripts/control_plane.py --registry /absolute/private/plugin-data/control/iterations.json stage-contract --plugin-data /absolute/private/plugin-data --iteration feature-v1 --target-session thread-id --contract-file /absolute/private/contract.json
python3 scripts/control_plane.py --registry /absolute/private/plugin-data/control/iterations.json close --iteration feature-v1 --expected-baseline <full-head> --outcome merged
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

For reuse, require an active V2 registry record, a matching native `threadId`, and matching project/worktree/branch ownership. Stage the next same-host contract against that ownership and send its short reference; do not create a parallel task for acceptance detail, retry, optimization, failed-acceptance fixes, tests, or docs belonging to the feature chain.

After a contract becomes complete or escalated, keep ownership active but treat the session as write-locked. A marker-free prompt cannot authorize more work. Control may verify the same worktree and branch, refresh the stored baseline when `HEAD` changed, and stage revised contract content with the same `contract_id` for the same task. Terminal rollover must use the private short reference so the Hook can revalidate active V2 ownership; inline V1 cannot roll over terminal state. The Hook verifies the incoming baseline and privately content-addresses the prior terminal state before atomically starting the revised plan. If the new session-state write fails, the prior terminal state remains authoritative and locked; retry the same reference rather than minting another task or archive. A non-terminal session, closed ownership, or different `contract_id` cannot roll over.

For close, pass an explicit `--outcome merged` or `--outcome cancelled`. Completion receipts, acceptance failures, escalations, and phase closeout are non-closing events. Once the feature chain is merged or cancelled, close every lane it owns; later independent work gets new ownership and a new baseline.
