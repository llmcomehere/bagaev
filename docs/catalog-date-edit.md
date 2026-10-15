# Keep, set or clear a catalogue date

The separate pure `catalog-date-edit/1` application changes one selected date
without reindexing tags. It reuses the existing sixteen-entry catalogue data
types and form5/profile11 operations. Existing catalog-application/2 and/3
contracts, sources and oracles are unchanged.

## Request and behavior

A request has exactly `interface`, `state`, `entry_id` and `action`.
The interface is `catalog-date-edit/1`; state and IDs follow
[the sixteen-entry catalogue](catalog-wide.md). An action is exactly one of:

```json
{"kind":"keep"}
{"kind":"set","day":0}
{"kind":"clear"}
```

Keep preserves the date's presence/value. Set writes an integer day from0 to31,
including zero. Clear removes the date key if present. Null, Bool, floats and
out-of-range days are invalid. No other field changes: IDs, titles, entry order,
and both tag arrays retain their exact contents, duplicates and order. Unlike
catalogue refresh, this operation never normalizes tags.

The returned state is detached from the input. Its separate ID view sorts known
dates by(day,id), then missing dates by ID, matching revision3 ordering. Clearing
a date is therefore observably different from setting it to zero.

Success is `{kind:"success",state:{entries:[...]},entry_ids:[...]}`. Refusal is
exactly `{kind:"refusal",reason:...}`, without partial state. This is a pure
returned value, not a persistent update, transaction, migration or authority.

## Validation order

Before any transformation:
1. invalid-request: all exact object shapes, required/unknown fields, array
   limits, interface, target ID, command, ID/title/tag grammar and bounds.
   Set requires its day key, but its value is checked at the next gate.
2. invalid-date: any stored date or Set day is not an exact integer0..31.
3. duplicate-entry-id.
4. entry-order.
5. origin-collision in stored tags.
6. entry-not-found.

All state entries are validated even for Keep/Clear or a missing target. An
operation cannot clear malformed state to bypass validation. State permits0..16
entries, each tag array0..4, IDs/tags1..8 ASCII identifier characters and titles
1..16 printable ASCII characters, as in application/3. The value-level boundary
accepts ordinary finite JSON values; cycles/custom objects and concurrent input
mutation are outside the contract. JSON text parsing is a separate boundary.

## Implementation and bounded acceptance

The ready [clear-date argument array](../examples/probes/catalog-date-edit/clear-date.arguments.json)
clears a's known day0 while preserving repeated tags. The expected state omits
a's date and keeps both entries and tag arrays unchanged; its ID view is [a,b].
Prepare inert invocation data into a new file:

```sh
python -B -S tools/record_text.py prepare \
  examples/probes/catalog-date-edit/Catalog.bagaev --form 5 \
  --arguments examples/probes/catalog-date-edit/clear-date.arguments.json \
  --output clear-date.invocation.json
```

This command does not run the application. A separately authorized reviewed
profile11 reference can consume that invocation. It is the existing frozen
clear-zero case, not an additional semantic acceptance case.

- [Readable source](../examples/probes/catalog-date-edit/Catalog.bagaev)
- [Frozen literal oracle](../examples/probes/catalog-date-edit/cases.json)
- [Ordinary Python reference](../src/catalog_date_edit_reference.py)

The 33-case oracle was reviewed before implementation. It distinguishes missing
dates from zero, checks the final entry at capacity16 and refusal at17, preserves
tag duplicates/order, and discriminates validation priorities and exact shapes.
All33 ordinary comparisons and all33 typed-reference invocations passed. The
ordinary-reference test also checks exact scalar types, unchanged inputs on
success/refusal and absence of input/output container aliases. One test method
contains33 cases; it is not33 independent test methods.

After separately authorizing a reviewed profile11 reference, run
`tests/probes/catalog_date_edit_checks.py` with its explicit reference path,
SHA-256 and fresh output directory. The harness retains complete results.
The language implementation uses existing optional values, records and bounded
folds; no new opcode or resource limit is introduced. These finite observations
are not independent reproduction, performance, model-cost or production claims.
