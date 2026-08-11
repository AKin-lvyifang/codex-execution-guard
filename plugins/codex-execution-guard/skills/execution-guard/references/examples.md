# Examples

## Legal status update

Keep every approved step and stable ID:

```json
{
  "explanation": "Implemented the approved parser without changing scope.",
  "plan": [
    {"step": "P1 Scaffold: create the approved structure", "status": "completed"},
    {"step": "P2 Implement: complete the frozen behavior", "status": "in_progress"}
  ]
}
```

## Rejected expansion

Do not add `P3 Harden every future input` because a reviewer raised a theoretical concern. Record it as backlog and continue against the frozen acceptance criteria. If `P3` is necessary for the current deliverable, stop and return the proposed contract change to the control task.

## Transparent fallback

```text
Route: Terra Max (fallback from unavailable Sol High; both are in the authorized pool).
```

If Terra Max is not authorized, do not use it.

For a non-live route, state the evidence boundary:

```text
Route: requested Terra Max from local authorized-pool fallback; not live host discovery; actual model unverified.
```

## Create-or-reuse decisions

Freeze lane identity before the first claim:

```text
Feature-chain key: feature-slug-v1
Implementation iteration: feature-slug-v1-implementation
Acceptance iteration, only if isolation is required: feature-slug-v1-acceptance
```

```text
Reuse implementation: this acceptance detail, retry, optimization, failed-acceptance fix, test, or documentation belongs to the same feature chain; active ownership matches the native task.
```

```text
Reuse acceptance: independent acceptance still needs its existing isolated lane; send code fixes back to implementation and return here only for recheck.
```

Claim `feature-slug-v1-acceptance` again for every recheck. The existing ownership yields reuse or `reconcile_only`; never create `feature-slug-v1-acceptance-v2`, `-v3`, or a timestamped retry. This is control policy, not a registry schema constraint.

```text
Create: the proposed work is explicit independent user value, or the prior feature chain was merged or cancelled.
```

```text
Stop: lane ownership or independence is ambiguous; keep the decision in control and do not create a task.
```

## One-shot creation claim

The first locked claim is the only create permission:

```text
Claim: create_once. Call native create_thread once.
```

Every later claim reconciles, even if the first call reported an error or returned only queue state:

```text
Claim: reconcile_only. Do not call create_thread again; inspect native tasks. Zero or multiple candidates stop without retry or archive.
```

## Marker-free bootstrap result

Do not activate from queued setup:

```text
Queued only: clientThreadId=<id>. No real threadId or Git baseline is available; execution remains inactive.
```

After native readiness and environment inspection, return the real identity and porcelain status. Finalize the existing claim to active only after this report validates and reconciliation found exactly one candidate.

## Default same-host handoff

Keep the canonical contract in target `PLUGIN_DATA` and send only:

```text
Execution Guard is ready for contract feature-slug-v1.
Task goal: Keep the approved handoff readable and create at most one native task.
CODEX_EXECUTION_GUARD_CONTRACT_V1
Execution contract reference: sha256:<64 lowercase hexadecimal characters>
```

Do not paste the artifact path or full JSON into visible chat. If target `PLUGIN_DATA` cannot be staged because control and execution are on different hosts, use the explicit `fold-inline` output. Never use inline fallback to bypass a same-host validation error.

## Terminal contract revision

After completion or escalation, marker-free follow-up leaves the terminal session write-locked. Reuse the same task and active ownership only through the private short reference:

```text
Revise: verify the current clean baseline, keep the same contract_id/worktree/branch, stage the revised contract, and send its short reference. The Hook privately archives the prior terminal state.
```

Inline V1 remains valid for first activation only. Do not use it to revise terminal state, closed ownership, a non-terminal session, or a different `contract_id`. If the archive succeeds but the new session-state write fails, retry the same reference: the old terminal state remains locked and the content-addressed archive is reused.

## Ownership close

Completion receipts, acceptance failures, escalations, and phase closeout keep ownership active. Close only the whole feature-chain outcome:

```text
control_plane.py ... close --iteration feature-v1 --expected-baseline <full-head> --outcome merged
control_plane.py ... close --iteration feature-v1 --expected-baseline <full-head> --outcome cancelled
```

## Host-limited acceptance

```text
Unverified: real fresh-session plugin Hook loading and trust review require a host restart and user trust action; fixture lifecycle tests passed, but they do not prove host pickup.
```
