# A faithful JSON active-total entry

The [readable source](../examples/probes/json-active-total/ActiveJson.bagaev)
uses explicit record-form/6 and reference profile12 to apply the
[existing active-total calculation](record-work-walkthrough.md) to Json input.
It does not add a new evaluator, native interface or automatic profile selection.

Input is an array of at most sixteen exact objects: amount is an Int64 integer
token and active is an actual Boolean. Missing or extra fields, a non-array root,
non-object elements, out-of-range amounts and incorrect field types reject the
whole input. Inactive items must also be valid. A fractional or exponent token
is not an integer even when its mathematical value is integral. Integer -0 is
zero; fractional -0.0 is not an integer. These follow the existing json.int rule.

Validation completes before aggregation. Valid input produces Outcome with
valid=true and total equal to the input-order checked sum of active amounts.
Inactive amounts never enter arithmetic. Invalid input produces
{valid:false,total:0}; it cannot masquerade as a valid zero total. An overflowing
selected addition retains the language RR_OVERFLOW refusal, with no partial
Outcome. A later invalid item rejects input before any earlier overflow can run.
The old nominal typed entry and its argument-refusal behavior remain unchanged.

## Evidence and boundaries

[Twenty literal business cases](../examples/probes/json-active-total/cases.json)
and [three lexical controls](../examples/probes/json-active-total/lexical-cases.json)
were frozen before source implementation. They cover true/false selection,
positive and negative overflow, skipped overflow, sixteen/seventeen items,
invalid shapes and types, validation-before-arithmetic, and numeric token kinds.

On 2026-10-10 all23 cases matched both the unchanged ordinary Python baseline
and23 separately executed reference12 calls. The source roundtripped through
both form6 encoders. [Full observations](../examples/probes/json-active-total/observations.json)
retain language work and locations. Those fields are captured observations,
not independently frozen full-envelope expectations; the oracle is the business
status/value projection. Portable data tests do not launch the reference.

The input is synthetic and bounded. There is no native12 adapter or kernel,
performance/model-benefit measurement, persistence, concurrency or production
admission. Use the explicit [lossless Json preparer](json-argument-prepare.md)
with `--form 6` to construct invocation12 data. The compact guide and general
record_text tool still select the existing profile11 route. Do not feed this
source to that route implicitly.
