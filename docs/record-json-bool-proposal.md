# Explicit Json Boolean projection, candidate profile 12

Status: finite reference qualification completed on 2026-10-10; see PR #237
for integration status and exact-head review/CI.
This does not extend the accepted profile11 native interface or admit execution.

The active-total application needs to distinguish Json true and false. Existing
profile11 `json.kind` returns `bool` for both, and its other projections do not
extract a Bool. Changing input to integer 0/1 would change the application
contract. Typed record-list entries are not accepted by the current Json-only
native emitter either.

The candidate introduces only `json.bool_or(Json, Bool) -> Bool`: evaluate the
Json operand; for actual true/false return that value, otherwise evaluate the
fallback. No coercion. Fallback type-checking is mandatory even if that branch
will not run. The operation and its Json operand each charge one logical tick;
fallback work is charged only when evaluated. No extra payload-byte charge is
needed for reading a Boolean.

Selection is explicit: typed-record/12, invocation/12 and result/12, with
record-form/6 for the separate data codec. The record/list capacities and other
limits remain those of profile11. Profiles1–11 and record-form/5 keep their
existing operation set and refuse the new operation/version. No automatic
migration or fallback is provided. The /8–/11 native emitters explicitly refuse
the new IR node; no native /12 emitter, binding or adapter is supplied.

[Twenty independently frozen cases](../examples/probes/record-json-bool/cases.json)
fix complete intended responses for Boolean identity, non-Boolean fallback,
missing fields, lazy overflow suppression, evaluated fallback overflow, static
wrong-fallback type and legacy refusal. Their frozen bytes remain unchanged.
Nineteen /12 graphs roundtripped through both data encoders; four new data tests
and29 existing wide-form tests passed. Five metadata-only Rust compiler checks
passed for the candidate reference and four existing native emitter entrypoints.
These compiler checks were historical metadata-only observations.

On 2026-10-10, linked references /11 and /12 were built from source commit
`5a01f01d5aa8d03d8734057bfcb82cdeb124b97b` with Rust 1.93, edition2021,
`-Dwarnings -O`. All20 frozen cases and [ten supplemental cases](../examples/probes/record-json-bool/supplement.json)
matched their complete expected result envelopes, including work and locations.
The supplement covers fraction/exponent/negative-zero fallback, old outer/inner
schemas, missing arguments and a wrong Json operand.

[Recorded qualification](../examples/probes/record-json-bool/qualification.json)
contains82 new reference observations:30 operation/version cases and52 legacy
replays. The latter replay the12 active-total,6 boundary and8 order cases on both
references, changing only explicit input/output schema versions for /12. All
complete envelopes matched. Four new codec tests and ten selected existing
codec/application tests were rerun;19 new graphs roundtripped through both
encoders and12 old graphs retained old-form roundtrips and version refusal.
This is finite reference evidence, not a full-language conformance proof.
No generated native module was executed, and no native /12 path is supplied.

Before integration: retain separate exact-head review and passing CI. The
compact guide and existing tools still describe the /11 route; extending them
must retain the compact-reference byte budget. A future faithful Json
application adapter and native qualification are
separate work, not implied by parsing, compilation or source integration.
