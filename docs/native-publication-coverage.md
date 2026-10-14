# Native caller publication coverage

Initial observations 2026-10-04; additional original-path observations 2026-10-14
are recorded below. This is a bounded coverage record, not full CLI acceptance.
The implementation is [native_main.rs](../examples/probes/backend/rust/native_main.rs);
the source harness is [native_source_tests.rs](../tests/probes/backend/native_source_tests.rs).

## Checked writer behavior

The 11-test Rust 1.93.0 source harness passed, including one new scripted-writer
method with six cases. Production caller code is unchanged. The new cases check:

- two-byte short writes complete all five result bytes before one flush;
- an initial `Interrupted` write is retried without losing or duplicating bytes;
- a broken pipe after two bytes preserves that prefix and never flushes;
- a zero-length write after two bytes returns `WriteZero` and never flushes;
- a flush failure occurs after all bytes were accepted and remains an error;
- an empty payload performs no write but still flushes once.

These use an in-memory `Write` implementation. They do not simulate filesystem
synchronization or establish that a real filesystem made data durable.

## Obligation map

| Boundary | Evidence | Remaining scope |
| --- | --- | --- |
| Exact CLI arguments and lexical output path | Existing source-harness tests | Host path stability is an external prerequisite. |
| Input is regular and bounded | Existing regular temporary-file/overrun test and special-file refusal | Concurrent replacement and hostile ancestor races are not established. |
| New witness size/path guard precedes open | Source tests and October 14 eight-case real-file matrix below | Arbitrary filesystem faults and hostile races remain unexecuted. |
| Canonical parent check | Source readback | No hostile-race guarantee; canonicalization is not ownership verification. |
| Exclusive creation, no overwrite | October 14 existing-file, directory, symlink and missing-parent refusals preserve the complete test tree | Arbitrary filesystem-error coverage remains open. |
| Full write, then flush | Scripted writer cases above | Real disk errors and OS buffering are not established by mocks. |
| Witness sync precedes stdout | October 14 successful real `write_new` return and witness-visible-before-sink-callback observations | Injected sync failure and physical durability remain unexecuted. |
| Failed witness prevents result output | Invalid-path `publish` test; early-return source structure | No real disk-full/sync-failure end-to-end observation. |
| Result write/flush failure | October 14 real witness plus scripted short-write, broken-pipe and flush-failure sink | Full CLI/process stdout, real device failures and interruption remain unexecuted. |
| Retain partial evidence, no retry/delete | Source readback | Real partial-file retention remains unexecuted. |

There is no atomic rename or directory synchronization in this publication path.
A successful `File::sync_all` is not evidence of directory-entry durability after
a power loss. The probe does not claim crash-atomic publication or hostile-host
isolation. Parent-path immutability and admitted output ownership must be supplied
by the execution profile, not inferred from the diagnostic message.

The linked observation-core results in [native-probe-results.md](native-probe-results.md)
exercise an earlier boundary. They do not close any unexecuted publication item
in this table. No frozen oracle, native semantics, output guard or workflow was changed.

## October 14: original-path API observations

Two separately source-reviewed harness methods ran once with Rust 1.93.0 under
the same bounded no-network profile. The [frozen matrix plan](../examples/probes/native-publication/frozen-matrix-plan.json)
retains its historical NOT_RUN label; the distinct [observation record](../examples/probes/native-publication/observations.json)
records subsequent execution. Expectations were not rewritten after running.

The [matrix harness](../tests/probes/backend/native_publication_matrix.rs) exercised
eight cases at its literal `/out/bagaev-publication-matrix-r1` root: new bytes,
existing file, directory, symlink, oversize payload, empty payload, missing parent
and aliased parent. All eight API outcomes and complete before/after tree
comparisons matched, including file bytes and symlink targets. Two cases
successfully returned from `write_new`; no directory-entry durability is inferred.

The [ordering harness](../tests/probes/backend/native_publish_order.rs) exercised
four cases at `/out/bagaev-publish-order-r1`: successful two-byte result writes,
broken pipe after two bytes, failure flushing a complete result, and an existing
witness. Every sink callback checked the full witness was already visible.
The existing-witness case preserved its bytes and made zero sink calls.
The observation came from static frame refusal; no foreign kernel was dispatched.

These are 12 cases in two passing test methods, not 12 independent test methods.
The repository copies normalize only module import paths; recorded execution
used the original prepared harnesses identified by hashes in the observation
record. Their test bodies are unchanged. Import-path normalization is not a
second runtime observation or independent reproduction.

A reproduction needs a reviewed bounded execution profile and explicit authority
for a direct non-symlink `/out` directory. The two named roots must be absent:
the harnesses create them exclusively and intentionally retain all outputs.
Do not automatically retry, clean up, substitute a root or alter the production
guard. Build each harness with `rustc --edition=2021 --test`; select only its named method with
`--exact ... --nocapture`. Listing tests does not execute these cases.

This closes selected real-filesystem API and witness/sink-order observations.
It does not close full CLI acceptance, partial disk-write retention, disk-full,
injected synchronization failure, hostile races or crash/power-loss durability.
