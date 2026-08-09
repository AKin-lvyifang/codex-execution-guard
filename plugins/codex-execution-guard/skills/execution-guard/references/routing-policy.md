# Model routing policy

Discover the current host's advertised model and reasoning combinations first. Intersect them with `authorized_models`, then route only inside that intersection. Show the requested profile, evidence source, reason, and actual-model verification state before execution.

| Frozen task shape | Preferred profile |
| --- | --- |
| Clear, mechanical, narrow | Luna Max |
| Normal feature or bounded fix | Terra Max |
| Cross-module with decisions already frozen | Sol High |
| Material ambiguity or unresolved product choice | Keep planning in the control task with Sol Ultra |
| One bounded high-risk final review | Sol XHigh or Ultra |

Treat the callable native task tool's current schema or an explicit host capability result as host-advertised evidence. A static table, prior run, local config, or this reference is not live discovery.

If live discovery is unavailable, route from the local authorized pool only when the user allows that fallback. Label it `local authorized-pool fallback; not live host discovery`. The host still validates the request when task creation runs.

Requested availability is not proof of the model that actually ran. Report one of:

- `actual model verified: <host-reported model/reasoning>` when the host returns runtime identity;
- `actual model unverified` when it does not.

If the preferred profile is unavailable, choose the nearest task-appropriate profile only when it remains inside both the host-advertised set and `authorized_models`, and report the fallback. Otherwise stop and request authority. Do not silently increase reasoning or add a review pass. Material ambiguity stays in the Sol Ultra control task; it is not delegated as implementation. Limit high-risk final review to one bounded XHigh or Ultra pass per unchanged code state.
