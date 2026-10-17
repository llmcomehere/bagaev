# Replace one catalogue entry's manual tags

The separate `catalog-manual-tags/1` application accepts exactly interface,
state, entry_id and tags. It complements automatic reindexing and date edits
without changing their contracts or frozen expectations.

For the selected entry, replace manual_tags with sorted unique replacement
members. An empty array clears manual tags. Reject any replacement tag already
present in that entry's indexed origin. Preserve selected indexed tags exactly,
including duplicates/order, and preserve every other field and entry exactly.
There is no catalogue-wide normalization. Return a detached state and an ID view
ordered by date then ID, missing dates last. Repeating a successful replacement
is idempotent; callers retain old snapshots if they need undo.

The bounded state has at most sixteen ID-ordered unique entries, each with the
existing catalogue ID/title/date/tag constraints. Replacement tags contain at
most four valid identifiers before deduplication. Day zero is present, not
missing; Boolean, float and null dates refuse. Validation order is shape/grammar,
dates, duplicate IDs, entry order, stored origin collisions, missing target,
then incoming collision with selected indexed tags. Failure returns only a
refusal, without partial state.

The behavior lives in [readable form5](../examples/probes/catalog-manual-tags/Catalog.bagaev),
using existing profile11 operations. The [ordinary comparison reference](../src/catalog_manual_tags_reference.py)
is separate. [Frozen cases](../examples/probes/catalog-manual-tags/cases.json)
contain independently fixed expected outputs, reused literal fixtures and a
mechanically assembled sixteen-entry boundary state; neither implementation
computed those expectations.

After separate review, two ordinary test methods passed all 37 frozen cases and
two actual predecessor chains, with exact scalar-type comparison, unchanged input
and detached output containers. The existing reviewed typed reference then
matched all 37 full outputs plus two calls fed actual predecessor states: 39
typed-reference calls and 39 ordinary comparisons. Chain repetitions are not new
semantic cases. Selected indexed duplicates, non-target presentation, clearing,
re-adding, known-zero/missing order, day 31, gate priority and 16/17-entry bounds
were exercised. Source, oracle, binary and input frames remained unchanged.

This is pure synthetic application behavior. There is no external catalogue
mutation, persistence, transaction, migration, new opcode, performance comparison
or model-benefit claim. Runtime evidence is distinct from documentation CI.
