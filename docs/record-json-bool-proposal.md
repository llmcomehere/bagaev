# Explicit Json Boolean projection, candidate profile 12

Status: source proposal and data-codec checks. Runtime qualification is NOT_RUN.
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
wrong-fallback type and legacy refusal. They are expectations, not observations.
Nineteen /12 graphs roundtripped through both data encoders; four new data tests
and29 existing wide-form tests passed. Five metadata-only Rust compiler checks
passed for the candidate reference and four existing native emitter entrypoints.
No linked candidate reference or generated native module was executed.

Before acceptance: complete the frozen runtime cases; compare legacy reference
observations and schema refusal controls; add number-kind coverage; retain the
compact-reference byte budget when this profile becomes usable. Until then the
main compact guide and existing tools continue to describe the accepted /11
route. A future faithful Json application adapter and native qualification are
separate work, not implied by parsing, compilation or source integration.
