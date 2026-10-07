# Detached changes in arithmetic notation

The explicit component-edit/3 frame carries component-form/3 source. It produces
the existing component-draft/2 because the decoded semantic source is still
component-source/2. This adds a representation route, not a new admission rule.

Use the fixed bagaev_component_arithmetic_edit library with a separately reviewed
component-source/2 checker and an independently selected receiving policy.
The existing edit/2 entry point continues to require form/2 and refuses a /3 frame.
No codec is selected from an arbitrary name in input, and no module-global codec
is temporarily rebound.

## What is checked

The frame contains exactly schema, form, base, target, candidate_id and source.
Source is the actual readable text, not a path to load. Base and target are
canonical component SHA-256 identities. A non-null candidate_id must resolve
through the separately supplied candidate map to the same target source.

The draft procedure retains the original sequence:
1. Decode the original and actually check it against the receiving policy.
2. Parse the explicit frame and decode its candidate.
3. Check the exact base and candidate selection.
4. Preserve component metadata, record/variant declarations, existing function
   names and their signatures. Function bodies may change and helpers may be added.
5. Actually check the candidate source and policy, then verify its target pin.
6. Return a detached draft with execution_admission:false.

The shared frame/compatibility implementation retains the edit/2 defaults and
refusal codes. Producing a draft does not register a source, change a program head
or grant execution rights. Host/checker failures remain distinct from source refusals.

## A small helper extraction

The [new source](../examples/probes/component-arithmetic/edit/S2.bagaev) extracts
the adjustment addition into an adjusted(current, delta) helper. It retains the
same application interface and zero-quantity behavior. The exact draft delta
adds adjusted and replaces apply; all other declarations remain unchanged.

A second candidate changes the negative-value test to reject zero. It is also
structurally compatible, but fails the independently fixed zero-result
expectation. Compatibility alone therefore does not establish business refinement.
The existing qualification and admission stages still decide whether a checked
candidate may become the current program.

## Reproduction and limits

The [fixture manifest](../examples/probes/component-arithmetic/edit/manifest.json)
binds 16 pre-implementation cases. The component_arithmetic_edit_checks.py driver
accepts a fresh output directory and separately reviewed reader/reference paths
and hashes, just like the existing outcome drivers. Its 21 native calls include
the two pure zero-case observations. It checks version, base, target, candidate
mapping, interface/signature/removal, bad typing, checker failures and the
compatible-but-wrong business candidate. The old frame's refusal is also checked.

The unchanged 17-case edit/2 suite passed after the shared-helper refactor.
Fresh qualification and the connected old-outcome/new-state path were rerun
against the reconciled source. Their new producer identity is retained with their
outputs; old evidence was not relabelled. These are finite same-maintainer
checks, not independent reproduction or new permission, durability or cost claims.
