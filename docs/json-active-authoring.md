# Reproduce an ActiveJson authored change without execution

The [synthetic fragment](../examples/probes/json-active-authoring/Main.fragment.bagaev)
wraps the unchanged main expression B as `if true then B else B`, with named
helper calls and an internal comment. This exercises authoring, not a new
business policy or a model-produced change. Original ActiveJson and its business
cases remain unchanged; its three helper functions are retained exactly.

The [data-only test](../tests/probes/test_json_active_authoring.py) runs the
actual contextual replacement CLI and authored export CLI using the fixed
[pins](../examples/probes/json-active-authoring/pins.json). It checks the earlier
successor byte hash, exact expression splice, all four named calls, outside-body
bytes, comment and unchanged helpers. It also checks existing-output refusal,
stale base/source refusal, unchanged inputs and false execution admission.

Run `python tests/probes/test_json_active_authoring.py` within an independently
reviewed bounded profile. The five CLI calls produce and inspect inert data;
they do not launch an evaluator, compiler, kernel or model. Source/graph pins
are fixed authoring identities, not independent expected business results.
No runtime equivalence, performance or cost observation is added by this test.
