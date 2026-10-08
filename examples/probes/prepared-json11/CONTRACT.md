# Explicit source-once profile11 Json reference API

Add separate PreparedJsonProgramV11 and borrowed PreparedJsonInvocationV11,
prepare_json_program_v11, prepare_json_arguments_v11 and
 evaluate_prepared_json_v11, mirroring the accepted explicit /10 API. Keep the
entire old source prefix and all older APIs unchanged. No native adapter or
execution-control helper in this slice.

Prepare and type-check profile11 source once, require all Json or zero entry
parameters, retain owned checked source/canonical bytes and canonical source
value count. Per-call preparation owns copied Json arguments, checks exact arity
and the same conceptual canonical-envelope budget as /10: 70+canonical source
bytes+raw argument bytes <=1MiB; source JSON values+argument JSON values+2<=16384;
argument depth/shape limits unchanged. This explicit convention is not byte-for-
byte equivalence with arbitrary original invocation whitespace.

Each evaluation uses the unchanged profile11 runtime, starts logical work at zero
and returns owned profile11 result bytes, including the same runtime refusal and
location as full invocation evaluation. Dropping/reusing original source or raw
argument bytes cannot invalidate the prepared owners. Preparation/type checking
is not permission to invoke native code or bypass an execution profile.

Before implementation pin existing32 original batch and40 total10 cases and
five source-failure cases (overflow/underflow/index/list capacity/work). Compare
full and prepared result bytes, not selected fields; repeat one prepared call
and reuse source across changing arguments to expose state leakage. Freeze
negative profile10, non-Json signature, non-array, arity, malformed JSON,
conceptual frame/value bounds and oversized source cases. Preserve /10 regression.
Run only owned reviewed code under existing bounded profiles; no performance or
model measurement, new dependency or controls. Native preparation remains later.
