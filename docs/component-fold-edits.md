# Detached changes containing counted folds

The fixed `bagaev_component_fold_edit` API accepts component-edit/6 with
component-form/6 text. It returns the existing component-draft/2 over
component-source/2. Earlier edit entry points and shared draft rules are unchanged.

In the [byte-preflight example](tag-box-budget.md), byte_count traverses a list
with a guarded literal-count fold. The candidate extracts tag_bytes(tag: Text)
from its body. The exact delta adds tag_bytes and replaces byte_count, preserving
all existing function signatures, component metadata, record and variant types.

The frame contains exactly schema, form, base, target, candidate_id and source.
Source is text, not a path or module selector. Call the fixed API's
`draft(original, frame_bytes, policy_bytes, reviewed_checker, candidate_map=...)`.
The receiver actually checks the original, decodes the candidate, verifies base
and any candidate mapping, checks unchanged interfaces/declarations and the
actual candidate, then verifies its target identity. The returned draft always
has execution_admission:false. It changes no current program head or state.

Thirteen [frozen cases](../examples/probes/component-fold/edit/CONTRACT.md)
cover the exact extraction, wrong version/pins/mapping, missing or substituting
checker, no change, changed interface/signature, candidate type failure and a
compatible but wrong calculation. The unchanged core computes 3 bytes for
`["é", "a"]`. A helper returning zero is structurally compatible and produces a
draft, but fails that business expectation. A checked draft is not qualification
or live admission.

The portable `tests/probes/component_fold_edit_checks.py` uses the established
explicit reader/reference paths, hashes and new absolute output directory.
The bounded run made 18 native calls: 16 source/policy checks and two pure
reference invocations. The older edit/4 refuses edit/6. No network, model,
external application effect, source admission or runtime change is involved.
These are finite same-maintainer conformance observations, not independent
reproduction, full acceptance or a development-cost measurement.
