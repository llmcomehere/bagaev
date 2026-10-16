# Bounded local candidate history storage

`python3 -B -S tools/record_history_store.py` persists the existing portable form5 or form6 history in a
single local SQLite transaction. The form is always explicit. The store retains
source candidates, source/program identities and lineage. It neither evaluates
source nor grants execution/admission rights.

- init: create a new store from explicitly pinned source/program bytes
- append: compare the current canonical package pin and head, then append one source
- inspect: write identity metadata to a new file outside the store
- export: write canonical portable history to a new file
- checkout: write one explicitly selected revision's exact source bytes
- restore: validate a pinned portable history and create a new store
- recover: allow SQLite rollback recovery and report the readable validated state

A mutating operation prints compact metadata after commit. If that acknowledgment
cannot be sent, the append may already have happened. An uncertain commit or
acknowledgment must be reconciled by inspecting the old/new identities; do not
blindly retry. A recovery or append can alter physical journal/database bytes
before a later form or pin refusal, while preserving the prior logical history.
Read-only commands open read-only and never silently switch to a writable mode.

Only the bounded rollback-journal profile is accepted. Database headers, directory
members, owner/type/link counts and possible super-journal footers are checked
before SQLite opens. WAL and unsupported defaults refuse. Existing permissions
and SQLite settings are not changed. Logical restore accepts portable JSON, not
arbitrary database/journal imports. A failed initialization may leave incomplete
files; they are retained and cannot be overwritten by a retry.

The history limit is one MiB and sixteen revisions. Database admission is four
MiB; journal admission is eight MiB. The exact schema and canonical payload are
validated, and database page count is checked before commit. Parent-directory
races, hostile filesystem replacement and general damaged-database repair are
outside this bounded scope.

On 16 October 2026, a clean standalone source copy passed 31 frozen refusal controls,
five review controls and an inclusive input boundary. Twenty-two normal CLI calls,
two actual closed-pipe calls and four sequentially terminated child processes
passed across both forms. The before-commit exits retained the old logical state;
after-commit exits retained the new state. Closed acknowledgments returned exit 1
and explicitly uncertain outcomes. SQLite 3.53.1 was observed with delete journaling,
synchronous=2, normal locking and 4096-byte pages; no settings were assigned.

No tested interruption required hot-journal recovery. That behavior remains
unqualified beyond the controlled recovery-required error seam. No power-loss,
public-release, independent-machine or universal durability claim follows.

## Standalone commands

Use a new destination directory for init/restore and new output files. Replace
uppercase placeholders with explicit source paths and hashes. Source/program pins
are raw-source and canonical decoded-program identities; package pins are over
canonical portable history. A pin does not grant execution or data-access rights.

```text
python3 -B -S tools/record_history_store.py init NEW_STORE --form 5 --source SOURCE --source-sha256 SOURCE_SHA256 --program-sha256 PROGRAM_SHA256
python3 -B -S tools/record_history_store.py inspect STORE --form 5 --output NEW_REPORT
python3 -B -S tools/record_history_store.py append STORE --form 5 --package-sha256 PACKAGE_SHA256 --head HEAD_ID --source NEW_SOURCE --source-sha256 NEW_SOURCE_SHA256 --program-sha256 NEW_PROGRAM_SHA256
python3 -B -S tools/record_history_store.py export STORE --form 5 --output NEW_HISTORY
python3 -B -S tools/record_history_store.py checkout STORE --form 5 --revision REVISION_ID --output NEW_SOURCE
python3 -B -S tools/record_history_store.py restore NEW_STORE --form 5 --input HISTORY --package-sha256 PACKAGE_SHA256
python3 -B -S tools/record_history_store.py recover STORE --form 5
```

Use explicit form6 for form6 source/history. Run the two bounded qualification
scripts with separate new output directories outside the source/repository tree,
under an independently approved local execution profile. The process script owns
and awaits its test children serially. Its source-preservation check requires a
clean tree without bytecode or symlinks; do not place test outputs in that tree.
Its child guard is relative to that explicit fresh output root, so a copied source
tree does not need a project-specific workspace location.

```text
python3 -B -S tests/probes/history_store_unit_checks.py --output NEW_UNIT_DIRECTORY
python3 -B -S tests/probes/history_store_process_checks.py --output NEW_PROCESS_DIRECTORY
```

The clean copy contained seven new files and fourteen imported dependencies
byte-matching the public form6-revision base. The same 31 + 5 controls and 28 child
processes passed from fresh output paths, without a cohesive dispatcher or an
unpublished source-check helper. This was the same local environment, not an
independent machine. No database/journal import or automatic settings adjustment
is offered.
