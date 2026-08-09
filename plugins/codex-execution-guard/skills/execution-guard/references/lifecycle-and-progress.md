# Lifecycle and progress

## Startup and registration

For a guarded execution:

1. Report the selected model route in one line.
2. Run read-only checks for `pwd`, worktree identity, current branch, `HEAD`, and Git status.
3. Compare the results with `baseline`. Stop on a material mismatch.
4. Call `update_plan` with the complete ordered `plan` array. Copy each `step` exactly; change only allowed statuses. Keep at most one `in_progress`.
5. Begin writes only after the plan call succeeds and the Hook reports readiness.

The Hook independently verifies the Git baseline when it accepts the first plan registration. Before readiness it denies covered writes and allows only bounded environment inspection plus `update_plan`.

When the baseline is not yet known, complete the unguarded bootstrap described in the contract reference first. Do not include the marker and do not implement during bootstrap.

## Plan and acceptance updates

Always send the complete approved plan to `update_plan`; never send a partial list. To record proven acceptance, optionally set `explanation` to one JSON control line:

```text
execution_guard: {"acceptance_complete":["A1"],"evidence":"Validator X passed","implementation_note":"No scope change"}
```

Only list acceptance IDs supported by evidence already produced. The Hook rejects unknown IDs and records the note without creating a new step.

To return a material blocker to the control task while approved IDs remain incomplete, register one explicit escalation:

```text
execution_guard: {"escalation":{"reason":"A required scope decision is missing","evidence":"The approved API has no behavior for case X"}}
```

Both fields are required. Escalation is not completion: the receipt retains incomplete plan and acceptance IDs and makes no success claim.

## Evidence budget

- Record a validation command once with its outcome, current Git HEAD, changed paths, current step, and acceptance state.
- If the same command and outcome run again with unchanged Git state, current step, and acceptance target, treat it as duplicate evidence, not progress. A failed result followed by a passed result is new evidence.
- Run broader checks only for phase integration, the frozen final budget, or a changed public or high-risk contract.
- Stop validation when it produces no new evidence.

## Compaction and resume

`PreCompact` persists the already-structured checkpoint. `SessionStart` on `resume` or `compact` restores the contract ID, goal, selected model, scope, decisions, non-goals, forbidden operations, current step, approved IDs and statuses, Git baseline/current identity, deviations, and concise evidence within the configured context boundary. Re-check Git state before resuming writes. Never reconstruct scope from the lossy transcript.

## Stop and receipt

`Stop` uses `decision: "block"` only while approved work remains incomplete without a registered escalation. Once all items are complete, or an evidence-backed escalation is registered, it returns no block decision and allows delivery to the control task.

For completed work, deliver:

```text
Execution receipt
- Contract: <contract ID>
- Completed plan: <stable IDs>
- Completed acceptance: <stable IDs>
- Changed paths: <repository-relative paths>
- Local commits: <commit IDs>
- Validation: <command and outcome, once per state>
- Allowed deviations: <none or concise reasons>
- Unverified or blocked: <none or explicit host limitation>
- Remote/release actions: none
```

Hooks cannot guarantee coverage of every tool path. Report fixture validation separately from a real fresh-session install, Hook trust review, and host discovery check.
