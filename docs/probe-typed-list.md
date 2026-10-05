# Experimental typed Text-list source profile

Separate program/invocation/result schemas: `bagaev-typed-list/1`,
`bagaev-typed-list-invocation/1`, `bagaev-typed-list-result/1`. Inherit the typed
optional-Int64 profile, including Text, complete static checking and existing
expression/work semantics. Existing schemas are unchanged. Source reasons use
LI_ rather than OI_. Entry results remain Bool/Int64 only.

Add type `TextList` (ordered, duplicates retained, immutable, 0..64 checked Text
values, total UTF-8 bytes <=4096) and these exact forms:
- `["list.text", E, ...]`: zero to64 Text operands, evaluated left to right.
  Check operand count in the structure phase before descent. After ALL operands
  succeed, validate aggregate bytes; overflow is runtime list-bound/LI_LIST_BYTES
  at this constructor node. Earlier child failures supersede this final check.
- `["list.len", L]`: TextList -> Int64.
- `["list.at", L, I]`: TextList and Int64 -> Text; evaluate L then I. Negative
  index or index >=length is runtime list-index/LI_INDEX at this operation node.
- `["list.contains", L, T]`: TextList and Text -> Bool, exact byte membership.
- `["list.increasing", L]`: Bool, strictly increasing scalar order; empty and
  singleton true, duplicates false.
- `["list.unique", L]`: TextList, ascending unique values, retaining the first
  input byte view for equal values. It never changes the input ordering/bytes.

All new forms use the inherited unit entry tick before children. After operands
succeed, reserve the following additional logical charge atomically at the
operation node, before doing membership/order/normalization work:
- contains: n + B + n*Q, with n=list length, B=aggregate list bytes, Q=query bytes;
- increasing: n + 2*B;
- unique: n*n + 2*n*B.
Construction, len and at have no additional charge. These are versioned logical
charges, not elapsed time or a performance estimate. A valid large value can
cause a work-limit refusal. Failure retains prior work, with the shared65536 cap.

Static type mismatch uses the offending operand node, following inherited
require-type behavior. Both branches and all functions are checked. TextList may
flow through parameters, locals, branches, helpers and loops, but cannot leave
an entry result; reject non-scalar entry result after all function type checks
at `/functions/ENTRY/result`.

Invocation TextList is a JSON array of strings. Check its array tag and64-item
bound first. Then validate every item left to right for a scalar string and
existing per-Text bounds, reporting malformed items at `/arguments/i/j`. Finally
check aggregate bytes, refusing at `/arguments/i`. Outer tag/count refusals also
use `/arguments/i`. Whole program checking precedes all argument checking. All
argument refusals use LI_ARGUMENT and work0. Arguments consume no language work.

The reference may own bounded descriptor vectors while borrowing immutable text
bytes from checked source or owned invocation strings. No text view may outlive
those owners. This does not extend the value library's no-heap claim to the
whole interpreter. No mutation, append, map/filter, records, native List ABI or
application completion is claimed. Freeze values, work and errors before
implementation; native lowering needs a later explicit layout/conformance pass.

## Recorded reference observations

The 32 pre-implementation cases matched complete result wires. Another 65
inherited Text/Option cases matched after schema/reason-prefix adaptation. Five
concrete reference mutants exited normally with complete but wrong records and
were detected. See `examples/probes/typed-list-observations.json`. These are
reference observations, not native-list conformance or performance evidence.
Review was a separate same-maintainer pass, not independent review.
