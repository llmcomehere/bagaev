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

## Equal cost can hide a changed branch

The [branch-edit cases](../examples/probes/record-branch-edit/cases.json) change
only an enabled branch from `x + 1` to `x + 2`, retaining `x` otherwise.
Both programs have conditional upper work 5, so the comparison delta is zero.
For input `(7, false)` both return 7 with work 3. For `(7, true)` they return
8 and 9 with work 5. All these inputs satisfy their dimension declarations.
For `(MAX_INT64, true)` both refuse with `RR_OVERFLOW` at work 5, despite
dimensions being within bounds and work being below its limit.

Six separately frozen complete envelopes matched six actual own-reference
calls, including exact overflow locations. Three portable data tests retain
the fixed source identities, zero cost delta, changed-branch counterexample
and overflow control without rerunning either program. No model, native-kernel
or performance measurement was performed. A matching disabled-branch sample
and equal work bounds do not establish equivalence on the enabled branch.

## Compare supplied capture data explicitly

The pure [capture comparator](../src/bagaev_record_capture_compare.py) accepts
two data objects, each containing exactly `program_sha256`,
`arguments_sha256` and `result`. The caller supplies expected base, target and
one shared argument pin. Here the argument pin is the canonical positional
array hash, not the dimension observer's canonical named-map hash. Mismatched
metadata refuses; matching metadata does not authenticate a capture or prove
that any program ran.

Revision 1 accepts only strict Int64/Bool success envelopes and the documented
integer-overflow, list-index, work-limit and record-list-bound failures from
profile 11. Other result types/statuses refuse. It returns full-envelope
equality, successful typed-value equality, failure identity equality and work
delta separately, with canonical result hashes. Value equality is null unless
both results succeed; failure equality is null unless both are failures.

For the helper examples the recorded values match while work deltas are
0, 4 and 32. For the changed branch, the enabled values differ despite a zero
work delta. Seven data tests cover these controls, result shapes, stale pins,
typed values, identities and input preservation. Source checking, capture
authentication, all-input equivalence checking and execution admission remain
explicitly false. This comparator neither runs programs nor upgrades supplied
data into trusted runtime evidence.

An explicit bounded file command exposes this comparison:

```
python tools/record_capture_compare.py before.json after.json --base BASE_SHA256 --target TARGET_SHA256 --arguments-sha256 POSITIONAL_ARGUMENTS_SHA256 --output comparison.json
```

Inputs use the exact capture-object shape above. Existing strict JSON,
bounded regular-file reads and exclusive output rules apply. The result also
retains both raw input-file hashes, distinct from canonical result identities.
A successful receipt means a file was written even when the compared values
differ. Malformed input, stale pins or wrong usage refuse with exit 2 and no
output. Five transport tests cover equal/different/failure outcomes, identities,
refusals, existing-output preservation and symlink rejection. There is no run
option, implicit capture creation or authentication step.

Four [complete frozen file comparisons](../examples/probes/record-capture-comparison/cases.json)
retain disabled-branch equality, enabled-branch value inequality at unchanged
work, equal overflow with null successful-value equality, and helper extraction
with equal value but four additional work units. Expectations were fixed without
importing the comparator, then matched four serial standalone data CLI calls,
including full output hashes and receipts. Two portable regression tests retain
these outputs. The capture inputs are synthetic fixture wrappers around prior
matched envelopes; this adds no program execution or capture authentication.

## An intentional application rule change

The [all-item total](../examples/probes/record-active-total/All.bagaev) and
[active-item total](../examples/probes/record-active-total/Active.bagaev) use the
same bounded record input: up to sixteen items with Int64 `amount` and Bool
`active`. The new rule adds only active amounts. This is a synthetic application
slice, not a durable catalog or an equivalence-preserving optimization.

Six paired [frozen scenarios](../examples/probes/record-active-total/cases.json)
cover empty, all-active, mixed, negative-inactive, skipped-overflow and active-
overflow inputs. Twelve own-reference calls matched the complete pre-frozen
responses. Empty totals stay 0; all-active 3 and 4 still total 7; inactive 3
and active 4 change the total from 7 to 4. Negative inactive amounts are skipped.
For active MAX_INT64 followed by inactive 1, the old program overflows while
the new one returns MAX_INT64: the inactive addition is genuinely unevaluated.
Making both items active still overflows, at the new expression's exact location.

All selected arguments satisfy their dimensions. Conditional work bounds are
178 and 258. Actual successful work is 98 + 5 times item count for the old
program, and another 5 times active count for the new one. The overflow controls
stop early at work 24 and 34. These are logical charges, not latency or memory
measurements. Three data tests retain source pins, bounds and supplied-capture
comparison axes without rerunning the programs. Equal failure reasons at
changed locations do not count as identical failure observations. This finite
slice establishes no all-input equivalence, native parity or production admission.

Three full-capacity [boundary pairs](../examples/probes/record-active-total/boundary-cases.json)
add six actual own-reference matches: sixteen active amounts 0–15 yield 120
with work 178/258; alternating active even amounts yield 120/56 with work
178/218. Sixteen inactive MAX_INT64 amounts overflow in the old program at
work 24, while the active-only program returns 0 at work 178. These complete
responses were frozen before execution; earlier fixture expectations are unchanged.
Three further data tests reject seventeen records, missing/extra fields,
Bool-as-Int64 and integer-as-Bool inputs, distinguish a valid sixteen-item input
exceeding a declared bound of fifteen, and check the exact detached source draft.
The draft replaces only `main`, preserves declarations, refuses stale pins and
retains false semantic-check and execution-admission flags.
