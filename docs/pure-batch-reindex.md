# Reindex a bounded batch

This pure example lifts [single-entry reindexing](pure-reindex-entry.md) to a
named list of at most four records. It preserves entry order, repeated entries,
identifiers and every manual tag sequence. Only computed tags are replaced.

```bagaev
bagaev record-form/1;
program {
  record Entry { id: Int64, manual: TextList, indexed: TextList };
  list Entries of Entry capacity 4;
  entry reindex_batch;
  fn reindex_entry(entry: Entry, tags: TextList) -> Entry =
    Entry { id: entry.id, manual: entry.manual, indexed: list.unique(tags) };
  fn reindex_batch(entries: Entries, tags: TextList) -> Entries =
    fold (4, records.list(Entries)) with (i, result) in
      if (i < records.len(entries))
      then records.push(result, reindex_entry(records.at(entries, i), tags))
      else result;
}
```

The fixed fold executes four iterations. Its length guard prevents reading past
the actual input. Starting from an empty result and appending at most once per
input entry preserves order and fits the declared capacity. Empty input returns
an empty list. No mutable state or persistent update is implied.

Use `tools/record_text.py prepare` with an arguments array containing the entry
list and new tags, then pass the generated invocation to a separately reviewed
reference. Example arguments:

```json
[[{"id":8,"manual":["z","a","z"],"indexed":["old"]}],["b","a","b"]]
```

The returned record keeps id 8 and manual `["z","a","z"]`, with indexed
`["a","b"]`. Empty new tags clear indexed lists. Unicode spellings are not
normalized. Expensive sorting can return RR_WORK with no partial result.

Six frozen cases cover empty, singleton, order/manual preservation, full
capacity, Unicode and a work refusal. The portable probe
`tests/probes/pure_batch_reindex_checks.py` compares five full values and the
refusal while preserving source/input bytes. These are finite correctness
observations, not a larger capacity, owned-state support or a cost measurement.
