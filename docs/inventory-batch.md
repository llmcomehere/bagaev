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
