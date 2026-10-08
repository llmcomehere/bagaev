# Pure ordered inventory batch

This form5 example reserves stock for up to four requests against at most sixteen
items. It reuses the [limited single-request policy](inventory-json.md) and keeps
its eleven predecessor functions unchanged. The separate entry is `batch_main`.
The [source](../examples/probes/inventory-batch/Batch.bagaev),
[contract](../examples/probes/inventory-batch/CONTRACT.md) and
[32 frozen outcomes](../examples/probes/inventory-batch/cases.json) are public.

Input has exactly `interface: "inventory-batch/1"`, `stock` and `requests`.
Each request has exactly `sku` and lexical Int64 `amount`; each stock item has
exactly `sku` and lexical Int64 `available`. All shapes are checked before any
business request. Use the [lossless Json preparation](json-argument-prepare.md)
route with one argument containing this envelope and explicit form5.

Requests apply in order. Success returns `BatchCommitted` with final stock and
ordered receipts, each retaining its own post-request stock snapshot. The first
business failure returns `BatchRejected` with its zero-based step, reason and
original stock. Later requests are skipped. Malformed shape gives step -1,
reason `request-shape` and empty typed stock. An empty batch checks stock validity
and rejects invalid stock at step -1; a nonempty batch retains the existing
request/cap-before-stock policy. Each amount is positive and at most five.

This rollback is a pure returned-value contract. It does not commit a database,
reserve real goods, undo external effects or provide durable exactly-once
transactions. No external state is changed by this programme.

## Resource correction

The first implementation repeatedly called the complete single-request reserve.
The first nineteen cases matched, but the sixteen-item/four-request case with
32-byte SKU names refused at work 65520 before a complete result. The remaining
cases were not run in that first attempt. Its resource budget and frozen expected
values were retained.

After one successful reservation, stock validity is preserved: SKU names/order
are unchanged and a single nonnegative availability is reduced by a positive
amount no larger than itself. Later reached steps use a helper with that explicit
valid-stock precondition, avoiding repeated quadratic validation. The first step
still calls the original reserve; a failed step never reaches the helper.
The [correction rationale](../examples/probes/inventory-batch/OPTIMIZATION.md)
records the invariant and the failed attempt. This is an application-level
change, not a new runtime rule or increased work limit.

## Observed conformance

- An independent ordinary Python implementation matched all 32 pre-frozen full
  values with input preservation.
- The corrected form5 roundtrip preserved its graph and all eleven predecessor
  functions. Thirty-two preparation/reference calls matched all frozen values;
  the largest observed work was 31490. Work values are reference observations,
  not an independently derived work oracle or a universal bound proof.
- The reviewed source was emitted and compiled at LLVM O0/O2 using the same
  admitted toolchains and fixed harness. Across both output prefills, 128 native
  calls matched complete frozen values and reference work. All result bytes
  matched across variants. Inputs, scratch guards/tails and owned-result lifetime
  were checked by the existing harness.
- Three portable tests check the ordinary oracle, source compatibility and
  [captured native wires](../examples/probes/inventory-batch/native-observations.json).
  Decoding those captures is not another native execution.

No speed, allocation, model-choice or cost measurement was performed. These are
bounded same-maintainer conformance observations, not independent reproduction
or full production acceptance. Other inputs can still refuse for profile limits.

## Concrete semantic controls

Five one-site mutants and existing frozen witnesses were selected before the
mutated programmes were created: skipping first stock validation, returning
tentative stock on rollback, reversing request order, discarding prior receipts,
and validating only the first request shape. Each remained a valid checked
profile11 programme and completed normally with `status: success`, but returned
a full value different from its preselected frozen outcome. All five were
detected in five fresh reference calls; no native call or oracle change occurred.

The [contract](../examples/probes/inventory-batch-controls/CONTRACT.md) and
[observations](../examples/probes/inventory-batch-controls/observations.json)
record exact subtrees, programme digests, expected values and observed wrong
values. The portable data test reconstructs each single-site change and verifies
its digest and captured mismatch; it does not run those programmes. These five
controls demonstrate sensitivity to named mistakes, not arbitrary mutation
coverage, native-backend sensitivity or universal correctness.

The separate [one-function batch-total change](inventory-batch-change.md) adds a
synthetic total-ten policy through pinned context, replacement, export and
reference/native checks, preserving this original programme and its oracle.

## Same program with shorter guards

[Batch.lazy.bagaev](../examples/probes/inventory-batch/Batch.lazy.bagaev) is a
separate readable view. Only `sku_ok` and `item_shape` use the lazy form5 spelling:

```
fn sku_ok(sku: Text) -> Bool =
  bool.and(0 < text.bytes(sku), int.le(text.bytes(sku), 32));
```

The two complete source files decode to exactly the same checked-program input
and canonical pin
`sha256:d6b56f365d222f52d015ac336cd2f85bf2626c0148ce7f3fadf2bd243a2f4f66`.
The original source, frozen outcomes and native captures remain unchanged.
Canonical formatting expands the shorthand back to `if`; this is not a second
runtime implementation. Generated Boolean literals keep enclosing source ranges.
Two portable data tests verify full graph/pin/canonical equality and all four
new synthetic literal ranges. No new runtime, native or performance observations
are claimed for an identical lowered program.
