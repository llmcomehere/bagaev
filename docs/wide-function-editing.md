# Focused edits for the wider pure profile

`tools/record_function.py --form 5` explicitly selects the separate fixed
form5 implementation for extract, context and replace. Omitting this flag keeps
the original form4 behavior. There is no schema auto-detection or silent migration.

Use it with the [sixteen-entry catalogue](catalog-wide.md):

```sh
python tools/record_function.py context Catalog.bagaev --form 5 \
  --name select_next --output context.json
```

The context has schema `bagaev-function-context/2`; its nested fragment has schema
`bagaev-function-fragment/2` and form `record-form/5`. It carries the exact base
and old-function hashes, the selected function and complete type declarations,
and direct caller/callee signatures. It does not include other function bodies.
For select_next, the caller is view and the callee is before. These are syntactic
relationships, not a runtime reachability proof.

A replacement yields `bagaev-record-draft/2`. Only the existing selected function
body may change. Type declarations, signature, entry and all other functions are
preserved. Stale base/function pins, scope expansion and no-op replacements are
refused. The output is detached from the original; it neither executes nor
admits the proposed function. A changed body still needs semantic review and
appropriate bounded checks. Output files must be new.

A frozen candidate wraps id_ok in a true conditional without changing its result.
It matched all fifteen application/3 literal responses through the reviewed
profile11 reference. Seven API refusals, six CLI operations including wrong
implicit form and existing-output rejection, context and detached-state checks
passed. The unchanged form4 check also passed all99 responses, seven refusals
and four CLI operations. These are bounded same-maintainer observations.
Fragment byte counts are not token-cost or model-preference measurements.

[Diagnostics and formatting](wide-authoring.md) separately support explicit form5.
Whole-program draft tools retain their earlier version limits.
