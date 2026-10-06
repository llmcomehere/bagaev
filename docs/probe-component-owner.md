# Generic serial owned-record simulation /1

Experimental contract. Initial literal expectations were frozen before implementation.
This is an in-memory model driven by checked component-source/1, not a trusted
production service, durable store or general concurrency implementation.

## Trusted host setup

An Owner receives independent policy, admitted immutable source components,
initial nominal state, initial nonnegative Int64 revision, resource incarnation,
a data-checker callback, a typed-reference callback and a current-conditions
callback. Each callback is explicit host setup, never packet data. Source membership
is a host premise; this slice does not replace source-change admission.

Every source is completely checked against the same policy using the existing
component reader; canonical source hash indexes an immutable registry (1..16).
State type and identity bindings come from checked output, not field names in the
model. Validate initial state with actual typed identity-program invocation.
Actual evaluation and output validation use the existing typed-record/10 reference.
Hash equality cannot authenticate a dishonest callback. State/inputs/outputs are
deep detached copies. No callbacks or fallible serialization between state/receipt
publication steps. Python assignment sequence is not a process-crash transaction.

Current conditions contain exact tick, epoch (nonnegative Int64) and exact boolean
submit/write/observe/cancel fields. They come from the host every boundary. Time
must be monotone per owner. Conditions do not come from request/context. Owner
resource is fixed. Revision cannot exceed Int64 maximum. Capacity64 terminal rows.
No expiration or row deletion in this slice; full capacity refuses before compute.

## Request and immutable intent

Packet has exactly key, source, request, epoch, deadline. key has exact resource,
domain,id fields (nonempty bounded ASCII identifiers, resource permits slash).
source is a lowercase64hex admitted component identity. request is a complete
nominal value interpreted only using the selected source request type. epoch and
deadline are nonnegative Int64. Packet size <=1MiB, depth<=128, values<=10000;
no floats, duplicate object keys, nonfinite numbers or non-string object keys.

The key is separate from application state identity. Intent is complete source,
request,epoch,deadline. Expected revision comes solely from the source-declared
request revision record field. State/request application identity comes solely
from their checked fields. Do not canonicalize unordered user data into a different
intent after it crosses the boundary.

## Submit order and observable outcomes

1. Bounded packet shape, resource and admitted source membership. Malformed input
   raises OwnerInputError with a stable code; no business receipt or computation.
2. Read current conditions. Missing submit permission => AccessDenied, no binding.
3. If key exists: current observe permission first, then exact intent comparison.
   Denied => AccessDenied; different => IntentConflict; otherwise detached old
   receipt. No current write permission/base/epoch/deadline check or evaluation.
4. New key: require write permission. Validate nominal request with actual typed
   identity invocation and identity binding. Invalid request => OwnerInputError,
   no terminal record. Actual reference refusal is distinct from service failure.
5. Capacity => CapacityExceeded without binding. Then deadline, epoch, revision,
   Int64 revision exhaustion checked in that order. These well-formed accepted
   business refusals bind Refused{reason,revision}, then current observe permission
   determines whether receipt or OutcomeUnknown is returned.
6. Snapshot state/revision and evaluate selected source with [state,request].
   Validate returned full nominal state by actual reference. Compare every checked
   preserved field. Refusal/type/frame failure => explicit exception, no mutation
   or business receipt; never successful zero/empty result.
7. Read current conditions again. Submit/write revocation => AccessDenied without
   binding. Recheck terminal-key race, capacity, deadline,epoch,revision/exhaustion
   and exact snapshot state. A different accepted nested operation is retained;
   this attempt cannot undo it. A now-recorded same-key terminal result resolves
   via step3. Refused stale attempt binds refusal at current revision if capacity
   allows. A state change without revision change is a model integrity error.
8. Publish detached next state, increment revision once, bind immutable Applied
   {key,intent,revision,state}. Return receipt if current observe permission,
   otherwise OutcomeUnknown. Test transport may discard a returned receipt outside
   Owner; lost reply never removes terminal state.

All external callbacks finish before step8. Framework memory failure is outside
this finite model; there is no claim Python operations cannot fail physically.

## Observe / cancel

Observe validates packet frame and membership, reads current observe permission,
then returns Unknown when no row exists, IntentConflict for different intent,
or detached historical receipt. It never computes or writes application state.
Cancel requires current cancel permission and a valid nominal request before
binding a fresh Cancelled{key,intent,revision}. Existing applied result returns
AlreadyApplied only when observation is permitted and intent matches. Other
terminal results replay. No write permission needed to establish cancellation,
but capacity/resource/source/request constraints still apply. A delayed submit
encounters the same bound cancellation. Cancellation never reverses application
state. With observation denied it returns OutcomeUnknown after a fresh binding.

## Scope of continuation and run identity

Use exact source identities in each packet. A new run's host-selected default
cannot rewrite old packet intent. Existing component-context inspection can retain
these packets but does not reconstruct host callbacks, permissions or Owner state.
Keep this test model and its new cases separate from unchanged WC17 legacy traces.


## Reproduction and observed limits

[Stock source](../examples/probes/component-owner/Stock.bagaev) uses the existing
readable form unchanged. It replaces an explicitly requested Int64 quantity and
preserves a differently named key/note, without catalogue-specific conversion or
hidden host arithmetic. The catalogue component uses its existing source.

[Twenty original cases](../examples/probes/component-owner/receiver-cases.json)
and [three additional cases](../examples/probes/component-owner/extra-cases.json)
are pinned by the [input manifest](../examples/probes/component-owner/inputs.json).
The original model matched18/20 because its adapter assumed the wrong reference
refusal status. The actual reference uses invalid-ir/RR_ARGUMENT for bad values.
Correcting the adapter preserved the original expectations. A later frozen case
exposed Python equality treating integer1 and booleantrue as the same intent;
complete canonical intent comparison fixed it without changing the oracle.
These failures are reasons to distinguish host-language equality from language
identity, not a claim of complete verification.

The [portable runner](../tests/probes/component_owner_checks.py) requires absolute
`--reader`, `--reference`, their separately retained `--reader-sha256` and
`--reference-sha256`, and a new absolute `--output` directory whose parent exists.
The existing component reader and typed-record/10 reference are described in the
[component source guide](probe-component-source.md). Review and authorize those
executables first, then use an approved bounded no-network profile. The runner
does not establish isolation or authorize binaries merely because hashes match.

The final qualification matches23 finite scenarios across both domains. Capacity
and detached receipt/state guards are separate. Five own-code mutations produced
normal wrong outcomes and were detected during same-maintainer qualification;
this is not independent reproduction. Actual source/reference calls and retained
failure details are conformance observations, not speed/cost measurements.

There is no migration, multi-record transaction, production authorization, storage,
real concurrency, receiver discovery or retention deletion. The old17-case
catalogue simulation and L2/Store/P0 contracts are unchanged. Each new case is a
separate serial model instance; passing does not establish arbitrary application
contracts or the complete proposed language.
