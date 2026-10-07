# Readable pure record-list helpers

Explicit component-form/7 represents the existing typed-record/10 named record
lists inside component-source/2. It changes neither the core nor the owned
component boundary.

```text
record Item { value: Int64 };
list Items of Item capacity 4;
fn calc() -> Int64 =
  let items = records.list(Items, Item { value: 3 }, Item { value: 1 }) in
  fold (4, 0) with (idx, total) in
    if idx < records.len(items)
    then let item = records.at(items, idx) in total + item.value
    else total;
```

The helper returns 4. Declarations use a literal capacity 0–4 and a named record
element. `records.list(Name, ...)` preserves order and the nominal list type.
Fixed records.len, records.at and records.push calls retain the existing arities,
index checks and immutable append behavior. An append exceeding capacity reports
RR_RECORD_LIST_ITEMS. Record-list identity is not interchangeable merely because
two declarations have the same shape.

## Boundary that remains closed

Lists may appear in pure helpers and local computation. The existing component/2
checker still refuses record lists inside owned state, request or error graphs
with CS_OWNED. Actual source/policy checks exercised both an accepted pure-helper
case and this owned-graph refusal. This is not persistent catalog state support,
a new native ABI, live admission or a larger capacity profile.

Use `tools/component_text.py` with explicit `--form 7`. Default2 and earlier
selectors remain unchanged. The new declaration words list, of and capacity are
reserved only in this version. The fixed diagnostic/edit/location APIs do not
automatically accept form7. Encoding retains exact decode roundtrip and refuses
lossy or unsupported graphs.

## Bounded checks

[Cases and contract](../examples/probes/component-record-list/CONTRACT.md) freeze
seven exact graphs and literal results, three syntax refusals, and three actual
core refusals. The initial push-capacity expectation used the TextList error
name; the existing source defines RR_RECORD_LIST_ITEMS. Only that expected label
was corrected, preserving the original failed observation and all product code.

Portable `component_record_list_checks.py`, `component_record_list_core_checks.py`,
`component_record_list_boundary_checks.py` and `component_record_list_cli_checks.py`
use the established explicit output and reviewed host/hash arguments. Supplemental
checks cover owned rejection, malformed encoder operands, five prior fold graphs
and prior-version refusal. Runtime locations/work are observations, not independent
full-wire oracles. These are finite conformance checks, not performance, model
preference or production acceptance.
