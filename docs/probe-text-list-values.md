# Bounded immutable Text list value precursor

Experimental contract `bagaev-text-list-value/1`, motivated by the public catalog's
ordered tags, canonical sets and origin-collision tests. It does not modify the
catalog's four-element/ASCII restrictions or claim language/application support.

Input is an immutable slice of already checked Text values. Each retains the
Text value contract (strict UTF-8, <=1024 bytes, <=256 scalars). This list allows
0..64 items and at most4096 aggregate UTF-8 bytes, counting duplicates. Validate
item count first: >64 gives LIST_ITEMS at index64 without inspecting elements.
Then sum byte lengths in input order; the first prefix above4096 gives
LIST_BYTES at that item's zero-based index. Construction returns no partial list.

Operations preserve the original descriptor slice and all string bytes:
- len and total_bytes report exact item count and aggregate bytes.
- get(usize) returns the borrowed Text at that index, or absent when out of range.
- contains(Text) uses exact byte equality; no normalization or C-string rules.
- is_strictly_increasing is true iff adjacent values are strictly increasing by
  Unicode scalar order (equivalent to strict UTF-8 byte order); duplicates fail.
  Empty and singleton lists are strictly increasing.
- unique_sorted returns separate fixed-capacity descriptors of unique values in
  ascending order. Equal values retain the first input occurrence's byte view.
  The result borrows text bytes but not the original descriptor array; its public
  constructors/fields are closed. It cannot change strings or original ordering.

The library allocates no heap, uses no unsafe code or external effects, and does
not rely on Rust container layout as a wire/native ABI. A fixed64-slot optional
Text array is permitted for the returned descriptor storage. Insertion sorting
is bounded by the stated capacities; no complexity/performance advantage is
claimed. Work charges, source syntax, runtime ownership and native lowering
must be defined separately before this becomes a language operation.

Freeze literal cases before implementation: empty/duplicates/ordering, NUL,
supplementary Unicode and non-normalization, first-occurrence identity, item
and aggregate bounds with refusal precedence. Exact expected values and indices
matter; roundtrip or self-comparison alone is insufficient.

## Bounded library evidence

The [safe Rust library](../examples/probes/backend/rust/text_list.rs) passed all
15 [pre-frozen literal cases](../examples/probes/text-list-value-cases.json).
The [tests](../tests/probes/backend/text_list_tests.rs) check exact original-index
selection, first-occurrence byte-view identity, unchanged owned inputs, and
continued use of the output after dropping the original descriptor array.
Rust1.93.0 compiled with warnings denied. Six concrete unit-level mutations
were detected by named test assertions: over-strict item limit, loose byte cap,
non-strict increasing check, reverse sort, retained duplicates and last-occurrence
view replacement. Failed builds/timeouts do not count. See
[observations](../examples/probes/text-list-value-observations.json).

This is same-maintainer value-library evidence. Source operations, work rules,
native representation and application acceptance still require separate work.
