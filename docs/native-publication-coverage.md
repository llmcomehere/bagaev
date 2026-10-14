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

## October 14: selected original CLI cases

A later six-case pass used the unchanged non-test `native_main.rs` linked to
the existing K-MIN LLVM kernel, with a fresh direct output directory. This
exercised actual argument parsing, input-file reading, fixed-kernel binding,
observation and file/stdout publication. It did not replace the caller with the
earlier witness-to-stdout adapter.

The [CLI observations](../examples/probes/native-publication/cli-observations.json)
record exact exit codes, stdout lengths, literal stderr bytes, preserved input
files and full output-directory comparisons. All six cases passed:

| Case | Input / destination | Expected observed boundary |
| --- | --- | --- |
| CLI-01 | Existing K-MIN, prefill00, new witness | Exit0, exact143-byte frozen result, full witness bytes |
| CLI-02 | Same K-MIN, prefillff, distinct new witness | Same result, full witness bytes with prefillff |
| CLI-03 | K-MIN, existing witness containing `keep` | Exit1, empty stdout, exact publication error, preserved file |
| CLI-04 | K-MAX input against the K-MIN-linked caller | Exit1, empty stdout, exact binding refusal, no witness |
| CLI-05 | Missing input file | Exit1, empty stdout, exact input error, no witness |
| CLI-06 | Invalid prefill argument | Exit1, empty stdout, exact usage error, no witness |

The independent [kernel oracle](../examples/probes/kernel-oracle.json) freezes
K-MIN as Int64 minimum with work1 and exact result/ABI bytes. Both successful
stored witnesses matched canonical bytes, not merely parsed JSON:
[prefill00](../examples/probes/native-publication/cli-zero.witness.json) and
[prefillff](../examples/probes/native-publication/cli-ones.witness.json).
All64 captured input bytes were unchanged and all32 ABI output bytes matched.
CLI-03 also reaches the native observation before exclusive creation refuses;
the six cases therefore entail three native calls by source path, with two
published successful observations. Counts are not externally instrumented.

The selected build used Rust1.93.0 edition2021 and generic x86-64 O2 LLVM21.
The retained K-MIN LLVM source SHA256 is
`cd674cb1a027f859662c7ddb1eb45267e526cd013fc8b40893555317b2524bdb`.
Before execution, separate source/artifact review checked the final ELF,
single entry and binding symbols, read-only regions, aligned length and the
1541-byte binding's full program correspondence. Its binding SHA256 is
`4cc5973b15357bea799c283bde271355efc03c231e7db7d6f7c58c67e25c662a`.
The caller source SHA256 remained
`3eb991d44f9cfbdb43126638e51c8c50d6eaf6e6089c449f910bd9be63e9989f`.
Compilation retained one unnecessary-unsafe warning. No caller-source,
output-guard, workflow or execution-profile change was made.

This is selected original CLI success/refusal coverage, not full CLI acceptance
or independent empirical reproduction. No disk-full, real stdout-device fault,
injected synchronization error, partial disk-write, race, crash or power-loss
claim follows. Read-only build inspection supplements source review; it does
not prove safety of arbitrary foreign objects. Retained one-shot directories
must not be reused or cleaned automatically to replay these observations.

## October 14: original CLI with a closed stdout pipe

One later bounded case used the same admitted K-MIN-linked original CLI binary
and prefill00 invocation. Before process creation, the helper created an anonymous
OS pipe and closed its only read end. The child received only the write end as
stdout; the parent closed that end after launch. Stderr was captured separately,
with a 30-second process deadline. The binary and input hashes were checked before
execution and their complete bytes remained unchanged afterward.

The [observation](../examples/probes/native-publication/closed-pipe-observation.json)
records exit1 and exact publication-error stderr. The fresh exclusive witness
matched the complete frozen canonical K-MIN bytes; the output directory contained
exactly that witness. No timeout occurred. There was no stdout reader or stdout
capture, so delivered stdout bytes are unknown, not reported as zero.

This adds one real-process closed-reader observation beyond the earlier scripted
sink cases. It does not independently identify the failed syscall/errno: complete
witness bytes could also survive an earlier flush/sync error with the same generic
diagnostic. Source inspection establishes publication ordering; this case does
not prove sync succeeded or physical durability. Disk-full, injected sync failures,
hostile races and process-crash storage behavior remain outside this observation.
No caller source, kernel, workflow, output guard or execution-profile change was
needed. Separate source review preceded the one-shot execution; it is not an
independent empirical reproduction or performance measurement.
