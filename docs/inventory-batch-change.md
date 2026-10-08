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

An [ordinary native Rust baseline](inventory-native-baseline.md) implements both
policies against the same frozen values. Its shared JSON parser and different
CLI boundary are explicit; conformance alone is not a performance comparison.

## Try the annotated, layout-preserving path

The [annotated original](../examples/probes/annotated-change/Batch.annotated.bagaev),
[expected changed source](../examples/probes/annotated-change/BatchLimited.annotated.bagaev)
and [manifest](../examples/probes/annotated-change/manifest.json) make this change
reproducible without a private workspace. They use the same accepted original
and total-10 program graphs, not a new policy or execution observation.

In a separately authorized data-tool environment, from the repository root:

```sh
mkdir demo-output
SOURCE=examples/probes/annotated-change/Batch.annotated.bagaev
FRAGMENT=examples/probes/inventory-batch-change/BatchLimited.fragment.bagaev
BASE=d6b56f365d222f52d015ac336cd2f85bf2626c0148ce7f3fadf2bd243a2f4f66
FUNCTION=7f22256c03ea16556738c8e69ce619424335150087f2784b14f6cdc298bd6696
TARGET=b4755a73e1090e2b4ed563f42c29250dc759c5b1224d3c5765a239cb6584351e
SOURCE_SHA=91973a5772e163c6fb84856814d4dfa2ed4536fbbe03a0eca5105a61098e44f3
python tools/record_function.py context "$SOURCE" --form 5 --name batch_apply --locations --output demo-output/context.json
python tools/record_function.py replace "$SOURCE" --form 5 --replacement "$FRAGMENT" --base "$BASE" --function-pin "$FUNCTION" --output demo-output/draft.json
python tools/record_export.py "$SOURCE" --form 5 --draft demo-output/draft.json --base "$BASE" --target "$TARGET" --preserve-layout --source-sha256 "$SOURCE_SHA" --output demo-output/BatchLimited.annotated.bagaev
python tools/record_text.py inspect demo-output/BatchLimited.annotated.bagaev --form 5 --output demo-output/inspection.json
```

Use a fresh output directory; existing output files are refused. The inspected
program hash must equal `TARGET`, and output bytes must equal the expected source
fixture. The manifest also pins context/draft/inspection artifacts. All bytes
outside `batch_apply`'s replaced expression, including the unrelated notes,
remain identical. The explicitly marked inside-body note is replaced.

These four commands inspect and transform data. They do not execute the program,
compile a kernel, admit an artifact or change real inventory. The public replay
test repeated all four commands and compared every captured artifact hash and
source byte. Existing runtime/native observations belong to the unchanged
program graphs and are not counted again for this walkthrough.
