# Lifecycle and progress

## Startup and registration

For a guarded execution:

1. Resolve the private reference, when present, before creating session state. Missing, oversized, malformed, tampered, wrong-session, inactive-ownership, or wrong-baseline artifacts stop without partial activation.
2. Receive the complete contract, exact plan, and exact acceptance in private Hook context; visible chat contains only the short reference during the default same-host path.
3. Report the selected model route in one line.
4. Run read-only checks for `pwd`, worktree identity, current branch, `HEAD`, and Git status.
5. Compare the results with `baseline`. Stop on a material mismatch.
6. Call `update_plan` with the complete ordered `plan` array. Copy each `step` exactly; change only allowed statuses. Keep at most one `in_progress`.
7. Begin writes only after the plan call succeeds and the Hook reports readiness.

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

## Terminal revision

Completion and escalation end one contract, not the feature-chain ownership. They also lock `update_plan` and every write tool; ordinary marker-free prompts do not change that state. Control may send revised contract content back to the same task only through a private short reference with the same active `contract_id`, worktree, and branch and a freshly verified baseline. Inline V1 is first-activation compatibility, not a terminal continuation path.

The Hook content-addresses the prior terminal state under private `PLUGIN_DATA`, then atomically installs the incoming plan and acceptance arrays. If the session-state write fails after archival, `UserPromptSubmit` blocks, the old terminal state remains authoritative and write-locked, and retrying the same reference reuses the one archive. After success, baseline verification and exact plan registration are required again before writes. A non-terminal state, closed ownership, or different identity fails closed without replacing current state.

Keep fixes and optimizations on the deterministic implementation iteration ID frozen for the feature-chain key. If acceptance truly requires an independent environment or responsibility, freeze one deterministic acceptance iteration ID and claim that exact ID on every recheck, producing reuse or `reconcile_only` rather than `acceptance-v2` or `acceptance-v3`. Later acceptance failures send code changes back to implementation. This is an orchestration policy; the registry schema does not encode feature-chain keys or enforce lane counts, and no schema migration is required.

## Evidence budget

- Record a validation command once with its outcome, current Git HEAD, changed paths, current step, and acceptance state.
- If the same command and outcome run again with unchanged Git state, current step, and acceptance target, treat it as duplicate evidence, not progress. A failed result followed by a passed result is new evidence.
- Run broader checks only for phase integration, the frozen final budget, or a changed public or high-risk contract.
- Stop validation when it produces no new evidence.

## Compaction and resume

`PreCompact` persists the already-structured checkpoint. `SessionStart` on `resume` or `compact` restores every contract boundary plus the exact current plan and acceptance arrays without source-level truncation. It also restores Git baseline/current identity, deviations, escalation, and recorded evidence. Re-check Git state before resuming writes. Never reconstruct scope from the lossy transcript.

Fixture output proves that the plugin source does not truncate these fields. A host may still impose an external context limit; report that separately if observed rather than silently claiming full host delivery.

## Stop and receipt

`Stop` uses `decision: "block"` only while approved work remains incomplete without a registered escalation. Once all items are complete, or an evidence-backed escalation is registered, it returns no block decision and allows delivery to the control task. This delivery is not ownership closure.

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

Control keeps registry ownership active after a completion receipt, acceptance failure, escalation, or phase closeout. Only an explicit merged or cancelled outcome closes the feature chain.
