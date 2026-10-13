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

## Final boundary for calls without a new outcome

The dispatcher checks the complete G/digest boundary after callbacks even when
submit, observe or cancel returns a retained result without changing the receiver.
A nested commit must not leave the outer call returning its stale-image answer.
An ABA sequence that restores identical payload bytes still conflicts because G
changed. The refusal is STORAGE_CONFLICT; the nested result is preserved and no
automatic retry occurs. With no intervening commit, the no-op CAS leaves G,
digest and bytes unchanged, including a clock-floor-only observation.

Six [dispatcher tests](../tests/probes/test_outcome_dispatch_final_cas.py) use
controlled owner/capture callbacks and actual temporary SQLite files. They cover
all three no-op commands, ABA, clock-only observation, a single real image change
and the existing mutating-call conflict. The prior dispatcher failed four
no-op conflict cases; the corrected dispatcher passed all six test methods.
These are storage-ordering checks, not new typed-evaluator or native observations,
real reboot tests or production durability evidence.

The separate [live dispatch driver](../tests/probes/outcome_persistence_dispatch_checks.py)
uses the same explicit reader/reference/hash arguments as the existing manager
checks. Each of submit, observe and cancel was also checked with actual typed
reconstruction: a nested run creation changed G from 2 to 3 while H stayed 0
and R stayed 7. The outer call refused, preserved the nested run and performed
no additional application evaluation. An explicit later retry returned the old
Declined receipt without a write. The portable driver repeated those same three
cases (129 reader/reference calls, three setup application evaluations), not
three new independent cases. The unchanged manager regression also passed its
nine-step trace and eleven refusals (303 reader/reference calls, three application
evaluations). Qualification receipts in that manager regression remain controlled
inputs. No generated native application kernel or model was invoked.

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

### Final observer callback freshness

The [final-read driver](../tests/probes/outcome_persistence_retained_final_checks.py)
crosses retained Declined, absent and conflicting-intent answers with unchanged,
changed, same-bytes ABA and changed-plus-denied final callbacks. Its separate
[literal expectations](../examples/probes/outcome-persistence/retained-view-final-read.json)
preserve the older fixture and oracle. It reconstructs the actual original
typed programme image, then performs synchronous serial SQLite changes in the
second observer callback. Changed and ABA images refuse `VIEW_STALE_IMAGE`;
final permission denial returns `AccessDenied` without disclosing the answer.
The nested generation remains 6 or 7 rather than being overwritten or retried.

Twelve cases passed in the bounded reference profile: 576 setup and 132 read
reader/reference invocations, 24 setup application evaluations, zero application
evaluations during observation and zero live-condition calls. The unchanged
retained result is detached. These repeat setup invocations are not additional
workloads. Temporary changed bytes are valid storage JSON but intentionally not
a programme image: they must be detected as stale without reconstructing them.

The driver requires explicit separately admitted `--reader`, `--reference`,
their `--reader-sha256` and `--reference-sha256` identities, and a new absolute
`--output` directory. It records actual inputs and outputs through the existing
test host. This is reference reconstruction with serial callback cuts, not a
native application kernel, production concurrency, authentication, or writable
clock-migration qualification. No runtime implementation changes are needed.

## Exact admission retry boundary

An exact retained admission retry also crosses a final G/digest CAS after typed
reconstruction callbacks. With unchanged storage, the receipt is detached and no
write, requalification or mutation-authority check occurs. A nested commit or an
ABA sequence produces STORAGE_CONFLICT and preserves the nested state. The caller
may explicitly retry later. Changed intent still raises PROGRAMME_INTENT_CONFLICT
before any receipt is returned; its error precedence is unchanged. This trusted
host retry API does not replace the separately authorized management observation
port.

Four [controlled tests](../tests/probes/test_admission_retry_final_cas.py) use
synthetic restoration callbacks and actual SQLite. The
[typed driver](../tests/probes/outcome_persistence_admission_retry_checks.py)
uses explicit reader/reference/hash arguments and checks stable replay, a nested
run creation during reconstruction, and ABA. Both nested cases returned an old
receipt on the prior dispatcher and refuse on the corrected dispatcher. Explicit
later retries return the old receipt without a write. Qualification receipts are
controlled; there are no application evaluations or generated native kernels.
These finite serial cases are not production concurrency or crash evidence.
