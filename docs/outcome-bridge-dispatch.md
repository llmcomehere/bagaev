# Final storage boundary for direct outcome calls

The direct [outcome bridge](../src/bagaev_outcome_storage.py) connects a typed
owner to one SQLite image. It is used by [stock adjustment](stock-adjustment.md)
and the tag-box examples, independently of managed programme admission.

Every successful return crosses the final complete-image G/digest comparison,
including retained submit, observe and cancel answers. A nested host callback
may commit after the outer image was read. The outer call then refuses with
STORAGE_CONFLICT, preserves that nested commit and performs no implicit retry.
Two nested commits that restore identical bytes still conflict through G.

Without an intervening change, a call with no receiver change retains the
original payload, digest and G. A clock-floor-only observation is not persisted.
An actual receiver change retains its single atomic image commit. This does not
alter the owner's current permission checks, terminal receipt semantics or
clock-domain rules. It adds no permission or historical authentication.

## Frozen regression and observations

The [six dispatcher test methods](../tests/probes/test_outcome_bridge_final_cas.py)
isolate owner callbacks with actual temporary SQLite files. Stable and nested
paths cover all three commands, plus ABA, clock-only observation, a genuine image
change and its existing conflict behavior. The preceding implementation failed
four no-op conflict cases; the corrected bridge passed all six methods.

The separate [typed dispatch check](../tests/probes/outcome_bridge_dispatch_checks.py)
uses the existing explicit reader/reference/hash arguments and a fresh output
directory. Each command starts with a retained Declined/R7 result. During typed
reconstruction, a nested cancellation commits G1 to G2 without changing R7.
The outer call refuses; the cancellation remains observable. An explicit later
retry returns the original decline without a write or application evaluation.
These three cases passed with 144 reader/reference calls and three setup
application evaluations. They are serial controlled callbacks, not real device
faults or a distributed execution claim.

The unchanged stock-adjustment regression passed with 104 reader/reference calls,
five application evaluations and final G5/R10/quantity7. The tag-box regression
also passed, preserving its ordinary business refusals, uncommitted byte-limit
failure and no-reexecution receipt recovery. Frozen application expectations were
not changed. No generated native application kernel, performance study, model
call, power-loss test or production durability claim is added.
