# Complete one readable pure change

Start with this original source in `original.bagaev`:

```bagaev
bagaev record-form/1;
program {
  entry calc;
  fn calc(x: Int64) -> Int64 = x + 1;
}
```

Extract a helper into `candidate.bagaev`, preserving the contract:

```bagaev
bagaev record-form/1;
program {
  entry calc;
  fn calc(x: Int64) -> Int64 = plus_one(x);
  fn plus_one(y: Int64) -> Int64 = y + 1;
}
```

The expected result for arguments `[7]` is 8 before and after the change. Keep
that expectation independently of the candidate.

## Inspect identity and signatures

```console
python3 -B tools/record_text.py inspect original.bagaev --output original-info.json
python3 -B tools/record_text.py inspect candidate.bagaev --output candidate-info.json
```

Each output is `bagaev-record-inspection/1`: raw source SHA-256, canonical
`program_sha256`, entry name, sorted function signatures and named-type counts.
Whitespace changes the raw pin but not the program pin. Inspection describes
syntax data; it does not prove that the entry exists, calls resolve or types fit.
Semantic checking and admission remain false. `--arguments` is not accepted.

## Prepare a detached draft

Use the selected original and candidate program pins as BASE_PIN and TARGET_PIN:

```console
python3 -B tools/record_draft.py original.bagaev candidate.bagaev --base BASE_PIN --target TARGET_PIN --output draft.json
```

The delta adds `plus_one` and replaces `calc`. Base/target identity and permitted
structural scope are checked. There is no automatic Store update, receiver,
execution or approval. Review which source you selected before trusting its pin.

## Prepare and evaluate explicit input

Write `[7]` into `arguments.json`:

```console
python3 -B tools/record_text.py prepare candidate.bagaev --arguments arguments.json --output invocation.json
```

Under the repository's execution boundaries, a separately reviewed typed-record/10
reference consumes `run --input invocation.json`. Compare the complete result to
8. Do the same for the original if preserving its behavior matters. Neither the
inspection, draft nor prepare tools launch this reference or choose its path.
Use [syntax diagnostics](record-diagnostics.md) when a readable form is refused.

The finite portable `pure_change_workflow_checks.py` performs eight CLI calls,
two reference calls and two explicit CLI refusals. It verifies exact inspection
metadata, whitespace identity, helper delta, preserved result and source/existing
output bytes. The legacy eleven-call conversion suite also passed. These are
bounded same-maintainer observations, not adoption or total-cost evidence.
