# Detached changes containing variant matches

The fixed bagaev_component_match_edit API accepts explicit component-edit/4 with
component-form/4 source. It produces the existing component-draft/2 over
component-source/2. Neither the edit/3 entry point nor its form/3 contract changes.

A match-bearing helper may be refactored while retaining the component's existing
interface. In the checked example, quantity(value: StockOutcome) initially reads
the Propose payload directly. The candidate adds proposed_quantity(stock: Stock)
and changes that arm to call it. The exact delta adds proposed_quantity and
replaces quantity. No current program or application state changes.

## Receiver contract

The frame still has exactly schema, form, base, target, candidate_id and source.
Source is text, not a path or a module selector. The receiver calls
`draft(original, frame_bytes, policy_bytes, reviewed_checker, candidate_map=...)`.
The separately supplied policy and trusted checker remain mandatory.

The implementation reuses the unchanged source/2 checked-draft procedure:
actually check the original, decode the explicit candidate, verify base and any
candidate mapping, preserve component metadata/declarations/existing signatures,
check the candidate, and verify its target identity. New helper functions and
body changes remain allowed. A missing exhaustive arm reaches the actual typed
checker and is refused. All drafts retain execution_admission:false.

The positive zero-payload expectation remains quantity 0. A structurally
compatible helper returning quantity+1 still produces a valid draft, but fails
that expected result. Qualification and live admission must not be replaced
by the fact that a draft is well typed and structurally compatible.

## Evidence and reproduction

The [manifest](../examples/probes/component-match/edit/manifest.json) pins thirteen
pre-implementation cases: valid extraction, old schema/form, wrong base/target,
unresolved candidate, absent/substituting checker, no change, signature/interface
changes, incomplete match and a compatible-but-wrong business result. The bounded
run made eighteen native calls: sixteen source/policy checks and two pure
reference invocations. Prior edit/3 refused the edit/4 frame. Inputs were
preserved and the exact independently constructed draft was matched.

The portable tests/probes/component_match_edit_checks.py requires a new absolute
output directory and separately reviewed reader/reference paths and SHA-256s,
using the same argument names as the [connected authoring harness](readable-authoring.md).
The implementation changes no shared edit logic, runtime, execution controls,
external application effects or authority. These finite same-maintainer results
are not independent reproduction or a measurement of development cost.
