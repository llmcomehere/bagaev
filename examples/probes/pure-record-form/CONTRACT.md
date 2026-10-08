# Pure readable record-form/1

A separate data-only envelope over bagaev-typed-record/10:
`bagaev record-form/1; program { declarations; entry NAME; functions; }`.
No component, owner, policy, identity or revision metadata is invented. Reuse the
explicit form7 expression vocabulary and named record/list/variant declarations.
Unsupported typed-record operations stay outside this representation subset.
No semantic checking, evaluation, admission, header detection or old-form upgrade.

Pure encode/decode preserves the entire supported program exactly, including
function order-independent maps and ordered parameters/operands/arms. The actual
core owns references, types, call cycles, work, argument/value and graph limits.
Expose a separate file converter, with existing bounded regular-file read and
exclusive new-output behavior; do not alter component conversion defaults.

Freeze literal programs/results before implementation: simple arithmetic,
record projection, ordered record-list fold, Text byte count, exhaustive variant
match and wrong-type syntactically representable program. Pure function input
and results require no durable receiver or operation receipt.
