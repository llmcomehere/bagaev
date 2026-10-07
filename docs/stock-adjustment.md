# A readable stock adjustment with retained results

This example composes two business decisions in the language and carries their
actual typed results through the existing serial SQLite image bridge. It uses
one fixed component source throughout. It is a bounded application example,
not a new storage engine or a production service.

## Compose the rules

The [complete source](../examples/probes/stock-adjustment/StockAdjustment.bagaev)
first computes a proposed stock quantity. Negative quantities produce a typed
Decline. Its entry function consumes that outcome with match and additionally
rejects quantities above 100:

```text
match (raw_adjust(state, request)) {
  Decline(error): StockOutcome.Decline(error);
  Propose(proposed): if 100 < proposed.quantity
    then StockOutcome.Decline(StockError { reason: "capacity-exceeded" })
    else StockOutcome.Propose(proposed);
}
```

The capacity 100 and the two reason strings are this example's business rules.
They are not global language limits. A Propose is pure data; the receiver
separately determines whether it becomes an Applied receipt and state change.

## Follow the state and receipts

Start with quantity 10 and application revision 7. Each request supplies the
expected revision and an operation identity:

| Operation | Delta | Expected revision | Recorded result | Current quantity / revision |
| --- | ---: | ---: | --- | --- |
| A | -20 | 7 | Declined: negative-quantity, revision 7 | 10 / 7 |
| B | 3 | 7 | Applied, revision 8 | 13 / 8 |
| C | 100 | 8 | Declined: capacity-exceeded, revision 8 | 13 / 8 |
| D | -13 | 8 | Applied, revision 9 | 0 / 9 |
| E | 7 | 9 | Applied retained, response OutcomeUnknown | 7 / 10 |

For E, the fixture disables observation before submission. This exercises the
existing distinction between committing a result and being allowed to observe
it. It does not simulate a network transport failure. Five terminal operations
produce storage generation 5, while only three applied changes advance the
application revision to 10. Business declines do not mutate stock.

A fresh bridge object then reconstructs the existing image using the same
explicit source, policy, resource and clock domain. Resubmitting E while
observation remains disabled returns AccessDenied and performs no new business
evaluation. With current observation enabled, it reads E's original Applied
receipt and A's original Declined receipt at revision 7. Current state remains
quantity 7 at revision 10. A new F request is denied while current submit/write
conditions are false. None of these reads or refusals changes the saved image.

The first unobserved submission's OutcomeUnknown and a later forbidden receipt
read's AccessDenied are different observations. The initial runner confused them;
that runner assertion was corrected to the existing owner contract. The original
failure and raw calls were retained, and the five frozen business receipts and
state expectations were not changed. A preparation-script syntax typo was also
corrected before the contract was frozen or the connected runner existed.

## Reproduce the bounded example

Review the source and select the existing component reader and typed-record/10
reference binaries under an authorized local execution profile:

```console
python3 -B tests/probes/stock_adjustment_checks.py --reader /absolute/reviewed/reader --reader-sha256 READER_SHA256 --reference /absolute/reviewed/record-reference10 --reference-sha256 REFERENCE_SHA256 --output /absolute/new-output-directory
```

Use your selected reviewed build paths and actual hashes. The harness creates
its own new SQLite file and retains raw inputs/outputs. It does not install,
download or build executables. A hash identifies bytes, not permission to run
an otherwise untrusted binary. The [fixture manifest](../examples/probes/stock-adjustment/manifest.json)
binds the readable source, exact source graph, full receipts and state trace.

The passing connected run made 104 native calls, including value validation and
source/policy checking; five were business application evaluations. Later
reconstruction/replay added zero business evaluations. The portable repetition
reused the same cases, not new independent coverage.

## Limits

This is one fixed programme source. There is no programme-head transition,
new-source qualification or live source admission in this example. Reconstruction
uses a fresh object, not a killed process, machine restart or power-loss test.
The existing bridge's trusted callbacks, filesystem, SQLite and single-writer
assumptions remain. Current-condition flags are a test model, not authentication
or production access control. No cost, memory, speed or model-choice measurement
is claimed. See [stateful components](stateful-components.md) for the broader
outcome/recovery boundaries and [readable authoring](readable-authoring.md) for
preparing a separately checked change.
