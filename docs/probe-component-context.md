# Explicit component context profile

Experimental inspection contract. Frozen cases precede implementation; source acceptance does not establish production conformance.

Use component-context/1 and independently supplied component-expectation/1.
Axes are semantic=bagaev-component-source/1, ir=bagaev-component-source/1,
form=component-form/1, envelope=component-context/1, evidence=probe-evidence/1.
The evidence axis identifies descriptive format only; this first API inspects
reconstruction and does not accept model/evidence exchange or execution authority.
Legacy probe-context/1 APIs continue refusing this profile.

Reuse existing context fields/bounds/reference/candidate-map mechanics through
an explicit private profile parameter defaulting to legacy behavior. Never select
the profile from packet contents in the old public API. New inspect() selects one
fixed component profile and requires a configured actual component semantic checker.

## Independently expected semantic roles and open facts

The new expectation adds programme_sources, unknowns and open_effects to the old
expectation fields. programme_sources is a sorted1–16-entry list of id/pin/role;
role is baseline or dependency, with exactly one baseline. Every programme-source
ID must also have an independently expected physical source pin. The baseline's
semantic pin equals the checked snapshot. Every designated source is decoded with
the actual readable component codec and bound to its canonical component identity.
The baseline text must equal the checked baseline data; dependencies receive actual
component checking. Old S1 is a dependency, never a candidate choice for new runs.

Expected unknowns (0–32) and open_effects (0–16) are sorted id/pin lists. Their pins
cover each complete context row (id/text/refs). These sets are exact: missing rows
refuse CTX_MISSING, extra rows CTX_REMAPPED, changed rows CTX_STALE. A context cannot
forget old A merely by retaining its source text but dropping its open-effect row.
The existing legacy expectation/API is not retroactively changed.

All ordinary source bytes and reference boundaries, five receiving obligations,
snapshot and candidate-map checks remain. Unknowns/open facts are descriptive data,
not instructions, permission grants or an autonomous reason to block unrelated work.
Inspection returns snapshot, candidate_set, unknown/effect IDs, checked programme
roles/pins, admission=false and model_calls=0. It neither discovers sources nor runs
a programme/model or restores capabilities.

## Checking and error order

Common context shape/axes and expectation shape precede actual baseline checking;
then snapshot/source/reference/obligation checks, exact unknown/effect bindings,
candidate mapping/checking and programme-source decoding/binding. Keep legacy
code/location behavior unchanged when the private profile flag is false.
New expectation role records and their independent source membership are shape
checked before semantic checking. Source semantic mismatch is CTX_STALE at its
programme_sources index/pin. Readable FormError and actual ComponentRefusal remain
distinct from ContextUnavailable for absent/substituting checker capability.
The checker cannot be selected by packet metadata; matching canonical bytes do not
authenticate an arbitrary lying host callback.

Existing bounds remain4MiB context,2MiB expectation,16 sources with131072 bytes each
and1MiB combined text,32 obligations/unknowns,16 effects/candidates,8 refs per row,
and the established depth/value/canonical-size caps. New role/expected-fact lists
fit those same bounds. All declarations are data, with no network/file discovery.

## Connected continuation

At WC17's resume point the current programme is S2 and state revisionR9, while old
A/S1 has an unobserved R8 receipt. Package current/old source, goal, five obligations,
unknown authority/production facts and exact pending continuation without permissions.
Validate against independently frozen current expectations. Then a separate bounded
bridge validates old programme/key/intent against the retained run and actual receiver
context before restoring the continuation. The observer's permission comes from the
current trusted fixture, never the context. Old receipt observation must leaveR9 and
the S1/S2 call order unchanged. Also test missing current observation permission.

This is explicit data reconstruction in a simulated receiver, not crash recovery,
durable storage, authentication, a new semantic checker registry or model operation.

## Reproduction and limits

The public inputs are [literal context cases](../examples/probes/component-context/cases.json),
with a separate [input manifest](../examples/probes/component-context/inputs.json).
The implementation is [component inspection](../src/bagaev_component_context.py),
sharing internal reconstruction code with the unchanged legacy public API.

After separately reviewing and authorizing host executables, run
`tests/probes/component_context_checks.py` with `--reader`, `--reader-sha256` and
`--output`. Paths must be absolute; output must not exist. The reader is the
existing data-only component reference. A hash identifies bytes and does not
itself authorize execution. The host must provide the documented bounded,
no-network environment; these harnesses do not create one.

`tests/probes/component_context_cycle.py` additionally takes `--reference`,
`--reference-sha256`, `--matcher` and `--matcher-sha256`, as described in the
[source component](probe-component-source.md) and [change](probe-component-change.md)
guides. It preserves the 17 frozen trace projections. Only WC17 receives the new
context reconstruction and current-permission denial branch; the other 16 are
regressions. The test-only `before_event` callback is configured by trusted host
code, defaults to absent, and cannot be selected by source/context packets.

The 17 literal context cases use actual data checking. Separately run
`tests/test_probe_context.py` to preserve the legacy 8 test methods / 23 frozen
oracle cases; those legacy tests use documented checker doubles. These are finite
conformance observations, not a completeness proof. No model invocation, timing,
allocation or token-cost experiment is part of this slice. Source inspection,
simulated admission, actual pure computation and production recovery are distinct.
