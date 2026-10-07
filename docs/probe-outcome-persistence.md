# Owned outcome persistence and caller continuation

This experimental single-writer Linux/CPython/SQLite profile composes typed
receiver state and terminal receipts with a programme default, immutable run
bindings and admission-operation receipts. It does not change Store/1, L2,
component-context/2, permissions or workflow controls.

G is the complete storage image generation. H is the programme admission
generation. R is the application revision. A terminal Decline changes G but not
R or H. Applied changes G and R. Admission changes G and H, even when returning
to earlier identical source bytes. Current authority and clock-domain ticks are
independent. No counter grants rights.

The store uses one canonical bounded image row and compares G plus the complete
old digest in an immediate SQLite transaction. It checks existing DELETE journal
and full-or-stronger synchronous settings, without assigning settings. The trusted
parent directory, local filesystem, SQLite implementation and host callbacks are
explicit premises. Images are data, never executable or permission selectors.

The manager checks a fixed host inventory, exact qualification binding, source
compatibility and current authority. One final CAS follows every callback, so a
nested application Decline cannot be erased by checking only the programme head.
An exact admission retry returns its old receipt; a changed intent conflicts.
New runs pin the current H/source pair. Old runs remain pinned across admissions.
Histories and ledgers are bounded without eviction. Canonical checksums and
contiguous histories are consistency checks, not authentication of old rights.

A caller continuation has independently selected context, pending identity and
expected current H/source. It resolves against the reconstructed owner and retained
run, then rechecks G/digest after validation callbacks. It returns caller data only.
A later observation checks current rights and may return an old receipt without
new application execution. It does not activate an owner backup, renew deadlines,
grant a lease, import arbitrary history or restore privileges.

## Finite reproduction

The [fixture manifest](../examples/probes/outcome-persistence/manifest.json)
binds literal envelope, G/H/R, process-cut and continuation expectations. The
outcome_persistence_*_checks.py drivers in tests/probes accept an explicit fresh
output directory and separately reviewed reader/reference binaries with hashes.
Connected and continuation drivers additionally accept the matcher and exact
qualification directory/producer/good/bad hashes produced by the existing typed
outcome qualifier in this checkout. Hashes identify bytes; execution still needs
an independently approved bounded profile.

Envelope checks reconstruct actual typed values. Manager ordering and selected
pre/post-COMMIT cuts use controlled qualification receipts, labelled as such.
Connected and continuation tests instead consume verified actual qualification
and real matching. They retain raw inputs/outputs outside the repository and
distinguish those prior qualifications from new execution. Child process cuts are
serial self-exits at four selected dirty-COMMIT boundaries, not power-loss tests
or coverage of arbitrary crashes. No production durability, multi-host exactly-once,
historical authenticity, performance or cost advantage follows from these probes.

## Lost management responses

The existing start operation remains duplicate-refusing and never repins a run.
A separate read-only management observation port resolves a run's retained birth
H/source or an admission receipt after a lost response. An independent host
callback must grant current observation both before reading and after typed
reconstruction. Denied existing and absent IDs have the same AccessDenied result.
A final G/digest comparison detects callback-induced state changes. Returned data
is detached and grants no authority or lease. Existing trusted-host APIs and their
limitations are unchanged; this is not a complete system authorization boundary.

The additional errors and observation drivers cover four controlled pre-write or
post-commit response failures and ten read-only recovery cases. They use synthetic
owned stores and controlled admission receipts, not actual device failures. A
separate explicit retry requalifies an uncommitted admission, or retrieves the
already committed receipt without requalifying. No hidden retry is implemented.

## Retained facts and old clock bindings

A separate read-only retained-fact view can inspect terminal outcomes using
independently selected original owner bindings and fresh observation permission.
It returns no executable owner or write port, requests no live clock condition,
converts no deadline and performs no application evaluation. Ordinary writable
activation under a different clock domain remains refused. Unknown cannot initiate
a new effect, and an altered intent conflicts with the retained identity.

The retained-view driver compares old Decline/R7 and Applied/R8 under current R8,
checks the unchanged new-domain activation refusal, original clock selection,
run/source association and early/late permission denial. This does not establish
real reboot migration or recover a writable clock. Historical authenticity and
same-user storage tampering remain outside this trusted-host profile.
