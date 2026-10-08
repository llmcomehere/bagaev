# Reindex one entry without changing manual tags

This is a complete pure record-form/1 example. Its job is small: retain an entry's
identity and human-maintained tags, and replace computed tags with a sorted,
duplicate-free new list.

```bagaev
bagaev record-form/1;
program {
  record Entry { id: Int64, manual: TextList, indexed: TextList };
  entry reindex_entry;
  fn reindex_entry(entry: Entry, tags: TextList) -> Entry =
    Entry { id: entry.id, manual: entry.manual, indexed: list.unique(tags) };
}
```

For `id=1`, `manual=["family"]`, `indexed=["old"]` and
`tags=["new","new"]`, it returns `id=1`, `manual=["family"]`,
`indexed=["new"]`. Manual tag order and duplicates are intentionally preserved.
Empty incoming tags clear only indexed tags. `list.unique` sorts; it does not
preserve first-occurrence order or perform Unicode normalization.

## Use and verification

The [data-only converter](pure-record-form.md) can decode the readable source
into a typed-record/10 program. Supply that program and explicit arguments in
a `bagaev-typed-record-invocation/10` input to a separately reviewed reference's
`run --input FILE` command. The converter itself never invokes an evaluator.
The reference has no separate `check` subcommand.

Frozen literal expectations are in
[the example packet](../examples/probes/pure-reindex-entry/cases.json).
`tests/probes/pure_reindex_entry_checks.py` accepts explicit reviewed reader and
reference paths, their SHA-256 identities, and a new output directory using the
same options as the other portable probes. It compares the exact decoded graph,
roundtrip and four full record values, and retains one explicit work-limit
refusal. Inputs and source bytes must remain unchanged.

This is not a durable update. A caller must define its own admitted transition
boundary before storing results. The owned-record-list restriction in component/2
is unchanged. Valid-sized lists can still exceed the finite sorting work budget;
the refusal case returns no partial value. No cost or performance advantage is
claimed by these correctness observations.
