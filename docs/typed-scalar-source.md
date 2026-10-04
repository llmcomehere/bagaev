# Experimental scalar source with inferred locals

Contract proposal: `bagaev-typed-scalar/1`, frozen for the bounded experiment
below. No adapter implementation or execution is claimed by this specification.
This is not full L3, native L2 equivalence or a production profile. The unchanged
[scalar kernel contract](probes.md#typed-kernel-grammar) supplies the target
semantics. Text, arrays, records, imports, effects and storage are unsupported.

## Source grammar

A program has exactly `schema`, `entry`, `functions`; schema is
`bagaev-typed-scalar/1`. Functions have exactly `params`, `result`, `body`.
Identifiers, explicit parameter/result types, expression forms and all source
bounds follow the scalar kernel contract, with precisely two grammar changes:

- `let`: `["let", ID, value, body]`, inferring the local type from value.
- `loop`: `["loop", count, indexID, accumulatorID, initial, body]`, inferring
  accumulator type from initial. The index type remains Int64.

Only Int64 and Bool exist. Parameters/results stay explicit. No coercions,
implicit annotations, recursive inference, overloaded operations or latest-name
lookup are introduced. A let name is visible only in its body. A loop's names
are visible only in its body. Freshness, active-shadowing refusal and separate
`arg`/`use` namespaces are unchanged. An empty or zero-count branch is still
statically checked.

Limits are 1,048,576 transport bytes, JSON depth 128 and 8192 value occurrences,
1..8 functions, at most 8 parameters each, 512 expression occurrences, expression
depth 32, literal loop counts 0..1024 and signed Int64 literal endpoints.
Object keys are not JSON value occurrences. Root depth is one. Repeated
expressions count separately; metadata is not an expression occurrence.

## Ordered static checks and diagnostics

Complete these phases before returning a lowered draft:

1. Byte bound, then complete UTF-8/JSON grammar and duplicate-key detection.
2. Exact envelope/version, JSON bounds, then full structure and lexical scopes.
3. References: entry first, then function-ID order and body preorder, including
   exact call arity. Structural checking completes before name resolution.
4. Acyclic direct-call graph: sorted-ID DFS, sorted callees, first preorder call
   for repeated edges. Refuse the first edge to a grey function.
5. Types: functions by ID; infer each child and immediately check its required
   type before visiting the next child. Check complete body against result type.

Use `TS_JSON`, `TS_VERSION`, `TS_SHAPE`, `TS_BOUNDS`, `TS_REFERENCE`, `TS_CYCLE`
and `TS_TYPE`. Apart from the two grammar changes, exact priorities and pointer
rules are the kernel's [static refusal order](probes.md#static-refusal-order),
with `TS_` replacing `IR_`. There is no invocation/argument phase in this source
interface. All pointers refer to the source, not the lowered program.

A malformed transport reports root; a byte overrun takes priority over JSON.
A missing/non-string schema is shape, another schema string is version at
`/schema`. Exact-field failures report their containing object. Source let
value/body indices are 2/3, loop initial/body indices 4/5. These must not be
reported using the kernel's shifted indices.

Type synthesis follows the kernel operations. A let's inferred value type
becomes its binder type before its body is inferred; there is no annotation
check. A loop infers its initial type, binds the accumulator with that type and
requires the body's type to agree. Its index is Int64. `arg`/`use` return their
resolved binding type; calls use declared signatures without recursively typing
the callee. A return mismatch reports the complete body. Both conditional arms
are checked regardless of a constant condition; runtime remains lazy.

## Lowering and occurrence mapping

Lower to `bagaev-probe-ir/1` by inserting each inferred local/accumulator type in
the kernel's existing let/loop position. Preserve every other identifier,
function signature, expression, argument order and literal. No optimization or
work counter is added by inference. Existing semantic charges and runtime error
order remain properties of the unchanged lowered kernel.

Every source expression has one origin record with exactly `id`, `source` and
`lowered`: one-based complete preorder ID and two JSON pointers. Visit functions
in sorted ID order and expressions in source child order, including both arms.
Type metadata inserted by inference is not a new expression occurrence. A
metadata diagnostic belongs to the source binder, not a fabricated source index.
Do not infer locations from serialized byte offsets or globally subtract one.

Check the complete lowered program with the existing trusted kernel checker
before returning success. Any unexpected rejection there is an adapter/environment
inconsistency, not a new source refusal or permission to repair/repin a source.
This final check does not execute code.

## Detached result boundary

A successful library result has exactly:

- `schema`: `bagaev-typed-source-result/1`;
- `kind`: `draft`;
- `source_pin`: H of the complete canonical source program;
- `lowered`: the complete canonical kernel program;
- `lowered_pin`: its existing kernel identity H(lowered);
- `origins`: the ordered origin records above;
- `execution_admission`: false.

H and canonical JSON are the kernel's existing canonical representation/hash
rules. Distinct schema bytes preserve distinct source and lowered identities.
A source pin is never substituted for a lowered identity. On language refusal,
return exactly `schema`, `kind`=`refusal`, `code`, `source_location` and
`execution_admission`=false. Environment/allocation/adapter failures stay outside
these language records. If a wire representation is provided, it is canonical
JSON plus one LF, bounded by 8 MiB; exceeding that bound is an environment failure.

The interface itself performs no filesystem operations, subprocesses, code
loading, network, cache promotion, deployment or admission. A caller may supply
bytes, but cannot turn the detached draft into execution authority by changing
an output field.

## Pre-implementation examples

[Literal cases](../examples/probes/typed-scalar-literals.json) contain 9 success
and 17 refusal cases. [Boundary cases](../examples/probes/typed-scalar-boundaries.json)
contain 10 structural cases, 5 raw transport cases and 2 byte-bound recipes.
Expected lowerings and refusal locations were authored before a candidate
adapter. Boundary counts are explained in the data. Origin maps are derived
only from the declared source/target field layouts, without a candidate checker.
The basic nested index shift also has a separately written literal map.

These 43 cases are a bounded initial suite, not proof of arbitrary correctness.
Freeze their identities before implementation; report a contract defect rather
than silently changing expected results to match a candidate. This experiment
adds no production backend choice, full container language, model-cost claim or
runtime behavior beyond the frozen scalar kernel.
