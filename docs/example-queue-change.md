# Change a bounded support-queue rule

This small synthetic application uses the existing L2 language and CLI. It adds
no interpreter feature. It is an authored example, not a model-completion study,
production queue or claim of lower cost than ordinary Python.

## Task and changed requirement

Accept exactly `{"jobs": [...]}` with at most eight jobs. Each job has an `id`
and Boolean `urgent`, and may have an integer `priority` from 0 through 9.
IDs are unique, one through eight ASCII characters matching
`[a-z][a-z0-9-]{0,7}`. Unknown or missing fields, null/float/Boolean priorities,
and invalid IDs refuse with `{"kind":"refusal","reason":"invalid-request"}`.

Return `{"kind":"ok","order":[...]}` containing IDs: urgent jobs first, then
lower priority numbers first, then IDs in ascending ASCII order. Initially a
missing priority counts as zero. The requested change puts missing priorities
after all explicit priorities **within each urgency group**. Urgency still wins.
Neither version mutates its input. This is pure ordering, with no job execution,
user accounts, deployment, network or external service.

## Run and change it

Review the source and use an authorized local execution profile as described in
[the beta guide](beta.md). From the checkout root, with a new owned output filename:

```console
python3 -B -S -m src.bagaev run examples/l2/queue/initial.json --input examples/l2/queue/input.json
python3 -B -S -m src.bagaev patch examples/l2/queue/initial.json examples/l2/queue/missing-last.patch --output queue-updated.json
python3 -B -S -m src.bagaev run queue-updated.json --input examples/l2/queue/input.json
```

The first run's `result.value` is `{"kind":"ok","order":["a","b"]}`.
The last is `{"kind":"ok","order":["b","a"]}`: job `a` has no priority,
while `b` has explicit priority zero. Both are urgent. The patch replaces only
the `key` definition; its exact base, target and transitive pins are checked.
`queue-updated.json` is written by the CLI and must not already exist.

Trying the same patch against `queue-updated.json`, with a different new output
filename, must fail with `L2_STALE` and exit 2; it must not create that output.
Do not treat this intentional refusal as a failed application result.

## Check the requirements

```console
python3 -B tests/probes/queue_order_checks.py
```

The checked data contains 23 pre-implementation literal cases for both revisions.
The driver compares an ordinary Python implementation, the L2 reference and
fresh verified CPython lowering against those same expectations: 46 case/revision
comparisons. It also rejects the stale patch and detects two normal wrong outputs:
retaining the old missing-priority rule and ignoring urgency. Input files stay
unchanged. Generated Python executes only after equality with trusted lowering;
this is not permission to run arbitrary generated or contributor code.

Ordinary Python expresses this task compactly with validation and a tuple sort
key. bagaev's additional structure exposes the exact changed definition and
revision checks; whether that pays for itself depends on the larger change and
handoff workflow. No timing, token, lifecycle-cost or preference advantage is
established by the matching results. This is not an exhaustive conformance suite.
