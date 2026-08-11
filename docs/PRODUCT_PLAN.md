# Codex Execution Guard — Control and Execution Design

## 1. Outcome

Turn implementation authorization in a project control task into one durable feature-chain owner and bounded execution contracts that the correct Codex tasks can continue in stable worktrees, with explicit progress, recovery after compaction, and evidence-based completion.

The product is not a replacement for native Plan mode or native task tools. It governs task ownership and the transition from planning to execution.

## 2. First-principles model

Reliable agent delivery requires four durable elements:

1. Approved intent: goal, scope, decisions, non-goals, authorization, and acceptance criteria.
2. Isolated state: one reusable implementation task, worktree, and branch per feature chain, plus at most one acceptance lane when isolation is required.
3. Recoverable progress: stable plan step identifiers, current status, deviations, and validation evidence.
4. A bounded exit rule: completion is judged against the approved contract, not newly invented gates.

Conversation history is lossy and may be compacted. Git state is durable and consequential. Therefore critical execution state must be concise, structured, and recoverable without replaying the planning transcript.

## 3. Target user and primary scenario

The first target is a Codex desktop user who keeps product decisions in a project control task and delegates implementation to a separate visible task with an isolated worktree.

Primary flow:

1. The user approves execution in the project control task.
2. Control resolves the real project and decides whether the approved work reuses the active iteration or creates a new one.
3. Control discovers host-advertised model capabilities, intersects them with the authorized pool, and reports requested versus verified actual model state.
4. For a new iteration, control atomically persists a V2 creation claim before one native create call. Every later entry is reconciliation-only, including after queue state, error, timeout, crash, or reload.
5. Control continues only when reconciliation finds exactly one real task. It verifies the marker-free bootstrap, then atomically finalizes host, `threadId`, worktree, branch, and baseline as active ownership.
6. Control compiles the approved decisions plus baseline into canonical JSON under private target `PLUGIN_DATA` and sends only a short SHA-256 reference in visible chat.
7. The Hook validates artifact format, size, hash, contract ID, session, active ownership, and live baseline before state creation. The execution task then registers the approved steps in `update_plan` before writing code.
8. The task implements the contract, records only relevant evidence, and survives compaction or resume without source-level truncation of contract boundaries, plan, or acceptance.
9. The task returns a concise execution receipt. Ownership stays active through completion, acceptance failure, and escalation; control closes every lane only after the feature chain is explicitly merged or cancelled.

## 4. Four-layer architecture

### 4.1 Trigger layer

`AGENTS.md` should contain only one trigger rule:

```text
- When no matching active feature-chain ownership and control identity exists, establish that feature chain only when both are true: the current task is explicitly designated as control for the same still-pending implementation, including by a prior explicit $execution-guard invocation in its unresolved clarification chain, or the current prompt explicitly names $execution-guard; and the user approved starting or continuing a sufficiently frozen implementation in a real Git repository.
- Explicitly naming $execution-guard still requires loading the Skill and responding in the current task. Without implementation approval or frozen boundaries, stay there without a claim, execution task, branch, or worktree. The invocation remains control-intent evidence across later clarification turns for that same still-pending implementation. Once ownership is finalized as active and implementation starts, the pending designation ends by transferring its routing identity to that exact active ownership and control chain; cancellation or replacement by an independent goal ends it without handoff.
- A user-approved continuation, optimization, failed-acceptance repair, test, or documentation update whose active implementation ownership and native task identity match exactly reuses the original implementation lane. An isolated recheck whose existing sole approved acceptance ownership and native task identity match exactly reuses that acceptance lane. Neither requires another Guard invocation or control designation, creates a second implementation lane, or absorbs an independent goal.
- When that exact active implementation chain has a concrete approved isolation need and no acceptance lane exists, its inherited routing identity may deterministically claim the sole <feature-chain-key>-acceptance lane without another Guard invocation or control designation. The first claim permits at most one create; later claims reconcile or reuse, and acceptance-v2, acceptance-v3, or timestamped retry lanes are forbidden.
- Research, analysis, review, and one-off Paper, Figma, or HTML exploration stay in the current task even when they generate code or use $frontend-design; an approved production page in a real Git repository may establish a feature chain when both keys are present.
- After new-chain qualification or an exact active-chain match, task creation or reuse, model and reasoning selection, worktree and branch management, plan persistence, execution recovery, and final handoff follow that Skill. Active chain identity ends only when the feature chain is explicitly merged or cancelled. A valid marked execution contract or persisted execution resume follows the existing execution path without restating the entry gate.
```

The trigger does not embed tool order, model policy, registry schema, or lifecycle rules.

### 4.2 Control layer

The public Skill's control path owns create-versus-reuse, live host capability evidence, model routing, the locked pre-create claim, one Codex-native create call, queued/error reconciliation without retry, title and worktree acquisition, detached-HEAD repair, baseline validation, atomic ownership finalization, private contract staging, and short-reference activation. Any missing or ambiguous identity stops before implementation.

The same feature chain reuses one implementation lane for implementation, optimization, tests, documentation, and failed-acceptance fixes. Acceptance detail and rechecks use that lane or an existing acceptance lane. Only a concrete approved isolation need lets the exact active implementation chain claim one deterministic acceptance lane without another Guard invocation; its first claim may create once, and all later claims reconcile or reuse. Independent user value or a known feature chain that restarts after explicit merge or cancellation creates new ownership; ambiguous evidence stops in control.

### 4.3 Execution layer

The execution path preserves the versioned marker and contract. It owns exact `update_plan` registration, implementation, local validation, escalation, local commits, and the evidence-based receipt. It cannot create, fork, delegate, or hand off another task.

### 4.4 Hook layer

Hooks remain inert in ordinary sessions and activate only from the exact marker. They protect the approved execution baseline and lifecycle; they are not a project manager and do not select or create tasks.

## 5. Preserved execution capabilities

### 5.1 Plan compiler

Produce one canonical private execution contract containing:

- contract version and stable contract ID;
- goal and user-visible outcome;
- scope and allowed repositories or paths;
- confirmed decisions;
- non-goals and forbidden operations;
- ordered plan steps with stable IDs;
- allowed local adjustments;
- escalation conditions;
- development and final validation budgets;
- acceptance criteria;
- baseline Git state when available.

Do not send visible chat the full contract or planning transcript on the same host. Stage the contract against active ownership and send natural language plus its short digest reference. Preserve labeled folded-inline V1 only for a cross-host target whose `PLUGIN_DATA` control cannot write.

### 5.2 Model router

Choose from a user-authorized model and reasoning pool. Explain the chosen route in one line and proceed without repeated confirmation while inside policy.

Default policy:

| Task shape | Execution profile |
| --- | --- |
| Clear, mechanical, narrow | Luna Max |
| Normal feature or bounded fix | Terra Max |
| Cross-module but already decided | Sol High |
| Material ambiguity or unresolved product decision | Keep planning in the control task with Sol Ultra |
| High-risk final review | Sol XHigh or Ultra for one bounded review |

Model availability varies by host. Use current native tool schema or explicit host capability evidence first. Fall back only within the user's allowed pool, label that source as non-live, and never present requested availability as verified runtime identity.

### 5.3 Execution ownership

- A project control task owns planning, decisions, model routing, and final acceptance.
- One implementation task owns the feature chain's code changes, local verification, and execution receipts.
- The feature chain reuses one visible implementation task, one worktree, and one feature branch.
- A concrete isolation requirement may add one deterministic acceptance task, worktree, and branch; every later recheck reuses that lane, while code fixes return to implementation.
- The execution task must never create, fork, or hand off another task for the same iteration.
- Completion receipts, acceptance failures, escalations, and phase closeout keep ownership active. Only explicit `merged` or `cancelled` outcomes close it.
- Remote push, PR, CI, tag, and release are outside the guarded local execution path.

### 5.4 Plan registration and anti-expansion

- Register the approved plan in the execution task's `update_plan` before any code write.
- Keep at most one step `in_progress`.
- Preserve stable plan step IDs and reject unapproved step additions.
- Permit implementation-detail adjustments only when they do not change the goal, scope, acceptance criteria, or authorization.
- Return material changes to the control task.

### 5.5 Forward-progress governor

A discovered risk may become current work only when it is directly tied to:

- the current deliverable;
- an observed failure;
- an approved acceptance criterion; or
- a direct blocker to the next implementation step.

Future hardening, theoretical risks, optional capabilities, and unrelated cleanup go to a backlog and do not become implementation steps.

Do not add hashes, fingerprints, integrity layers, new gate frameworks, or validation of existing gates without a named failure, threat boundary, or acceptance requirement. The private contract digest is allowed because this iteration names reproduced visible-handoff and binding failures; it does not authorize wider integrity work.

### 5.6 Validation budget

- During implementation, run only the smallest affected checks.
- Run broader checks only at phase integration, final delivery, or after a public-contract or high-risk change.
- Do not repeat an unchanged check when code, environment, and acceptance target have not changed.
- Stop expanding validation when it no longer produces new evidence.
- Passing the approved acceptance criteria ends the task; the executor cannot invent a new exit gate.

### 5.7 Lifecycle recovery

Use opt-in lifecycle hooks for guarded execution sessions:

- `UserPromptSubmit`: resolve inline V1 or a private reference, validate all artifact bindings, and only then create structured execution state.
- `PreToolUse`: protect writes until environment and plan registration are ready; inspect covered local tool calls.
- `PostToolUse`: record plan transitions and relevant validation evidence.
- `PreCompact`: persist the latest structured checkpoint.
- `SessionStart` on resume or compact: restore every contract boundary plus the exact current plan and acceptance arrays, Git identity, and recorded evidence without source-level character truncation.
- `Stop`: continue only when an approved step or acceptance item remains incomplete; otherwise allow a receipt.

Hooks must remain inert in ordinary chats and sessions without an active contract marker.

A completed or escalated contract is terminal and write-locked. Plain-language follow-ups cannot reopen writes. Control may continue the same task only with the same `contract_id`, worktree, and branch through a private reference that revalidates active ownership and the refreshed Git baseline. The prior terminal state is content-addressed before the revised state is installed atomically; failed installation preserves the locked prior state and one reusable archive.

### 5.8 Execution receipt

Return:

- completed contract and plan step IDs;
- changed paths and local commit IDs;
- validation commands and outcomes;
- deviations and why they were allowed;
- unresolved blockers or explicitly unverified items;
- confirmation that no unauthorized remote or release action occurred.

## 6. Package shape

Repository marketplace layout:

```text
codex-execution-guard/
├── .agents/plugins/marketplace.json
├── plugins/codex-execution-guard/
│   ├── .codex-plugin/plugin.json
│   ├── skills/execution-guard/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   └── references/
│   ├── hooks/hooks.json
│   └── scripts/
│       ├── control_plane.py
│       ├── contract_protocol.py
│       └── execution_guard.py
├── tests/
├── docs/
├── README.md
└── LICENSE
```

Keep `SKILL.md` concise. Put detailed control, contract, routing, lifecycle, and example rules in one-level references. Use deterministic scripts only for the local ownership registry and execution lifecycle state.

The V2 control registry remains at the established private path `PLUGIN_DATA/control/iterations.json`. `claimed` contains no native task or Git identity; `active` adds verified host, real thread, title, worktree, branch, and full baseline; `closed` preserves ownership. A stable sidecar process lock serializes every reload, validation, mutation, and atomic replacement. V1 migrates in place on the next locked write. No MCP, server, database, network runtime, telemetry, automatic claim expiry, or claim clearing is involved.

The shared standard-library contract protocol writes canonical envelopes under `PLUGIN_DATA/contracts/`, capped at 1 MiB and named by SHA-256. It binds contract ID and target session to the exact active ownership snapshot. The digest is a narrow response to reproduced handoff exposure and binding failures, not a general integrity framework.

## 7. Non-goals

The current release does not include:

- an MCP server;
- a hosted service or account system;
- a custom dashboard;
- telemetry or remote storage;
- autonomous push, PR, CI, tag, release, or deployment;
- generic project management;
- guaranteed enforcement across tool paths that Codex Hooks do not cover;
- automatic repair of a bad or incomplete approved plan;
- multi-agent parallel implementation.

## 8. Adversarial review and resolved risks

### Queued task is mistaken for a ready execution owner

Resolution: `clientThreadId` is only setup state. Control waits for a real `threadId`, clear title, linked worktree, branch, full `HEAD`, and Git status before recording ownership or activating execution.

### A failed create response is retried after the host already created a task

Resolution: persist `claimed` before the native call. Only the first locked claim returns `create_once`; later claims are permanently `reconcile_only`. Errors, timeouts, crashes, reloads, and `clientThreadId` never clear the claim. Reconciliation continues only for exactly one candidate and never archives ambiguous candidates automatically.

### One feature produces endless acceptance worktrees

Resolution: freeze one feature-chain key, derive one deterministic implementation iteration ID, and derive a single acceptance ID only when isolation is required. Acceptance detail, retry, optimization, and failed-acceptance fixes resolve the same lanes. Retry-specific `acceptance-v2`, `acceptance-v3`, and timestamped IDs are forbidden by orchestration policy.

### Completion either reopens writes or closes ownership too early

Resolution: keep ownership active after receipts, acceptance failures, escalations, and phase closeout. Completed and escalated contracts remain write-locked. A terminal revision must use the same contract ID and a private reference that revalidates active ownership; only an explicit merged or cancelled feature chain closes its lanes.

### The complete JSON contract overwhelms visible chat

Resolution: same-host control stores one canonical private artifact bound to active ownership and target session. Visible chat contains only natural language, the marker, and a short SHA-256 reference. The Hook validates format, size, hash, ID, session, ownership, contract baseline, and live Git before creating state. Inline V1 remains only as the labeled cross-host fallback.

### Registry silently splits iteration ownership

Resolution: validate every record, hold a stable sidecar process lock across the complete read-modify-write transaction, replace JSON atomically, compare expected baselines, and reject duplicate thread, worktree, and same-project branch ownership. A waiting writer reloads after acquiring the lock, so concurrent writes do not lose committed records. Corrupt state stops control without overwrite.

### Static model policy is presented as live discovery

Resolution: separate host-advertised schema evidence from the local authorized-pool fallback, and report requested versus host-verified actual model state explicitly.

### Global hook accidentally affects normal tasks

Resolution: require an explicit versioned contract marker and session-scoped state. Without it, hooks exit successfully without steering or blocking.

### Executor expands the plan through `update_plan`

Resolution: use stable step IDs and compare updates to the stored approved set. New IDs require a material plan-change path back to the control task.

### Compaction restores stale or excessive context

Resolution: restore every approved contract boundary plus the exact current plan and acceptance arrays, Git identity, deviations, escalation, and evidence. Do not silently truncate fields in plugin source, and never replay or store the full planning transcript.

### Corrupted local state bricks Codex

Resolution: remain fail-open for ordinary sessions. In an active guarded session, block only covered write actions and return a concrete local recovery message. Use atomic local state writes without hashes or fingerprint layers.

### Model router silently spends more than expected

Resolution: route only inside a user-approved model/reasoning pool, show the choice and reason, and require new authority for any profile outside the pool.

### High-reasoning review reopens finished work

Resolution: reviewers may judge only the frozen acceptance contract. Optional hardening and theoretical risks are backlog items. One review pass per unchanged code state.

### Hook coverage creates false confidence

Resolution: document Hooks as guardrails rather than a security boundary, test supported tool paths, and never claim zero-drift guarantees.

### The plugin recreates the overengineering it opposes

Resolution: one focused control helper, one small shared contract protocol, and the preserved execution state engine. There is no MCP, service, database, telemetry, broad integrity framework, or speculative abstraction. SHA-256 is limited to the reproduced private-artifact boundary.

## 9. Acceptance scenarios

1. Same-feature implementation, optimization, acceptance detail, recheck, failed-acceptance fix, test, and documentation reuse deterministic lanes; only independent user value or a known chain restarted after merge or cancellation creates ownership; ambiguity stops.
2. Sequential and concurrent claims grant exactly one `create_once`; every later claim returns `reconcile_only`.
3. An error, timeout, crash, reload, or queued `clientThreadId` cannot clear a claim or authorize another native create call.
4. Finalize accepts exactly one real verified task, is atomic and idempotent, and stops on zero, multiple, dirty, detached, incomplete, or conflicting candidates without retry or automatic archive.
5. The next locked write migrates V1 to V2 without losing existing active or closed records.
6. The default fixture handoff includes a readable single-line goal, remains below 600 UTF-8 bytes through character-safe truncation, and exposes no full JSON, arrays, or absolute worktree path.
7. Missing, oversized, malformed, tampered, wrong-ID, wrong-session, inactive-ownership, and wrong-baseline artifacts fail before partial session state; reference plus inline JSON is rejected.
8. Inline V1 remains compatible, and an ordinary unmarked chat remains fail-open.
9. Activation and simulated compact/resume preserve every contract boundary plus the exact plan and acceptance arrays without source-level truncation.
10. Host-advertised and authorized model evidence is intersected, local fallback is labeled non-live, and actual model state is not fabricated.
11. A guarded execution task cannot write before environment verification and exact plan registration.
12. An unapproved plan step addition is rejected with a return-to-control-task message.
13. Required validation evidence is recorded once; unchanged duplicate validation does not become progress.
14. `Stop` continues an incomplete contract and allows completion after all approved acceptance items are satisfied.
15. The plugin and Skill validators plus control and lifecycle fixtures pass.
16. Fresh-host task creation, actual runtime model identity, marketplace reload, Skill discovery, Hook trust, and host-side context delivery remain explicit manual checks rather than fixture claims.
17. No MCP configuration, server, database, network dependency, telemetry, remote Git action, personal path, live registry, contract artifact, or transcript is included in the distributable source commit.
18. Completed and escalated contracts deny plan changes and writes until a same-contract private reference revalidates active ownership, session, worktree, branch, and baseline; inline V1 remains first-activation only.
19. If terminal revision installation fails after archival, the prior state remains authoritative and locked. Resume, compact, and read-only validation do not mutate it, so retrying the same reference retains exactly one archive.

## 10. Implemented release scope

The 0.3.x release line implements the following scope:

1. Preserve the public `$execution-guard` entry and keep product decisions in control while execution follows one bounded contract at a time.
2. Use a V2 `claimed → active → closed` registry with one-shot creation authorization, reconcile-only recovery, atomic finalize, locked V1 migration, and explicit merged/cancelled closure.
3. Keep the complete same-host contract in a canonical private artifact and send visible natural language plus a short reference, with strict session, ownership, artifact, and Git-baseline checks.
4. Accept strict native delegation envelopes and preserve a labeled inline fallback for first activation across hosts.
5. Freeze one deterministic implementation lane per feature chain and at most one acceptance lane when isolation is required; reuse both across later optimization, fixes, and rechecks.
6. Keep completed and escalated contracts write-locked, support verified same-contract private-reference continuation, and preserve one idempotent terminal archive across recovery events.
7. Restore the complete contract, plan, acceptance, deviations, escalation, and evidence after compaction without plugin-side character truncation.
8. Validate control, lifecycle, Skill, and plugin contracts while keeping marketplace reload, Hook trust, host delivery, and actual runtime-model identity as explicit host checks.
9. Require explicit control intent plus an approved real-repository implementation to establish a new feature chain; reuse exact active implementation ownership for same-chain follow-ups and permit only one deterministic acceptance lane when isolation is approved.
