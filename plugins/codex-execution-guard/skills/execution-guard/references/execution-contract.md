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

The entire visible prompt is capped at 599 UTF-8 bytes. Long goals are truncated on a character boundary with an ellipsis; newlines are folded, JSON brackets are neutralized, and the exact owned worktree path is replaced before rendering.

The Hook accepts the reference only when its format, size, SHA-256, contract ID, target session, active V2 ownership, and Git baseline all match before session state is created. A prompt containing both a reference and inline JSON is ambiguous and fails closed.

Inline V1 JSON remains compatible. Use it by default only for the labeled folded-inline cross-host fallback when control cannot write target `PLUGIN_DATA`; do not silently fall back after a missing, malformed, oversized, or tampered same-host artifact.

## Two-stage handoff

When the control task does not yet know the real execution task, worktree, branch, or HEAD, follow [control-orchestration.md](control-orchestration.md) and:

1. Resolve create versus reuse, select the execution model from host-advertised and authorized evidence, and atomically claim a new iteration before any native create call.
2. Send a bootstrap prompt without the contract marker. Authorize only establishing or checking the unique feature branch and reporting `cwd`, worktree identity, branch, `HEAD`, and status. Explicitly forbid implementation, plan changes, delegation, and additional tasks or worktrees.
3. Reconcile native state without retrying create. Continue only after exactly one real `threadId` and one verified environment report can atomically finalize the claim to active ownership.
4. Compile `baseline`. On the same host, stage the complete canonical contract privately and send the marker plus short reference. Use the labeled folded-inline fallback only when target `PLUGIN_DATA` is unavailable across hosts.

If the current task is already the intended worktree with confirmed active ownership, branch, and `HEAD`, skip bootstrap and stage the complete contract directly. Never send a contract with a `clientThreadId` or guessed baseline values.

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

## Change boundary

The executor may change plan status and add a concise implementation note. It must not change step text, reorder or omit steps, add IDs, widen paths, weaken acceptance, or authorize a new model or external action. A material change returns to the control task.
