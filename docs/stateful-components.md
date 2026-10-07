# A stateful component with explicit outcomes

A stateful operation needs to say more than “the function returned.” It must
distinguish a proposed state, an ordinary business refusal, a failed computation
and a result that the caller has not observed. The language and receiver carry
these distinctions so each new application does not have to invent them again.

This guide follows the accepted experimental typed component profile. It is
separate from the pure L2/2 filtering language and its saved-source Store.
The [outcome contract](probe-component-outcomes.md),
[change/continuation contract](probe-outcome-composition.md) and
[persistence contract](probe-outcome-persistence.md) own the exact rules.

## Express the application rule

This is the complete existing [StockOutcome source](../examples/probes/component-outcomes/form/StockOutcome.bagaev):

```text
bagaev component-form/2;
component StockItem operation set_quantity {
  record StockKey { code: Text };
  record StockVersion { value: Int64 };
  record Stock { key: StockKey, quantity: Int64, note: Text };
  record SetStock { item: StockKey, expected: StockVersion, quantity: Int64 };
  record StockError { reason: Text };
  variant StockOutcome { Decline: StockError, Propose: Stock };
  state Stock identity key;
  request SetStock identity item revision expected: StockVersion;
  replace quantity;
  outcome StockOutcome error StockError;
  entry apply;
  fn apply(state: Stock, request: SetStock) -> StockOutcome =
    if request.quantity < 0
    then StockOutcome.Decline(StockError { reason: "negative-quantity" })
    else StockOutcome.Propose(Stock { key: state.key, note: state.note, quantity: request.quantity });
}
```

The source declares which state field may change and which record binds the
request to the expected revision. The ordinary rule belongs to the function:
negative quantity returns a typed business error; nonnegative quantity proposes
a Stock with its key and note preserved. The generic receiver does not invent
a stock-management rule.

The [data-only file converter](component-text-cli.md) turns this notation into
source JSON and back without writing a Python wrapper. Semantic checking remains
a separate explicit step.

## Follow the meaning across boundaries

| Observation | Meaning |
| --- | --- |
| Pure Propose | A candidate state value. It has not changed stored state. |
| Pure Decline | A typed business refusal. The receiver still checks current conditions before recording it. |
| Applied receipt | The admitted operation changed application revision R and retained its result. |
| Declined receipt | The operation has a terminal business result without changing R. |
| OutcomeUnknown | The caller has no observable result. It is not permission to repeat an effect under a new identity. |
| Evaluator/type/work failure | Computation failed. It is neither a successful empty value nor a business decline. |

For example, at application revision 7, a valid request for quantity = -1 can end
with Declined at 7. A later valid request can end with Applied at 8. Reading the
first operation again returns its old decline at 7 under current observation
permission. Current state at 8 does not replace the first operation's result.

A proposal checks the preserved fields, exact source/request bindings and current
final conditions before becoming Applied. Equal-state proposals still increment
R under this profile. An exact operation retry uses its retained receipt;
changed intent under the same operation identity conflicts.

## Change the program without rewriting old runs

The [readable edit receiver](probe-outcome-composition.md) checks a compatible
candidate against an exact base. Compatibility alone does not prove the business
rule: changing quantity < 0 to quantity < 1 remains structurally compatible but
incorrectly refuses zero under the existing independent expectation.

Admission checks the candidate's applicable obligations and current receiver
conditions. New runs pin the new program. Existing runs keep their original
source, even when they finish or are observed after an admission.

Persistence keeps three counters separate:
- G identifies the complete stored image.
- H identifies the admitted program generation.
- R identifies application state revision.

A decline can advance G without advancing R or H. Admission can advance G and H
without applying an application operation. A whole-image comparison guards
against overwriting a nested change that did not change H.

## Continue after a missing response

Retain the operation/run identity and independently selected source/context pins.
Use the existing observation port to determine whether its result is known.
Caller-context reconstruction returns checked caller data; it does not restore
permissions, renew a deadline or create a new operation.

The [retained-fact view](probe-outcome-persistence.md#retained-facts-and-old-clock-bindings)
can inspect old terminal results under the original bindings and current
observation permission without activating a writable owner. Ordinary activation
in a different clock domain remains refused. Clock migration and remote effects
are outside this profile.

## Select the execution boundary deliberately

This is an experimental single-writer Linux/CPython/SQLite profile with a
separately reviewed typed checker/reference and trusted host callbacks.
It is not a production service, universal authorization layer or proof against
arbitrary storage failures. Selected process-cut checks are not power-loss tests.

The linked contracts contain the bounded reproduction drivers and executable
selection requirements. Review source and use an authorized execution profile
before running them. Neither this example nor a successful source check grants
execution authority. No model call is needed to use the documented language
forms.
