# Codex Execution Guard — Control and Execution Design

## 1. Outcome

Turn implementation authorization in a project control task into one durable iteration owner and one bounded execution contract that the correct Codex task can implement in one worktree, with explicit progress, recovery after compaction, and evidence-based completion.

The product is not a replacement for native Plan mode or native task tools. It governs task ownership and the transition from planning to execution.

## 2. First-principles model

Reliable agent delivery requires four durable elements:

1. Approved intent: goal, scope, decisions, non-goals, authorization, and acceptance criteria.
2. Isolated state: one execution task, one worktree, and one feature branch per iteration.
3. Recoverable progress: stable plan step identifiers, current status, deviations, and validation evidence.
4. A bounded exit rule: completion is judged against the approved contract, not newly invented gates.

Conversation history is lossy and may be compacted. Git state is durable and consequential. Therefore critical execution state must be concise, structured, and recoverable without replaying the planning transcript.

## 3. Target user and primary scenario

The first target is a Codex desktop user who keeps product decisions in a project control task and delegates implementation to a separate visible task with an isolated worktree.

Primary flow:

1. The user approves execution in the project control task.
2. Control resolves the real project and decides whether the approved work reuses the active iteration or creates a new one.
3. Control discovers host-advertised model capabilities, intersects them with the authorized pool, and reports requested versus verified actual model state.
4. For a new iteration, Codex creates one visible worktree task, waits for a real `threadId`, sets its title, and obtains its real Git baseline through a marker-free bootstrap.
5. Control persists iteration ownership under a process lock and atomic replacement, then compiles the approved discussion plus baseline into an execution contract.
6. The execution task verifies its environment and registers the approved steps in `update_plan` before writing code.
7. The task implements the contract, records only relevant evidence, and survives compaction or resume.
8. The task returns a concise execution receipt; control later closes the mapping after acceptance or merge.

## 4. Four-layer architecture

### 4.1 Trigger layer

`AGENTS.md` should contain only one trigger rule:

```text
When the user explicitly authorizes implementation of a new feature, an independent code task, or continuation of an existing feature, the project control task must invoke $execution-guard; task creation or reuse, model selection, worktree and branch management, plan persistence, execution recovery, and final handoff follow that Skill.
```

The trigger does not embed tool order, model policy, registry schema, or lifecycle rules.

### 4.2 Control layer

The public Skill's control path owns create-versus-reuse, live host capability evidence, model routing, Codex-native project and task calls, queued-to-real task gating, title and worktree acquisition, detached-HEAD repair, baseline validation, ownership persistence, and contract activation. Any missing identity or product ambiguity stops before implementation.

Same goal, scope, and acceptance reuse the active task, including its fixes, adjustments, tests, and documentation. Closed or merged iterations, independent user value, and new acceptance criteria create a new task.

### 4.3 Execution layer

The execution path preserves the versioned marker and contract. It owns exact `update_plan` registration, implementation, local validation, escalation, local commits, and the evidence-based receipt. It cannot create, fork, delegate, or hand off another task.

### 4.4 Hook layer

Hooks remain inert in ordinary sessions and activate only from the exact marker. They protect the approved execution baseline and lifecycle; they are not a project manager and do not select or create tasks.

## 5. Preserved execution capabilities

### 5.1 Plan compiler

Produce a concise execution contract containing:

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

Do not send the execution task the full planning transcript.

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
- An execution task owns implementation, local verification, and the execution receipt.
- One iteration uses one visible execution task, one worktree, and one feature branch.
- The execution task must never create, fork, or hand off another task for the same iteration.
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

Do not add hashes, fingerprints, integrity layers, new gate frameworks, or validation of existing gates without a named failure, threat boundary, or acceptance requirement.

### 5.6 Validation budget

- During implementation, run only the smallest affected checks.
- Run broader checks only at phase integration, final delivery, or after a public-contract or high-risk change.
- Do not repeat an unchanged check when code, environment, and acceptance target have not changed.
- Stop expanding validation when it no longer produces new evidence.
- Passing the approved acceptance criteria ends the task; the executor cannot invent a new exit gate.

### 5.7 Lifecycle recovery

Use opt-in lifecycle hooks for guarded execution sessions:

- `UserPromptSubmit`: recognize and store the structured execution contract.
- `PreToolUse`: protect writes until environment and plan registration are ready; inspect covered local tool calls.
- `PostToolUse`: record plan transitions and relevant validation evidence.
- `PreCompact`: persist the latest structured checkpoint.
- `SessionStart` on resume or compact: restore the contract, current step, Git identity, and recorded evidence as concise context.
- `Stop`: continue only when an approved step or acceptance item remains incomplete; otherwise allow a receipt.

Hooks must remain inert in ordinary chats and sessions without an active contract marker.

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
│       └── execution_guard.py
├── tests/
├── docs/
├── README.md
└── LICENSE
```

Keep `SKILL.md` concise. Put detailed control, contract, routing, lifecycle, and example rules in one-level references. Use deterministic scripts only for the local ownership registry and execution lifecycle state.

The control registry maps iteration ID to project, real thread, title, worktree, branch, full baseline, and active or closed status. It uses only Python standard library JSON at an explicit private path outside the repository. A stable sidecar process lock serializes every reload, validation, mutation, and atomic replacement, preventing concurrent control tasks from overwriting one another's committed records. No MCP, server, database, network runtime, or telemetry is involved.

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

### Registry silently splits iteration ownership

Resolution: validate every record, hold a stable sidecar process lock across the complete read-modify-write transaction, replace JSON atomically, compare expected baselines, and reject duplicate thread, worktree, and same-project branch ownership. A waiting writer reloads after acquiring the lock, so concurrent writes do not lose committed records. Corrupt state stops control without overwrite.

### Static model policy is presented as live discovery

Resolution: separate host-advertised schema evidence from the local authorized-pool fallback, and report requested versus host-verified actual model state explicitly.

### Global hook accidentally affects normal tasks

Resolution: require an explicit versioned contract marker and session-scoped state. Without it, hooks exit successfully without steering or blocking.

### Executor expands the plan through `update_plan`

Resolution: use stable step IDs and compare updates to the stored approved set. New IDs require a material plan-change path back to the control task.

### Compaction restores stale or excessive context

Resolution: restore only the approved contract, current plan state, Git identity, deviations, and evidence. Never replay or store the full transcript.

### Corrupted local state bricks Codex

Resolution: remain fail-open for ordinary sessions. In an active guarded session, block only covered write actions and return a concrete local recovery message. Use atomic local state writes without hashes or fingerprint layers.

### Model router silently spends more than expected

Resolution: route only inside a user-approved model/reasoning pool, show the choice and reason, and require new authority for any profile outside the pool.

### High-reasoning review reopens finished work

Resolution: reviewers may judge only the frozen acceptance contract. Optional hardening and theoretical risks are backlog items. One review pass per unchanged code state.

### Hook coverage creates false confidence

Resolution: document Hooks as guardrails rather than a security boundary, test supported tool paths, and never claim zero-drift guarantees.

### The plugin recreates the overengineering it opposes

Resolution: one focused control helper plus the preserved execution state engine, no MCP, no checksums, no general policy language, no speculative abstractions, and tests limited to the frozen control and lifecycle contracts.

## 9. Acceptance scenarios

1. Same-goal work and iteration maintenance reuse the active task; closed work, independent value, and new acceptance create a task; ambiguity stops.
2. Duplicate ownership, stale baseline, incomplete record, or corrupt registry fails safely without overwrite; a deterministic two-process case proves the second writer waits, reloads, and preserves both records.
3. A queued `clientThreadId`, detached final report, dirty baseline, or incomplete identity cannot activate execution.
4. Host-advertised and authorized model evidence is intersected, local fallback is labeled non-live, and actual model state is not fabricated.
5. A normal chat without a contract is unaffected.
6. A guarded execution task cannot write before environment verification and plan registration.
7. The original plan registers unchanged with stable IDs and at most one `in_progress` step.
8. An unapproved plan step addition is rejected with a return-to-control-task message.
9. A guarded task resumes after simulated compaction with the correct contract and current step.
10. Required validation evidence is recorded once; unchanged duplicate validation does not become progress.
11. `Stop` continues an incomplete contract and allows completion after all approved acceptance items are satisfied.
12. The plugin and Skill validators plus control and lifecycle fixtures pass.
13. Fresh-host task creation, actual runtime model identity, marketplace reload, Skill discovery, and Hook trust remain explicit manual host checks rather than fixture claims.
14. No MCP configuration, server, database, network dependency, telemetry, remote Git action, or personal path is included in the distributable plugin.

## 10. Implemented release scope

The 0.2.0 release implements the following scope:

1. Preserve the public `$execution-guard` entry and route control versus execution through direct references.
2. Define deterministic ownership, native bootstrap, model evidence, and failure-stop semantics.
3. Add the process-locked, atomically replaced local iteration registry without changing Hook authority.
4. Add focused control and adversarial registry fixtures while preserving the earlier lifecycle behavior.
5. Synchronize product, usage, Skill UI, and plugin interface metadata.
6. Validate the control, lifecycle, Skill, and plugin contracts.
7. Keep fresh-host installation, marketplace reload, Skill discovery, Hook trust, and actual runtime-model identity as explicit host checks.
