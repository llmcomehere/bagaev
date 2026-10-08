# One-function batch total change

This is a synthetic focused-development exercise over the accepted
[ordered inventory batch](inventory-batch.md). It adds a total limit of ten
reserved units to the existing per-request limit of five. Equality with ten
succeeds. An otherwise successful reservation exceeding the batch total returns
`batch-limit` at its step, with the original stock. Existing shape and individual
business failures retain precedence. This is pure returned-value rollback, not
an external inventory transaction or a new real-world policy.

Only `batch_apply` changes. The entry, named types and all sixteen other functions
are unchanged. The original programme and 32-case oracle remain available.
[Forty separate full outcomes](../examples/probes/inventory-batch-change/cases.json)
were frozen before the source edit: only the original long-SKU four-request
outcome changes, and eight literal cases cover totals9/10/11, fourth-step refusal,
rollback and failure precedence. An ordinary Python implementation using a
running counter matched all forty; the bagaev function independently sums the
previous receipt amounts with a four-step fold.

## Pinned workflow

1. Extract `batch_apply` context, optionally with `--locations --form 5` to retain
   ranges in the original full source. The fragment's base and function digest
   must match the [pins](../examples/probes/inventory-batch-change/pins.json).
2. Apply the [replacement fragment](../examples/probes/inventory-batch-change/BatchLimited.fragment.bagaev)
   through `record_function.py replace` with those exact pins. It creates only a
   detached draft; stale base/function pins refuse without output.
3. Export the pinned draft with `record_export.py` and explicit form5. The
   [exported source](../examples/probes/inventory-batch-change/BatchLimited.bagaev)
   must decode to the recorded [target graph](../examples/probes/inventory-batch-change/program.json).
4. Prepare one-element Json argument arrays with `record_json_prepare.py`.
   Programme execution and native compilation still require their own admitted
   reference/toolchains/profile; the data tools do not launch them.

The initial fragment could not encode because a fold operand absorbed following
arithmetic. Its roundtrip guard refused before the changed-policy run. The
separate [form5 grouping correction](record-wide-profile.md#control-expression-operand-grouping)
retained that guard and fixed the real codec defect. No policy oracle was edited
to hide the failure.

## Evidence and limits

Forty complete outcomes matched the ordinary oracle and forty fresh admitted
reference calls. The actual data path made45 CLI calls, including two stale-pin
refusals; original source bytes were preserved. Largest observed work was29855.
These work observations are not an independent work oracle or a universal bound.

Fresh emitted LLVM at O0/O2, with both existing output-prefill variants, made160
native calls. Complete values and reference work matched; wires were identical
across variants, with input and harness guard/tail checks. Three portable tests
check the frozen oracle, exact replacement and captured wire data. Re-reading
those captures is not new native execution. No model, speed, memory, allocation
or cost measurement was made. Same-maintainer bounded conformance does not
establish independent reproduction or production acceptance.
