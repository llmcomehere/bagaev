# Carry typed source revisions into another session

The experimental `bagaev-record-revisions/1` package keeps a linear history of
readable form5 source files. It supports an inventory original and its
five-unit-limit successor in one portable file, with exact checkout of either
authored source. It preserves source bytes, decoded program hashes and chained
predecessor identities. It does not store application state or admit execution.

`tools/record_revisions.py` provides four explicit operations:

```sh
python tools/record_revisions.py init original.bagaev --output first.json \
  --source-sha256 RAW_A --program-sha256 PROGRAM_A
python tools/record_revisions.py append first.json --source candidate.bagaev \
  --output second.json --package-sha256 PACKAGE_A --head REVISION_A \
  --source-sha256 RAW_B --program-sha256 PROGRAM_B
python tools/record_revisions.py inspect second.json --output history.json
python tools/record_revisions.py checkout second.json --revision REVISION_A \
  --output restored-original.bagaev
```

Replace uppercase placeholders with independently selected lowercase SHA-256
pins. Package hashes use canonical JSON: sorted keys, UTF-8 without ASCII
escaping, compact comma/colon separators and no trailing newline. Revision IDs
hash the canonical object containing exactly parent, source_sha256 and
program_sha256. The first parent is null. The library exposes `package_digest`
for identity calculation; calculating a hash is not reviewing or approving data.
Fresh CLI package output is already canonical: its raw SHA-256 supplies
PACKAGE_A and its `head` field supplies REVISION_A.

## Ready inventory example

[inventory-history.json](../examples/probes/record-revisions/inventory-history.json)
contains the unchanged public inventory source and five-unit-limit successor.
Its raw/canonical SHA-256 is
`5733b994ab4612b572e7b42d848e3849a97ee165a826e51ca081d3b1e2946488`.
To recover the original into a new file:

```sh
python -B -S tools/record_revisions.py checkout \
  examples/probes/record-revisions/inventory-history.json \
  --revision 6ba1bfd299f66d4cdc546949bc0bedbce636c9eaadc9b0165a82807a20e80e01 \
  --output restored-original.bagaev
```

The successor revision is
`4e184efcce889451e88b1c1ab466eb853cf55bb87f90e0de5582855a84720762`.
Five additional in-process CLI calls built, inspected and checked out both
revisions. Both recovered files matched the original public files byte-for-byte;
revision IDs were independently reconstructed from the specified preimages.
These calls reuse the existing inventory behavior; they do not execute it.

## Validation boundary

Every operation validates the complete history, including later revisions when
checking out an earlier one. Append requires the expected package digest and
head, creates a detached successor and preserves its input. A return A→B→A is
allowed as new lineage; adjacent identical decoded programs, including
layout-only changes, are refused. Packages contain at most16 revisions and at
most1MiB of canonical JSON. Raw input is also limited to1MiB. Unknown fields,
profiles, duplicate keys, malformed sources, stale pins and forged history refuse.

All output paths must be new. Existing files are never replaced. An I/O failure
can leave a newly created incomplete output; no crash-atomic filesystem or
concurrent-head guarantee is made. Imported packages remain untrusted data.

Decoding establishes syntax and identity only. `semantic_check` and
`execution_admission` remain false. There is no evaluator, Rust checker,
subprocess, network, Store migration or trusted producer in this path. Later
semantic checking and execution require their own reviewed, authorized route.

Eight test methods cover the pinned existing inventory handoff, independent
scalar identities, A→B→A, stale heads/packages, tampered later history, source
and program pins, layout-only refusals,16/17-revision and escaped-size bounds,
hostile JSON/API inputs, and all four CLI-main operations with existing-output
preservation. These are bounded in-process observations, not new business
runtime evidence, independent reproduction or durability qualification.

## Interrupted output and fresh recovery

On 17 October 2026, six fresh data-only child processes exercised the existing
public inventory fixture. Init created the original revision. During append,
an instrumented stream at the exact new output path wrote and flushed17 bytes,
then that child terminated with exit73. The retained bytes matched the exact
prefix of the published two-revision package; the predecessor stayed unchanged.

A fresh inspect rejected the partial file with `REVISION_JSON`. Reusing its
occupied path for append returned `RECORD_PATH` and preserved both files.
Appending from the intact predecessor to a new path then matched the complete
published package byte-for-byte. Fresh checkout reproduced the successor source
with SHA256 `8df61c88b2150258a560e019ed4920e3aa8fb393708a9c1f720aa9ae961d7005`.
The partial file, process logs and both original source files were retained.

The first attempted run stopped before the init write because the probe audit
omitted a standard-library namedtuple construction. That failure was retained;
the corrected probe was separately reviewed before the six-process run. No
revision-library or application behavior was changed to make the test pass.

The probe is `tests/probes/revision_interruption_process_checks.py`. Run it by
absolute path with Python `-B -S` from a fresh working directory outside the
checkout, under a separately authorized bounded process profile. It creates
`revision-interruption-r2/` and refuses reuse; it checks nine pinned dependencies
and refuses their bytecode-cache directories. `-B -S` is not a sandbox.

This is controlled stream-boundary interruption in a real child followed by
fresh-process recovery, not uninstrumented OS-fault coverage, fsync/power-loss
durability, crash-atomic publication or concurrent-head safety. Capture timeout
and overflow handling were statically reviewed but not exercised by these six
calls. No application evaluator, database, model or network was invoked.

## Choose portable history or a local transactional store

Use this portable package when you need exact source exchange, detached review
or checkout in another session. Each append creates a new file; a failed output
can remain partial, and recovery starts from the intact predecessor at a new path.

For a local history whose logical append must commit as one transaction, use the
existing [candidate history store](record-history-store.md). It stores the same
bounded form5/form6 source history in SQLite and supports explicit restore,
append, inspect, recover, export and checkout. It is a candidate-source store,
not application state or execution admission. Follow that guide's explicit form,
pins and accepted rollback-journal profile; do not change SQLite settings to
force an unsupported environment through its checks.

A commit can succeed even if its acknowledgment fails. Reconcile the current
package/head before retrying. The existing store qualification distinguishes
before-commit and after-commit exits; it does not establish power-loss durability
or exercised hot-journal recovery. Export and checkout still write new portable
files and can leave partial output on failure. A transactional database commit
does not make the separate exported file atomically published.

These are two existing routes with different output boundaries. Moving a pinned
portable package into a new local store uses the store's explicit `restore`
operation; it does not require a new history schema or another storage backend.
