# Source-once Json reference calls, profile 12

The explicit reference API checks a Json-only source once, owns its canonical
source and prepares separately owned arguments for repeated evaluations.
It extends the Boolean-capable reference without requiring native compilation.
No native handle, unsafe dispatch, speed claim or execution authority is added.

In `typed_record.rs`, use `prepare_json_program_v12`,
`prepare_json_arguments_v12` and `evaluate_prepared_json_v12`.
The distinct `PreparedJsonProgramV12` and `PreparedJsonInvocationV12` types
prevent accidental use of older prepared handles. Source schema must be /12.
All existing /10 and /11 APIs and wire versions remain unchanged.

Each evaluation starts logical work at zero and returns the normal complete
result/12 envelope, including runtime failure reason and source location.
Json Booleans retain their actual values and lazy fallback semantics.
Caller source and argument buffers may be released after their preparation;
returned bytes are owned independently of the prepared handles.

The existing source-once budget convention is retained: 70 envelope bytes plus
canonical source bytes plus raw argument bytes must fit the 1 MiB frame limit.
Canonical source value count plus argument value count plus two must not exceed
16,384. Argument depth is checked in its conceptual invocation position.
This is a prepared calling convention, not preservation of arbitrary original
invocation whitespace. Malformed JSON, non-array arguments, wrong arity,
non-Json entry parameters, wrong schema and exceeded bounds refuse preparation.

## Finite checks

On 2026-10-11, 47 existing valid-source cases were replayed twice through the
new prepared reference: 24 Boolean/projection cases and 23 JSON active-total
application cases. All 94 complete envelopes matched the previously frozen or
recorded reference responses, including work and failure locations. Source and
argument buffers were overwritten and released before evaluation; returned
bytes were retained after both handles were released.

[Portable tests](../examples/probes/backend/rust/prepared_json12_tests.rs)
cover Boolean/fallback parity, ownership, repeated work reset, lazy overflow,
explicit version refusal and byte/value boundaries. The existing /11 prepared
reference suite also passed unchanged. This finite parity check shares the
reference evaluator; it is not an independent backend proof or measurement.
Generated native /12 qualification remains a separate gate in PR #239.
