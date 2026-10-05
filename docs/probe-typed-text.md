# Experimental typed Text execution profile

Contract: `bagaev-typed-text/1`, frozen before implementation. No existing schema
is changed. This specifies a separate experimental program profile; it does not
claim an implemented evaluator, native ABI or production acceptance.

The [scalar source contract](typed-scalar-source.md), [kernel evaluation rules](probes.md#invocation-and-evaluation)
and [Text value contract](probe-text-values.md) supply explicitly inherited rules.

## Grammar and type boundary

Program schema: bagaev-typed-text/1. Inherit the exact inferred-local scalar
program shape, identifier/scoping rules, expressions, structural limits and
explicit function signatures from bagaev-typed-scalar/1. Add the type Text and:

- ["text", STRING] -> Text
- ["text.eq", LEFT, RIGHT] -> Bool, both operands Text
- ["text.lt", LEFT, RIGHT] -> Bool, both operands Text
- ["text.bytes", VALUE] -> Int64, operand Text
- ["text.scalars", VALUE] -> Int64, operand Text

No concatenation, slicing, conversion, Unicode normalization, containers or
external calls. Existing arithmetic/comparisons keep their original type rules;
new Text comparisons are explicit operators. Let/if/call/loop may carry Text by
immutable reference. Functions may return Text internally, but the entry result
must be Bool or Int64. Text export/native ABI is excluded from this first profile.
No overloaded equality or automatic string/int/bool conversion.

All source literals must contain Unicode scalars, at most 1024 UTF-8 bytes and 256
scalars; empty/control/NUL/noncharacter values are valid. A literal reuses a
program-owned immutable value. Calls may return a parameter or literal reference
because all program/input backing bytes remain alive through the invocation.
No mutation, allocation-based string construction or escaping source handle exists.

## Static phase and identity rules

Preserve scalar source phases: transport/version/exact structure and scopes,
reference resolution, cycle detection, ordered type synthesis. All branches and
loop bodies are statically checked. Extend node kinds/types without changing
old profile identities. New complete preorder includes Text nodes.

Transport UTF-8 failure is TX_JSON. A JSON-decoded isolated surrogate inside a
Text literal is TX_SHAPE at its string field. A valid scalar literal beyond
byte/scalar bounds is TX_BOUNDS at that field. Other errors mirror TS_* with
TX_* prefixes. Check literal payload after operation arity, in normal structural
preorder; do not let a later type error mask it.

After every function passes type synthesis, require the resolved entry result to
be Bool/Int64. An entry declared Text yields TX_TYPE at /functions/ENTRY/result.
This final gate is explicit, so an earlier function-body type error still wins.
Canonical program identity includes this new schema and every literal. It must
never be substituted for the lowered scalar identity from the earlier adapter.
There is no lowering from Text programs to the old scalar kernel in this slice.

## Invocation boundary

Invocation has exactly schema, program, arguments; schema is
bagaev-typed-text-invocation/1. Use the existing probe invocation limits:1MiB
encoded frame, depth 132,16384 value occurrences. Check transport/envelope/bounds,
then the entire program, then argument count and values in signature order.
Maximum 8 arguments; complete validated Text payload therefore at most 8192 bytes.
This bounds argument payload only, not parsing allocation or process memory.

Int64/Bool argument rules stay exact. A Text argument must be a scalar JSON
string and satisfy the Text value limits. A wrong tag, isolated surrogate or
oversized Text argument gives TX_ARGUMENT at /arguments/INDEX. No coercion,
replacement decoding, implicit normalization or partial invocation occurs.
Invalid invocation/static result has work 0. Program diagnostic locations gain
/program; argument locations already refer to the whole invocation.

The evaluator borrows checked argument values and checked program literals for
one invocation. Return only Bool/Int64 data and a work/error record. Native
pointers, linking, execution admission, persistent storage and host callbacks
are not fields or side effects of this interface.

## Work and runtime errors

Work starts 0, limit 65536. Every entered expression first attempts a unit tick,
before children, exactly as in the scalar kernel. At the limit, fail work-limit
at that node without entering children. Calls, let, if and loops retain original
left-to-right/lazy ordering. Ordinary scalar nodes retain original charges.

Additional Text charges:
- A Text literal, after its entry tick, reserves its UTF-8 byte length.
- Text equality/order, after both operands finish, reserves the sum of their
  UTF-8 byte lengths regardless of prefix, early mismatch or shared storage.
- Text argument/reference and both length operations add no byte surcharge.

Reserve an additional charge atomically. If it exceeds remaining budget, fail
at the primitive node and retain work before that reservation; do not saturate
or partially consume the budget. Node-entry and earlier operand charges remain.
An earlier operand failure aborts before any later operand/surcharge. Untaken
branches incur no runtime charge. Optimizations must preserve all these logical
charges; they do not represent elapsed time or machine instructions.

Result schema bagaev-typed-text-result/1 retains exactly schema,status,reason,
location,value_type,value,work. Success: Bool/Int64 value with null reason/location.
Runtime errors: integer-overflow(TX_OVERFLOW) or work-limit(TX_WORK), null type/value.
Invalid-ir uses the specific TX_* code, pointer, null type/value and work 0.
A failed extra reservation can leave work below 65536; this is deliberate and
must not be confused with the old scalar unit-only failure behavior.
Allocation/process/output errors are environment failures, not language results.

## Pre-implementation fixture scope

[The 26 literal invocations](../examples/probes/typed-text-cases.json) contain complete
expected result fields, work and error pointers. They cover exact/insufficient
budgets induced by bounded loops (not a caller-selectable limit), a scalar-only
example, invalid untaken code/arguments, byte/scalar lengths, Text helpers/loops
and the scalar entry-result restriction. These finite cases are not full
conformance coverage, an independent reviewer or permission to execute a candidate.

Program JSON depth/count bounds apply to the program subtree with its root at
depth one; invocation bounds apply independently to the whole frame. Source
expression bounds remain depth 32 and 512 occurrences across all functions.
Canonical result JSON is followed by one LF; environment output failure must
not become a truncated language success. No command/path/authority is inferred
from invocation data.

## Bounded reference implementation

The separate [Rust reference evaluator](../examples/probes/backend/rust/typed_text.rs)
and [explicit CLI](../examples/probes/backend/rust/text_main.rs) now check and
evaluate this profile. They do not alter or lower through the old scalar IR.
The CLI accepts `run --input FILE`, with bounded regular-file input and one
complete result on stdout. Text values flow through literals, arguments, locals,
helpers and loops; only Bool/Int64 can leave the entry result.

All 26 [pre-frozen invocations](../examples/probes/typed-text-cases.json) matched
complete result wires, including work and error pointers. Another 25 old static
refusals were adapted after implementation; one initial location assumption was
corrected because the whole-invocation depth gate precedes program checking.
The original mismatch and the derivation are disclosed in the
[observations](../examples/probes/typed-text-observations.json). No frozen oracle
or candidate behavior was changed to repair that adaptation.

Rust 1.93.0 compiled the reference with warnings denied. This is executed
reference-interpreter evidence and a separate same-maintainer review, not a
generated native Text backend, independent review, complete conformance,
performance result or production admission.

## Reference-evaluator negative controls

Six concrete mutations were compiled separately and detected against unchanged
pre-frozen invocation expectations: free Text literals, free comparisons, byte
counts substituted for scalar counts, length-only equality, partial failed work
reservation, and rejecting an exactly exhausted work budget. Each witness exited
normally with a complete but wrong result wire; crashes and build failures did
not count as detections. See the [literal observations](../examples/probes/typed-text-mutation-observations.json)
for exact edits, source identities, expected and observed results.

The unmodified evaluator source and frozen fixture were unchanged. This is a
separate same-maintainer finite negative-control pass, not proof of arbitrary
defect detection, independent review, native Text execution or performance.
