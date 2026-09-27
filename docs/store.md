# Local revisions and continuation

`bagaev-store/1` is a bounded, single-host Linux/CPython store for the pure
[L2 language](l2.md). It implements the M4 slice of the [roadmap](roadmap.md).
Its source and authored tests are **NOT_RUN** pending independent acceptance.
It changes neither the language nor the frozen catalog/P0 expectations. Review
the [execution rules](../AGENTS.md) before running candidate code.

## Ownership, transactions and limits

The receiver explicitly selects one immutable policy at creation. The store
directory is private, owner-controlled local storage: mode 0700, regular owned
database file mode 0600, no hard links or final-component symlinks. Parent
directories and filesystem implementation are trusted. Hostile same-user
filesystem writers, network filesystems, distributed operation, arbitrary SQL
database import and external exactly-once effects are unsupported. This is an
application protocol, not access control against an owner who can edit SQLite.
Hashes identify bytes; they do not authenticate a source or grant rights.

SQLite owns concurrent writer serialization and rollback-journal recovery.
Each writer uses `BEGIN IMMEDIATE`, validates a captured state, and commits one
new state document containing all objects, head, admissions and operation
receipts. Readers use a consistent read transaction. The database contains one
fixed-schema row, not user-supplied SQL. `journal_mode=DELETE`,
`synchronous=EXTRA`, `trusted_schema=OFF` and `temp_store=MEMORY` are selected
and read back. Page size is 4096; page count is capped at 16384. Every access
checks schema, `quick_check`, canonical bytes and semantic references. A lock
conflict after the one-second busy timeout refuses with `STORE_BUSY`; no hidden
retry occurs. There is no worker process or connection pool; the caller closes
its `Store` context. Opening a store can recover a hot journal and therefore
can write even for `inspect` and `export`.

The complete portable package is at most 16,777,216 bytes, 128 JSON value levels,
and 1,000,000 value occurrences. It allows at most 512 objects, 128 active
admissions and eight historical ledgers (each at most 128 admissions). A contract
has 1–32 cases, each at most 1,048,576 canonical bytes. JSON integers have at most
256 bits; floats must be finite; strings must encode as UTF-8. This transport is
intentionally narrower than L2's borrowed callable input domain. Canonical JSON
uses sorted keys, no insignificant whitespace, literal UTF-8, finite JSON
numbers and distinct scalar representations; duplicate keys, BOM, malformed
text, unsupported fields and unresolved references refuse. Package import
requires exact canonical bytes. Other document inputs may have whitespace.
Bounds cause refusal, never pruning or silent omission. No migration or garbage
collection exists in version 1; unsupported schemas are refused intact.

SQLite's [transaction contract](https://www.sqlite.org/lang_transaction.html),
[EXTRA synchronization](https://www.sqlite.org/pragma.html#pragma_synchronous)
and [atomic-commit assumptions](https://www.sqlite.org/atomiccommit.html) define
the storage mechanism. Initialization and backup additionally fsync their
directory and parent as applicable. This design is not measured power-loss or
hardware durability evidence; it depends on the OS and device honoring sync.

## Immutable objects and receiver policy

Object IDs are `sha256:` plus SHA-256 of canonical **value** bytes. A source ID
therefore equals its L2 snapshot digest. The object record is `{kind,value}`.
All fields below are required; unknown fields refuse. Lists retain their order.

| Kind | Value and validation |
| --- | --- |
| `source` | Complete checked `bagaev-l2/1` program, including pins. |
| `contract` | `{schema:"bagaev-store-contract/1",cases:[{id,input,expected}],assumptions:[text]}`. Case IDs are distinct; expected is exactly `{value:JSON}` or `{error:"L2_TYPE"\|"L2_FIELD"\|"L2_BOUNDS"}`. |
| `change` | Actual `bagaev-l2-patch/1` value. Both source snapshots must exist; applying it must produce the pinned target. |
| `evidence` | `{schema:"bagaev-store-evidence/1",source,contract,case,input,checker,assumptions,result}`. `input` is the digest of the case input; source and contract resolve. |
| `continuation` | The complete task/change package below. |

Policy is `{schema:"bagaev-store-policy/1",contract:CONTRACT_VALUE}`. Its contract
is inserted automatically. Contract objects can retain other revisions, but
cannot replace the receiver's selected policy. An obligation is one case from
that contract; every case is mandatory. IDs for tasks, cases, effects and
operations use `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Text fields have 1–4096 UTF-8
bytes; text/reference lists are bounded as in source (at most 128, or 32 source
references per hypothesis). No text is interpreted as a shell command, URL,
permission or executable code.

`check(source)` checks the actual pinned L2 program and evaluates each case.
Each evidence record has `checker:{version:"bagaev-store-checker/1",implementation}`,
where implementation hashes the exact store and reference-checker source bytes.
It binds source, contract, case, exact input digest, assumptions, and
`result:{status:"passed"|"failed"|"unknown",actual:{value:JSON}|{error:CODE}}`.
`check` produces passed/failed; imported assertions may be unknown. Only expected
language failures count as outcomes; a host failure aborts the transaction.
A declared passed record must match the pinned expectation even when retained
as historical data. The checker still evaluates a candidate on admission:
caller-supplied passed flags, foreign checker versions or stale evidence cannot
replace the receiver's observations.

## Admission and recovery

A continuation has this exact shape:

```json
{"schema":"bagaev-store-continuation/1","task":"example","intent":"Adopt the checked target","base":{"generation":0,"source":null},"target":"sha256:...","changes":[],"contract":"sha256:...","required":["case-id"],"evidence":["sha256:..."],"unresolved":[],"effects":[],"hypotheses":[]}
```

`required` is the sorted complete list of contract case IDs. For a nonempty
base, `changes` references a sequential L2 patch chain from base to target;
empty changes permit only the same source. Initial admission has a null base
and no changes. `evidence` contains exactly one applicable passed record per
obligation when admitted. Each effect is `{id,status,detail}`, with status
`unknown`, `succeeded` or `failed`; these are declared context, not verified
remote-effect receipts. Hypotheses are `{text,sources:[OBJECT_ID,...]}` and remain
separate from evidence. References resolve on put/import. Hypotheses and task
intent are not verified by the case checker. Any unresolved item, unknown or
failed effect prevents admission. The store neither performs nor retries remote
effects; the receiver must reconcile them separately and propose a new package.

`admit(operation_id, continuation_id)` is an explicit receiver action under its
external execution authorization and local policy. It compares both base source
and monotonically increasing generation with the active head, repeats all
required checks and compares the resulting evidence identities, then atomically
appends the admission and advances head. Returning to an earlier source still
advances generation, preventing ABA. Candidate puts/checks never move head.
Admission alone grants no OS, model, network or deployment authority.

The stable operation ID binds the exact continuation digest through
`request=digest({continuation:ID})`. Its receipt is
`{operation,request,continuation,head:{generation,source}}`. Same-operation,
same-request retry returns the original receipt even if head has since advanced;
conflicting request reuse refuses. Operation records are never evicted. If the
caller loses the response, a fresh process calls `inspect(operation_id)`:
`{operation,status:"committed"|"absent",receipt,head}`. A committed receipt is
authoritative for that local transaction. Absent means no committed local
admission, not proof that an unrelated remote action never occurred. After a
precommit interruption SQLite rolls back the transaction; after commit but
before observation the receipt and head survive together. No interruption
injector or process-kill hook is exposed by the product.

## Export, import and backup restore

`export()` captures `{schema:"bagaev-store-package/1",snapshot,state}` as exact
canonical bytes. `snapshot` hashes the entire state (objects, policy, active and
historical ledgers), not just the head program. State has exactly `schema`,
`policy`, `objects`, `head`, `admissions`, `operations`, `historical`.
`historical` contains `{origin,ledger}`; each ledger contains policy, head,
admissions and operations. Complete reference, hash, patch-chain and receipt
consistency is validated, including historical assertions, before any new
destination is created. Existing destinations are never replaced.

`import_package(new_directory, bytes, receiver_policy)` preserves objects and
historical ledgers, adds the exported active ledger as history, and creates an
empty active head/operation ledger under the receiver's policy. Imported
admissions cannot activate themselves. The receiver creates a new continuation
with its current base and freshly checked evidence to admit an imported source.

`restore(new_directory, bytes, receiver_policy, expected_snapshot)` is different:
the operator explicitly selects a backup using its independently retained full
snapshot digest, supplies an exactly matching policy, and requests preservation
of head and receipts. Every active admission is rechecked locally before any
destination creation. The expected digest must come from the operator's prior
record, not be trusted merely because the package advertises it. An altered
checker implementation requires fresh import and new admission; version 1 does
not silently migrate old evidence. Restore recreates the exact accepted state
identity and makes old operation outcomes available for reconciliation. It does
not undo or replay external effects. Invalid packages leave no destination;
ordinary creation failures clean up this invocation's directory. A process
crash during initial directory creation can leave an incomplete directory;
opening it fails closed. Preserve and inspect it before manual cleanup/retry.

`backup(new_file, export_bytes)` verifies the package and writes/fsyncs an
exclusive new file. CLI export calls this helper; arbitrary SQLite files are
never accepted as import/restore input. Backup is portable JSON rather than a
copy of a live database/journal pair.

## CLI and library walkthrough

The existing [toolchain envelope](toolchain.md#commands-and-observations) and
exit codes apply. Store commands emit `command:"store"`. Store errors use
`STORE_FORMAT`, `STORE_BOUND`, `STORE_POLICY`, `STORE_STALE`, `STORE_CHECK`,
`STORE_OPERATION`, `STORE_PATH`, `STORE_CORRUPT`, `STORE_BUSY`; language checking
retains `L2_*`. No paths or payloads appear in error messages. Host failures exit
1, and commit outcome must be reconciled before retry. Help/version remain text.

```text
python3 -B -m src.bagaev store init NEW_DIRECTORY --policy POLICY_JSON
python3 -B -m src.bagaev store put DIRECTORY KIND DOCUMENT_JSON
python3 -B -m src.bagaev store check DIRECTORY SOURCE_ID
python3 -B -m src.bagaev store admit DIRECTORY OPERATION_ID CONTINUATION_ID
python3 -B -m src.bagaev store inspect DIRECTORY [--operation ID | --object ID]
python3 -B -m src.bagaev store export DIRECTORY --output NEW_BACKUP
python3 -B -m src.bagaev store import NEW_DIRECTORY --package BACKUP --policy POLICY_JSON
python3 -B -m src.bagaev store restore NEW_DIRECTORY --package BACKUP --policy POLICY_JSON --snapshot EXPECTED_SNAPSHOT
```

All input files use the toolchain's bounded regular-file/no-follow reader.
`init`, `put`, `inspect`, `export` and `import` do structural checking, not L2
evaluation. `check`, new `admit` and `restore` evaluate bounded pure L2 programs
and require the caller's appropriate execution profile. The six original
toolchain commands retain their existing effects. The store never executes
Python from payloads, starts subprocesses, contacts providers or runs commands.

This complete library example prepares policy and continuation files usable by
the CLI, advances catalog A0 to A1, demonstrates idempotent receipt recovery,
and restores an explicitly selected backup. Run only in an authorized profile
from a checkout, with the two new directories and output files initially absent.
The example selects one independently specified empty-catalog case; this is a
small demonstration contract, not full catalog acceptance. `Path.write_bytes`
below is only example setup; production backup uses exclusive creation.

```python
from pathlib import Path
from src import bagaev_l2 as L2, bagaev_store as S

policy = {"schema": S.POLICY, "contract": {
    "schema": S.CONTRACT, "assumptions": ["Pure L2; empty catalog example only"],
    "cases": [{"id": "empty", "input": {
        "interface": "catalog-application/2", "behavior_revision": 0,
        "state": {"entries": []}, "reindex": None}, "expected": {"value": {
        "kind": "success", "state": {"entries": []}, "entry_ids": []}}}]}}
Path("policy.json").write_bytes(S.canonical(policy))
S.create("local-store", policy)
a0 = L2.check_program(Path("examples/l2/catalog.json").read_bytes())
patch = S.decode(Path("examples/l2/catalog-01.patch").read_bytes())
a1 = L2.apply_patch(a0, patch)
with S.Store("local-store") as store:
    source0 = store.put("source", L2.program_value(a0))
    source1 = store.put("source", L2.program_value(a1))
    change = store.put("change", patch)
    for index, source in enumerate((source0, source1)):
        package = {"schema": S.CONTINUATION, "task": "catalog-change",
            "intent": "Retain empty catalog behavior", "base": store.inspect()["head"],
            "target": source, "changes": [] if index == 0 else [change],
            "contract": S.digest(policy["contract"]), "required": ["empty"],
            "evidence": store.check(source), "unresolved": [], "effects": [],
            "hypotheses": [{"text": "Other catalog cases need separate checks",
                            "sources": [source]}]}
        Path(f"continue-{index}.json").write_bytes(S.canonical(package))
        continuation = store.put("continuation", package)
        receipt = store.admit(f"catalog-{index}", continuation)
        assert store.admit(f"catalog-{index}", continuation) == receipt
    exported = store.export()
    expected_snapshot = store.inspect()["snapshot"]
    S.backup("catalog.backup.json", exported)
# Retain expected_snapshot outside the backup as the operator's selection.
with S.Store("local-store") as reopened:
    assert reopened.inspect("catalog-1")["receipt"] == receipt
S.restore("restored-store", exported, policy, expected_snapshot)
with S.Store("restored-store") as restored:
    assert restored.inspect()["snapshot"] == expected_snapshot
    assert restored.inspect("catalog-1")["receipt"] == receipt
```

For an equivalent CLI sequence, initialize from `policy.json`, put both source
documents and the patch in that order, take their IDs from each `result.object`,
call `store check` and take `result.evidence`, then fill the continuation shape
above using `store inspect`'s `result.head` and `result.contract`. Put it and use
its returned ID with `store admit`. Export returns `result.snapshot`; retain it
separately and pass that exact value to restore. `store inspect --operation
catalog-1` provides fresh-process reconciliation without repeating evaluation.
