# Observe a small function extraction

This data-only walkthrough uses the existing [direct sum](../examples/probes/record-work-helper-edit/Direct.bagaev),
[extracted helper](../examples/probes/record-work-helper-edit/Extracted.bagaev)
and [frozen cases](../examples/probes/record-work-helper-edit/cases.json).
It does not run either source program or grant execution permission.

For the two-record case, save the positional arguments as
`[[{"amount":3},{"amount":4}]]` and the bounds as
`{"items":{"type":"Items","items":2}}`. Then write a new observation:

```
python tools/record_work_observe.py examples/probes/record-work-helper-edit/Direct.bagaev --form 5 --program 042ed05a6ad9e7a0d3cc5f8bbe583d6c271dcbe28dd8ddb6934d7366033250d9 --bounds bounds.json --arguments arguments.json --output direct-observation.json
```

For the extracted source use program pin
`b2c6567909b9b43786a9d2822ccae0e21026b4cfd80c69efe0b2df4349e8c813`
and a different new output path. Strict file/JSON limits and exclusive output
rules are in the [profile contract](record-wide-profile.md).

## What the facts mean

- Both actual input lists are within the supplied item maximum. Exact scalar
  field types and the declared list capacity are checked by the dimension
  observer. This is not a complete source semantic check.
- The conditional work bounds are 178 and 210. The analyzer conservatively
  considers the more expensive branch of each of sixteen iterations, even
  for empty input. A bound is not an exact work prediction.
- The previously captured two-record runs returned 7 with work 108 and 112.
  The empty and sixteen-record captures returned 0 and 120. These remain
  prior observations from the frozen cases; this walkthrough adds no run.
- Three data tests check all six before/after source observations against
  the prior graphs and argument identities, plus two negative controls.

## Equal dimensions do not mean equal evidence

Changing the first amount from 3 to 4 leaves the count and conditional work
bound unchanged. Both inputs still report `WITHIN`, but their canonical
argument hashes differ. The old result 7 is not evidence for that changed
invocation. A comment-only source change instead preserves the program graph
pin while changing the raw source hash. Consumers must select the identity
required by their own explicit contract rather than silently treating the
different hashes as interchangeable.

Observation output keeps source, program, raw file and canonical argument
identities separate. Successful file transport, a `WITHIN` dimension result,
a supported work bound and an earlier captured runtime result are distinct
facts. None alone establishes current execution permission, complete language
conformance, equivalence of all inputs, performance or cost benefit.
