# Native caller publication coverage

Observed 2026-10-04. This is a bounded coverage record, not full CLI acceptance.
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
| New witness size/path guard precedes open | Source readback; invalid relative destination test | Real `/out` oversized/existing/symlink/error matrix is unexecuted. |
| Canonical parent check | Source readback | No hostile-race guarantee; canonicalization is not ownership verification. |
| Exclusive creation, no overwrite | `create_new(true)` in source | Actual existing-file and filesystem-error cases remain unexecuted. |
| Full write, then flush | Scripted writer cases above | Real disk errors and OS buffering are not established by mocks. |
| Witness sync precedes stdout | `write_new` calls `sync_all`, then `publish` writes stdout | Successful real sync and injected sync failure are unexecuted. |
| Failed witness prevents result output | Invalid-path `publish` test; early-return source structure | No real disk-full/sync-failure end-to-end observation. |
| Result write/flush failure | Shared `write_complete` scripted tests | Successful-witness plus failing stdout end-to-end path remains unexecuted. |
| Retain partial evidence, no retry/delete | Source readback | Real partial-file retention remains unexecuted. |

There is no atomic rename or directory synchronization in this publication path.
A successful `File::sync_all` is not evidence of directory-entry durability after
a power loss. The probe does not claim crash-atomic publication or hostile-host
isolation. Parent-path immutability and admitted output ownership must be supplied
by the execution profile, not inferred from the diagnostic message.

The linked observation-core results in [native-probe-results.md](native-probe-results.md)
exercise an earlier boundary. They do not close any unexecuted publication item
in this table. No frozen oracle, native semantics, output guard or workflow was changed.
