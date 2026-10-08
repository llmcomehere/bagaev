# Explicit source-once Json reference profile11

The existing `typed_record` module now has separate `PreparedJsonProgramV11` and
`PreparedJsonInvocationV11` types and three explicit functions:

- `prepare_json_program_v11(source)`: parse/type-check source, require all-Json or
  zero entry parameters, retain owned checked source and its canonical identity;
- `prepare_json_arguments_v11(&program, arguments)`: prepare an owned per-call
  Json argument array with exact entry arity;
- `evaluate_prepared_json_v11(&invocation)`: use the unchanged profile11 reference
  runtime and return owned result bytes. Logical work starts at zero each call.

Source preparation includes a canonical-source parse for the value count. It is
not a claim that the input is literally parsed only once internally; that work
is done during preparation rather than repeated for each argument array. Old
APIs and the existing source prefix remain unchanged. This API neither compiles
nor invokes a native kernel and does not grant execution admission.

## Ownership and bounds

The prepared source owns its checked representation. Each invocation borrows that
source and owns copied Json values. Original source/argument buffers can be
changed or dropped after their preparation. Result bytes remain owned after the
invocation is dropped. Source handles may be reused with different arguments.

The separately selected convention mirrors prepared /10: the conceptual compact
invocation envelope costs 70 bytes plus canonical source bytes plus raw argument
bytes and must fit 1 MiB. Canonical source JSON values plus argument JSON values
plus 2 envelope values must fit 16384. The argument array depth is at most 131,
corresponding to the full invocation's 132. Existing source, signature and Json
bounds remain. This is not equivalence with arbitrary original source whitespace
or an implicit upgrade from /10. Raw argument numeric lexemes are not converted
to binary floats by preparation.

The typed reference still requires an admitted execution profile when used.
Preparation is source/type checking and data ownership, not permission to run
foreign native code. A prepared native adapter is not included in this slice.

## Conformance observations

Three new API tests and the existing SHA256 known-answer test passed serially,
with compiler warnings denied. On the existing 32 original and 40 changed batch
inputs, 72 full reference evaluations matched 72 prepared evaluations byte for
byte, including complete values, work and status. Two selected prepared calls
were repeated with identical results. Five runtime-failure fixtures matched full
and prepared result bytes, including reason/location/work, and each prepared
failure was repeated to check work reset.

In total this test run made 77 full and 84 prepared profile11 evaluations, plus one
full/prepared /10 pair. They are repeated conformance observations on existing
cases, not new semantic cases. Nine admission refusals and three exact boundary
successes cover version, signature, source size, array/arity, malformed JSON,
conceptual bytes/value count and depth. Ownership checks mutate/drop original
buffers and retain results after invocation drop. A portable Python test verifies
that the [derived argument files](../examples/probes/prepared-json11/manifest.json)
match their unchanged oracles.

The [Rust tests](../examples/probes/backend/rust/prepared_json11_tests.rs) and
[contract](../examples/probes/prepared-json11/CONTRACT.md) record the bounded scope.
No generated-native calls or timing, memory, allocation, model or cost measurement
was made. This does not prove arbitrary-input equivalence or performance gains.
