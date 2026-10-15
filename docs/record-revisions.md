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
