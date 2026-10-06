# Checked drafts from readable component changes

The [readable component form](probe-component-form.md) now connects authoring a
change to the existing [source-bound admission path](probe-component-change.md).
A candidate text becomes a detached checked draft relative to an exact original.
Draft creation does not change a live source default, state, ledger or old run.
It is not an admission receipt or a global compare-and-swap transaction.

## One supported structural change

The example extracts S1's inline normalizer into S2's pure helper. Its structural
delta is `add: [normalize]`, `replace: [main]`. This first edit profile allows only
function addition and replacement. Existing parameter vectors and result types
must remain identical. Component bindings, record layouts, entry, lists/variants
and replacement footprint are unchanged. Removal, signature changes and other
structural changes explicitly refuse rather than acquiring accidental support.

The old L2 edit receiver and its contracts remain unchanged. Typed components
are not silently routed through an L2 semantic checker.

## Ordered receiver

`bagaev_component_edit.draft(original, edit_frame, policy, checker,
candidate_map=None)` uses the independent receiving policy and configured checker:

1. Decode and actually check the original against policy.
2. Validate the entire bounded edit frame.
3. Decode candidate text with the pure readable codec.
4. Require expected base to match the actual canonical original.
5. If an ID is selected, require its exact independent kind/content binding.
6. Preserve non-function structure and existing signatures; derive a nonempty
   add/replace-only delta.
7. Actually check the candidate source/policy.
8. Require the claimed target to equal the canonical checked candidate.
9. Return detached `component-draft/1` data, status draft, exact base/target,
   component, delta and `execution_admission:false`.

The candidate map is caller-supplied and immutable during the call. A selected
entry has exactly `kind: component-source` and `pin: canonical component hash`.
The frame cannot define its own map, callback, receiving policy or authority.
An unselected proposal may still create a draft; that is not independent acceptance.

The module performs no programme evaluation, process launch or file operation.
Semantic checking is an explicit trusted host dependency. The supplied checker
receives canonical component bytes and independent policy bytes and returns the
actual component-reader wire. Its source/core/policy identities and false admission
are checked. The integrated harness uses the reviewed data-only Rust reader.
Missing/failing/substituting checking capability raises CheckerUnavailable; it
does not become a semantic pass or refusal. An arbitrary lying callback is not
authenticated merely because it can return matching hashes.

## Frame and failure scope

The exact frame fields are schema, form, base, target, candidate_id and source.
Versions are component-edit/1 and component-form/1. Pins are64 lowercase hex
characters. Candidate ID is null or a bounded ASCII identifier. Source is scalar
UTF-8 text within the existing1MiB readable-form limit.

The JSON frame is bounded by2MiB, depth8 and32 values, with no BOM or duplicate
keys. Nonfinite and floating numeric tokens refuse at syntax validation. Integer
tokens retain only their kind for shape refusal because no admitted frame scalar
position accepts an integer. No unbounded integer conversion is required.

EditError codes distinguish EDIT_SYNTAX, EDIT_BOUNDS, EDIT_SHAPE, EDIT_VERSION,
EDIT_BASE, EDIT_CANDIDATE, EDIT_SCOPE, EDIT_SIGNATURE, EDIT_NO_CHANGE and
EDIT_TARGET. Codec FormError codes remain intact. ComponentRefused retains the
base/candidate stage and actual reader reason. CheckerUnavailable remains an
environment/dependency failure. No partial draft or implicit repair is returned.

## Complete-path evidence

Eighteen pre-implementation literal cases cover successful extraction and exact
selection, stale/wrong pins, missing/wrong selection, no-op, scope/signature/removal
refusals, invalid source, frame failures and missing/substituting/failing checker.
Nine additional witnesses exercise the previously specified frame boundaries.
Mutating a returned draft does not mutate source text or candidate-map data.

Six explicit owned receiver mutations were tested on valid baseline witnesses:
missing base, wrong candidate kind, expanded record scope, changed signature,
ignored target and ignored checker binding. Each yielded a normal wrong draft
and was detected; even these faulty drafts did not grant execution admission.

The actual independently selected S2 draft then supplies the candidate in all
seventeen existing world/receipt scenarios. The separate five-obligation/current
authority/live-head boundary still decides simulated admission. Old A/S1/R8
survives new B/S2/R9 and replay. Prior qualification is reused as prior evidence;
new draft checks and application calls are recorded separately. No production
durability, authentication, real concurrency or performance claim follows.

## Reproduction

Use the existing reviewed component reader, generic /10 reference and /8 matcher
under a separately approved bounded profile, with independently retained hashes:

```
python tests/probes/component_edit_checks.py --reader /absolute/component-reader --reader-sha256 RETAINED_READER_SHA --output /absolute/new-edit-checks
python tests/probes/component_edit_frame_guards.py --output /absolute/new-frame-guards
python tests/probes/component_edit_cycle.py --reader /absolute/component-reader --reader-sha256 RETAINED_READER_SHA --matcher /absolute/matcher --matcher-sha256 RETAINED_MATCHER_SHA --reference /absolute/record-reference --reference-sha256 RETAINED_REFERENCE_SHA --output /absolute/new-edit-cycle
```

Output parents exist; outputs must be new. Input manifests are checked. No
workflows, credentials, permissions, model calls or new runtime profiles are
introduced. Static CI and same-maintainer review concern source integration,
not independent runtime reproduction or full-language acceptance.
