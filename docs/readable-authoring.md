# Write, diagnose and change a component

Use this route when a component's arithmetic is easier to understand as a
formula than as a JSON expression tree. The example adjusts stock quantity,
then extracts its calculation into a helper without changing the interface.
All commands below are data preparation unless a separately reviewed checker
or reference executable is explicitly selected. Review source and the
[execution rules](../AGENTS.md) and use an authorized bounded profile first.

## 1. Start with the business rule

The complete [StockAdjustment source](../examples/probes/component-arithmetic/StockAdjustment.bagaev)
contains this calculation:

```text
let next = state.quantity + request.delta in
  if next < 0
  then StockOutcome.Decline(StockError { reason: "negative-quantity" })
  else StockOutcome.Propose(Stock { key: state.key, note: state.note, quantity: next })
```

For quantity 10, delta -10 must propose quantity 0. Delta -11 must decline.
These expectations belong to the business rule. A well-typed program can still
implement the wrong rule.

## 2. Locate a syntax refusal

```console
python3 -B tools/component_diagnose.py examples/probes/component-arithmetic/StockAdjustment.bagaev
```

The command emits JSON and exits 0 for a valid form, 2 for a refusal. In a local
copy, removing the semicolon from `entry apply;` gives FORM_SYNTAX. The report's
span is labelled `context`: it covers previous/lookahead parsing context and
is not a claim that one particular character is the unique cause. Correct the
copy yourself and diagnose it again. The command does not rewrite the source.

The [diagnostic contract](component-diagnostics.md) defines UTF-8 byte offsets,
line/column counting, null spans and bounds. Always match source_sha256 to the
bytes you are looking at. A successful diagnostic still reports
semantic_check:false and execution_admission:false.

## 3. Produce the semantic source

Use a new output filename:

```console
python3 -B tools/component_text.py decode examples/probes/component-arithmetic/StockAdjustment.bagaev --form 3 --output adjustment.json
```

This explicitly selects form 3 and creates component-source/2 data. It neither
checks the receiver's policy nor runs the operation. Existing output files are
refused. The [converter](component-text-cli.md) also supports encoding the JSON
back into canonical readable text.

## 4. Prepare an exact change

The [helper extraction](../examples/probes/component-arithmetic/edit/S2.bagaev)
adds `adjusted(current, delta)` and changes `apply` to call it. Its edit/3 frame
carries the exact base and target source identities plus the actual candidate
text. The fixed `bagaev_component_arithmetic_edit.draft` API takes the original
text, frame, separately selected receiving policy and reviewed checker.

The [edit contract](component-arithmetic-edits.md) checks both sources against
that policy, preserves existing signatures and declarations, and returns the
exact delta: add adjusted, replace apply. A detached draft has
execution_admission:false. No current program head or application state changes.

Do not turn a syntax success or compatible draft into a business approval.
The existing compatible-but-wrong candidate rejects zero; the frozen zero case
catches it. Qualification and live admission remain separate receiver decisions.

## Reproduce the connected path

After selecting and reviewing the existing component reader and typed-record/10
reference executables, run the portable harness in the approved local profile:

```console
python3 -B tests/probes/readable_authoring_checks.py --reader /absolute/reviewed/reader --reader-sha256 READER_SHA256 --reference /absolute/reviewed/record-reference10 --reference-sha256 REFERENCE_SHA256 --output /absolute/new-output-directory
```

Replace the paths and hashes with your independently selected reviewed builds.
The harness does not download or compile anything. A supplied hash binds the
selected bytes; it does not establish that those bytes are trustworthy.

The bounded connected run made four file-tool calls, four actual source/policy
checks and two pure reference invocations. It retained the malformed source,
checked the corrected source, matched the exact existing helper draft and
observed the existing zero-case counterexample. It preserved input bytes and
produced no external application effect. These are connected repetitions of
existing expectations, not new semantic cases, independent reproduction,
performance measurements or production acceptance.
