# Execution contract

## Marker and shape

Use this marker on its own line:

```text
CODEX_EXECUTION_GUARD_CONTRACT_V1
```

The line must contain exactly that marker. Mentioning the marker inline does not activate the guard.

The default same-host handoff keeps the complete contract out of visible chat. Control stores one canonical artifact under target `PLUGIN_DATA/contracts/` and sends a bounded single-line summary of `goal`, followed by the marker and reference:

```text
Execution Guard is ready for contract feature-slug-v1.
Task goal: <single-line goal summary>
CODEX_EXECUTION_GUARD_CONTRACT_V1
Execution contract reference: sha256:<64 lowercase hexadecimal characters>
```

The entire visible prompt is capped at 599 UTF-8 bytes. Long goals are truncated on a character boundary with an ellipsis; newlines are folded, JSON and host-markup brackets are neutralized, and the exact owned worktree path is replaced before rendering.

Codex native task messaging may wrap that prompt in one `<codex_delegation>` envelope whose single `<input>` body contains the handoff. The Hook validates that exact host envelope, extracts only its input body, and then applies the same standalone marker and strict reference rules. Malformed, nested, repeated-input, or unexpected-metadata envelopes fail closed.

The Hook accepts the reference only when its format, size, SHA-256, contract ID, target session, active V2 ownership, and Git baseline all match before session state is created. A prompt containing both a reference and inline JSON is ambiguous and fails closed.

Inline V1 JSON remains compatible for first activation. Use it by default only for the labeled folded-inline cross-host fallback when control cannot write target `PLUGIN_DATA`; do not silently fall back after a missing, malformed, oversized, or tampered same-host artifact. Inline V1 cannot replace completed or escalated session state: terminal revision requires a private reference so active V2 ownership is revalidated.

## Two-stage handoff

When the control task does not yet know the real execution task, worktree, branch, or HEAD, follow [control-orchestration.md](control-orchestration.md) and:

1. Resolve create versus reuse, select the execution model from host-advertised and authorized evidence, and atomically claim a new iteration before any native create call.
2. Send a bootstrap prompt that starts with `CODEX_EXECUTION_GUARD_BOOTSTRAP_V1` but does not contain the contract marker. The bootstrap marker enables `create_thread` payload preflight without activating execution state. Authorize only establishing or checking the unique feature branch and reporting `cwd`, worktree identity, branch, `HEAD`, and status. Explicitly forbid implementation, plan changes, delegation, and additional tasks or worktrees.
3. Reconcile native state without retrying create. Continue only after exactly one real `threadId` and one verified environment report can atomically finalize the claim to active ownership.
4. Compile `baseline`. On the same host, stage the complete canonical contract privately and send the marker plus short reference. Use the labeled folded-inline fallback only when target `PLUGIN_DATA` is unavailable across hosts.

If the current task is already the intended worktree with confirmed active ownership, branch, and `HEAD`, skip bootstrap and stage the complete contract directly. This includes implementation, optimization, failed-acceptance repair, and revalidation for the same feature chain; ordinary follow-up does not create a new task. Never send a contract with a `clientThreadId` or guessed baseline values.

The object must contain:

```json
{
  "contract_version": 1,
  "contract_id": "feature-slug-v1",
  "role": "execution",
  "goal": "User-visible outcome",
  "scope": ["Allowed repository-relative paths or components"],
  "decisions": ["Confirmed decision"],
  "non_goals": ["Excluded capability"],
  "forbidden_operations": ["push", "pull-request", "tag", "release", "deploy"],
  "authorized_models": ["gpt-5.6-sol/high"],
  "selected_model": "gpt-5.6-sol/high",
  "route_reason": "Cross-module implementation with frozen decisions",
  "baseline": {
    "worktree": "/absolute/expected/worktree",
    "branch": "codex/feature-slug",
    "head": "expected Git commit",
    "require_clean": true
  },
  "plan": [
    {"id": "P1", "step": "P1 Scaffold: create the approved structure", "status": "in_progress"},
    {"id": "P2", "step": "P2 Implement: complete the frozen behavior", "status": "pending"}
  ],
  "allowed_adjustments": ["Implementation notes that do not change scope or acceptance"],
  "escalation_conditions": ["A new stable plan ID is required"],
  "validation_budget": {
    "development": ["Smallest affected check"],
    "final": ["Frozen final validator"]
  },
  "acceptance": [
    {"id": "A1", "criterion": "Approved observable outcome", "status": "pending"}
  ]
}
```

Use absolute paths only in a live contract. Do not commit personal paths, credentials, transcripts, or private project names in plugin files or examples.

Referenced contract IDs use 1–128 ASCII letters, digits, dots, underscores, or hyphens. A canonical artifact may be at most 1 MiB. Its envelope binds the contract to the target session and the exact active ownership snapshot; changing either requires a newly staged artifact and reference.

## Compiler rules

- Compile confirmed decisions, not the full planning transcript.
- Preserve the user's wording where it defines scope or acceptance.
- Give each plan and acceptance item a stable, unique ID.
- Set exactly zero or one initial plan item to `in_progress`.
- Include a concrete Git baseline for an execution-role contract.
- Include only models and reasoning levels the user authorized.
- Treat missing material decisions as a reason to keep planning in the control task, not as executor discretion.
- Bind each lane's `contract_id` to the exact deterministic iteration ID frozen for the feature chain. Revisions and rechecks keep that ID; do not mint retry- or version-suffixed contract IDs.

## Change boundary

The executor may change plan status and add a concise implementation note. It must not change step text, reorder or omit steps, add IDs, widen paths, weaken acceptance, or authorize a new model or external action. A material change returns to the control task.

Control may send revised contract content to the same task after the prior contract is complete or escalated. Until then, marker-free prompts leave terminal state locked and neither `update_plan` nor write tools may run. The revision must arrive through a private short reference, keep the same `contract_id`, worktree, and branch, and carry a baseline verified against active V2 ownership and current clean Git state. The Hook archives the prior terminal session state under private `PLUGIN_DATA` by content hash before atomically initializing the revised plan. If session-state replacement fails, it blocks the prompt, preserves the old terminal state, and reuses the same archive on retry. It rejects inline rollover, closed or changed ownership, a non-terminal prior state, or differing identity and baseline.
