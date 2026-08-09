# Execution contract

## Marker and shape

Use this marker on its own line, followed by one JSON object:

```text
CODEX_EXECUTION_GUARD_CONTRACT_V1
```

The line must contain exactly that marker. Mentioning the marker inline does not activate the guard.

## Two-stage handoff

When the control task does not yet know the real execution task, worktree, branch, or HEAD, follow [control-orchestration.md](control-orchestration.md) and:

1. Resolve create versus reuse, select the execution model from host-advertised and authorized evidence, and create at most the one allowed execution task.
2. Send a bootstrap prompt without the contract marker. Authorize only establishing or checking the unique feature branch and reporting `cwd`, worktree identity, branch, `HEAD`, and status. Explicitly forbid implementation, plan changes, delegation, and additional tasks or worktrees.
3. Wait for a real `threadId`; receive the real environment report in the control task, validate it, persist ownership, and compile it into `baseline`.
4. Send the exact marker line plus the complete contract to activate guarded execution.

If the current task is already the intended worktree with a confirmed real task identity, branch, and HEAD, skip bootstrap and activate the complete contract directly. Never send a contract with a `clientThreadId` or guessed baseline values.

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
