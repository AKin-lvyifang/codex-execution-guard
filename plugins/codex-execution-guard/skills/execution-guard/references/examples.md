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

## Marker-free bootstrap result

Do not activate from queued setup:

```text
Queued only: clientThreadId=<id>. No real threadId or Git baseline is available; execution remains inactive.
```

After native readiness and environment inspection, return the real identity and porcelain status. Create the active registry record and compile the contract only after this report validates.

## Host-limited acceptance

```text
Unverified: real fresh-session plugin Hook loading and trust review require a host restart and user trust action; fixture lifecycle tests passed, but they do not prove host pickup.
```
