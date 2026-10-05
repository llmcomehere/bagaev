# Experimental typed optional Int64 source profile

Program schema: `bagaev-typed-option-int/1`; invocation schema:
`bagaev-typed-option-int-invocation/1`; result schema:
`bagaev-typed-option-int-result/1`. This is a separate successor probe; existing
Text/scalar/L2 schemas and their interpretation remain unchanged.

Inherit the complete typed Text syntax, structural limits, static phase order,
reference/cycle checking, lazy branches/calls/loops, arithmetic and work rules.
Add the type `OptionInt64` and exactly four forms:

- `["none.int"]`: OptionInt64 None.
- `["some.int", E]`: E is Int64, produce Some(E).
- `["option.is_some", E]`: E is OptionInt64, result Bool.
- `["option.or", E, F]`: E is OptionInt64; F is Int64. Evaluate E first. Return
  its present Int64 without evaluating F, or evaluate F exactly once for None.

No sentinel integers, automatic coercion, generic sums or overloaded `eq` are
introduced. OptionInt64 may occur in function signatures, locals, if branches
and loop accumulators. Both fallback arms/types are checked statically even when
unreached at runtime. Type mismatch for these new forms refuses at that form's
source node. The entry result remains Bool or Int64; reject Text/OptionInt64
entry result after all function type checks, at `/functions/ENTRY/result`.

Every new expression uses one unit entry tick before any child. None has only
that tick; Some/is_some evaluate one child; option.or evaluates its first child
and only the needed fallback. No extra byte surcharge for optional Int64 values.
The shared 65536-work cap, atomic Text byte costs and first-error semantics stay.

Invocation OptionInt64 argument: JSON null = None; a JSON integer within Int64
= Some(value), including zero. Bool/float/string/array/object or oversized integer
refuse at `/arguments/i`. This language invocation encoding is not the catalog
application's absent-field encoding and does not modify its validation rules.
Whole program is checked before arguments; arguments validate left to right.

Result fields and canonical wire follow typed Text but use the new schema and
OI_ reason prefix. Static/refusal work is0. Runtime overflow/work-limit retain
exact work and invocation-prefixed node pointer. No OptionInt64 is exported as
an entry result. Environment failures stay outside domain results.

Freeze literal values/work/locations before implementation. Test None versus
Some(0), fallback laziness, all checked types, args, helpers, branch merges and
loops. Source integration does not establish native lowering or ABI support;
those require a separate contract and conformance pass.

## Bounded reference implementation

The separate [checker/reference evaluator](../examples/probes/backend/rust/typed_option.rs)
and [CLI](../examples/probes/backend/rust/option_main.rs) implement this profile.
All 24 [pre-implementation invocation cases](../examples/probes/typed-option-int-cases.json)
matched complete result wires. Another 41 existing Text cases passed after
only schema/reason-prefix adaptation; original fixtures and implementation were
unchanged. [Observations](../examples/probes/typed-option-int-observations.json)
distinguish the frozen new cases and adapted regressions. Rust1.93.0 compiled
with warnings denied. Separate same-maintainer review, not independent
reproduction, native optional support or application acceptance.
