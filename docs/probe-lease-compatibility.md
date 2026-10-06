# Clock-bound lease compatibility example

This is a pure predicate over supplied interval metadata using existing /8 JSON
operations. It reads no clock, creates no lease, renews nothing and authorizes
no action. Clock labels and ticks are assertions supplied by the caller. A
compatible result cannot establish trustworthy time or eliminate TOCTOU races.

## Contract

Four JSON arguments: parent lease, candidate child lease, previous child lease
or null, and observed time. A lease has exactly clock, origin, expires, cap;
time has exactly clock,tick. Clock is an integer 0..3 and all endpoints/ticks
are integers 0..2147483647. Booleans and floating tokens are invalid. Every
lease must satisfy origin < expires <= cap. Unknown/missing fields invalidate;
duplicate decoded keys are transport refusals. The ordinary Python function
accepts already decoded ordinary JSON values and cannot recover discarded keys.

Return a record with Text decision and reason, in this exact priority:

1. Validate parent, child, previous and time in order, returning invalid with
   that field name. Previous null is valid first creation.
2. Require all supplied clock labels to agree, else pending/clock-mismatch.
3. For renewal, preserve the previous child origin and hard cap, then forbid
   shortening expiry, then reject observed tick >= previous expiry. Reasons are
   origin-changed, cap-changed, expiry-shortened, previous-ended respectively.
4. Require child origin >= parent origin, child expiry <= parent expiry and
   child cap <= parent cap, else pending/outside-parent.
5. Reject tick < child origin as pending/not-started and tick >= child expiry
   as pending/ended.
6. Return compatible/initial or compatible/renewal as appropriate.

Intervals are half-open [origin,expires). Parent and child origins need not
coincide. Renewal can extend expiry within unchanged original cap and current
parent expiry. Unchanged expiry is an idempotent descriptive renewal while still
active. An expired previous lease cannot be revived merely by calling it renewal.
First creation has no previous-child prerequisite. Equal durations alone do not
prove interval containment or clock agreement. Endpoints are compared without
unchecked tick-plus-duration arithmetic.

## Portable material

- [Source](../examples/probes/lease-compatibility/program.json) and
  [ordinary function](../examples/probes/lease-compatibility/ordinary_reference.py)
  express the same finite contract, without adding a type or backend feature.
- [42 cases](../examples/probes/lease-compatibility/cases.json) preserve literal
  semantic records fixed before implementation. Complete reference/native wires
  and logical work are captured observations, not independent cost predictions.
- [Data helper](../tests/probes/lease_compatibility_wire.py): list; request CASE;
  check CASE --mode reference|native --output FILE. No compile or process launch.
- [Reference harness](../tests/probes/backend/evidence_reference_harness.rs.in):
  substitute {{BACKEND}} and supply the invocation file.
- [Native harness](../tests/probes/backend/lease_native_harness.rs.in): substitute
  {{BACKEND}}, link only the separately admitted exact-source /8 kernel, then
  supply invocation, fill 90/165 and expected work. Before dispatch it checks
  canonical source identity and four-argument arity. It snapshots all four JSON
  roots, observes one call, guards and unused tails, and validates owned output
  after temporary input/scratch owners are dropped. The wire binding retains
  the distributed-source digest; the artifact canonical digest is separate.

These files do not authorize native execution. Compilation and execution need
an admitted bounded environment; a hash or compatible decision is not permission.

## Finite evidence and limits

Earlier qualification matched 42 ordinary/reference cases and 168 native
observations (O0/O2, fills 90/165). Ten source mutations returned normal wrong
records. Four additional compiled native semantic controls also returned wrong
records; each was compared with its own binding and reference work, so digest
or charge changes alone could not trigger detection.

A conservative charge model matched all 42 reference counts. For fixed exact-key
bounded-integer inputs its initial/renewal bounds were 1,814/2,744, below 65,536.
This is not a compiler proof or a bound on arbitrary malformed inputs, wall time,
RSS or clock accuracy. Ordinary-language equivalence supports finite
expressibility, not language novelty, speed or model-cost superiority.

Exact-head CI validates documentation; native conformance is separate.
Same-maintainer review is not independent reproduction or production acceptance.

The portable packet was rebuilt against its integration-base backend. All 42
ordinary records, 42 complete reference wires and 42 O2/fill-165 native wires
matched the prior fixtures; regenerated LLVM and binding were identical. Five
comparator/refusal controls and documentation checks passed. This adds a replay
of the same finite cases, without new independent cases or measurements.
