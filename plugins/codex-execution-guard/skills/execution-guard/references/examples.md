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

```text
Reuse: this is a test and documentation follow-up for the same goal, scope, and acceptance; active iteration ownership matches the native task.
```

```text
Stop: the proposed work may add independent user value and new acceptance; keep the decision in control and do not create a task.
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

## Host-limited acceptance

```text
Unverified: real fresh-session plugin Hook loading and trust review require a host restart and user trust action; fixture lifecycle tests passed, but they do not prove host pickup.
```
