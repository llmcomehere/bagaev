# Ordinary native inventory baseline

The [ordinary Rust source](../examples/probes/inventory-native-baseline/baseline.rs)
implements both the [original batch](inventory-batch.md) and
[total-ten policy](inventory-batch-change.md) with ordinary `Vec`, `String`, loops
and a running total. It neither translates nor evaluates a bagaev programme.
It preserves shape precedence, individual business failures, first rejection,
original-stock rollback and per-step receipt snapshots. Stock validity is reused
after a successful step because positive bounded decrement preserves it; repeated
quadratic validation was removed before the conformance run.

## Shared and different boundaries

Only the existing JSON transport parser is shared with bagaev. This is an
independent business implementation, **not** an independent JSON parser. The
[frozen inputs](../examples/probes/inventory-native-baseline/frozen-inputs.json)
and [source manifest](../examples/probes/inventory-native-baseline/manifest.json)
identify the exact common dependency and unchanged 32/40 full outcomes.

The baseline CLI accepts `REQUEST_JSON_FILE original` or `REQUEST_JSON_FILE total10`
and writes the complete business Outcome as JSON. It does not accept a programme,
bagaev invocation or BCMPRES4 ABI. Consequently these conformance results are not
an equal-boundary performance comparison. A later measurement needs its own
frozen interface, accounting and execution profile.

Input is limited by the existing 1 MiB transport/parser bounds, and all decoded
strings (including keys) must be scalar UTF-8 of at most 256 bytes. This admits all
frozen cases. Lexical fractions/exponents are not projected to Int64; out-of-range
integers are shape failures. Out-of-profile text is refused before business
processing, so no general arbitrary-JSON parity is claimed. The regular-file
check is for owned fixtures, not a hostile-filesystem race-resistance guarantee.
The source uses no unsafe code, network, external effects or extra packages.

## Actual checks

Two Rust tests passed for JSON quoting and lexical Int64 projection. The reviewed
source compiled with warnings denied at Rust O0/O2. The 72 policy/case pairs
(32 original and40 total10, not 72 distinct requests) gave 144 fresh ordinary-native
calls matching every complete frozen value. Output bytes matched across builds,
input files were preserved, and two repeated multistep calls were deterministic.
Sixteen refusals covered eight input/usage conditions at both builds and emitted
no success stdout. Three portable tests verify source/input pins and the
[captured values](../examples/probes/inventory-native-baseline/observations.json)
and [refusal records](../examples/probes/inventory-native-baseline/refusals.json).
Those data tests are not additional native execution.

There were zero bagaev runtime calls and no time, memory, allocation, model or
cost measurements in this baseline slice. Same-maintainer conformance does not
establish independent acceptance, a general backend comparison or a performance
advantage for either implementation.
