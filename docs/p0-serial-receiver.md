# Frozen P0 serial receiver subset

This supporting model asks whether historical receipts remain distinct from
current receiver authority and current knowledge of an effect. It implements a
bounded subset of [p0-contract/1.0.0](p0.md) using unchanged [frozen observations](p0-cases.json).
It is not a new language feature or a prerequisite for model experiments.

The [receiver](../src/p0_receiver.py) models ordered write, transfer and receipt
query checks over trusted synthetic initial state and session/grant fixtures.
Current authentication, assignee, grants, task versions and epoch precede write
receipt lookup. An exact admitted retry retrieves the immutable receipt without
applying the effect again. Reading an old transfer receipt does not restore its
old authority value. Returned observations and snapshots are detached values.

The [scenario layer](../src/p0_scenario.py) models lost and delayed responses,
timeout knowledge, unsupported cancellation, and explicit before/after-commit
cuts followed by reconstruction of the selected committed state. A missing
receipt at a query does not settle an earlier unknown outcome. These are serial
in-memory transitions. No real process is killed, no disk fault is injected,
and no external authentication, durable transaction or network is supplied.

## Fixed selection and checking

The [selection](../examples/probes/p0-serial-subset.json) pins the original
specification/oracle hashes and lists 22 receiver cases, 11 additional scenarios
and all 52 excluded cases. The [test](../tests/test_p0_receiver.py) projects only
fields actually produced by each model step onto the frozen expected keys.
It preserves scalar types and array order; missing observations cannot be filled
from expectations. The selected traces contain 45 receiver and31 scenario
projections. Tests also check input/returned-value independence and four malformed
observation controls. Case counts are distinct from unittest method counts.

After reviewing the source and choosing an authorized bounded local execution
profile, run from a clean repository checkout:

```console
python3 -B tests/test_p0_receiver.py -v
```

This selects three unittest methods, not the entire repository test suite or all
85 P0 cases. It needs only the standard library and public repository files.
It does not run contributor programmes, examples, models, subprocesses or a server.

## Limits

The Python API accepts model fields and trusted fixtures; it is not a hardened
JSON endpoint, a general oracle resolver or a production security boundary.
Receipt tables use internal tuple keys; no portable storage format is promised.
Only the selected fixture reference forms are resolved by this test adapter.
Behaviour migration, candidate admission, completed handoff, concurrent ordering
and the explicitly excluded counterexamples are outside this slice.

Local matching supports only the selected synthetic model. It does not establish
full P0 acceptance, production durability, arbitrary external exactly-once
effects, runtime integration, independent reproduction, performance or model-cost
advantage. Existing runtime and model-study acceptance remain separate.
