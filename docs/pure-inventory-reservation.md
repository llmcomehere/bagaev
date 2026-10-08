# Reserve inventory as a pure value

[Reserve.bagaev](../examples/probes/inventory-reserve/Reserve.bagaev) is a practical
readable form5 example: reserve a positive quantity of one SKU from at most
sixteen stock records. It uses the existing profile11 reference, without new
language operations, limits or execution controls.

```bagaev
fn reserve(stock: Stock, sku: Text, amount: Int64) -> Outcome =
  if amount < 1 then Outcome.Rejected("invalid-request")
  else if bool.not(sku_ok(sku)) then Outcome.Rejected("invalid-request")
  else if bool.not(stock_ok(stock)) then Outcome.Rejected("invalid-stock")
  else let index = find(stock, sku) in
    if index < 0 then Outcome.Rejected("not-found")
    else if record.field(records.at(stock, index), "available") < amount
      then Outcome.Rejected("insufficient-stock")
    else Outcome.Reserved(Receipt {
      stock: decrement(stock, index, amount), sku: sku, amount: amount
    });
```

The linked file includes the records, variant and all helper definitions.
A success returns the entire replacement stock and reservation quantity/SKU.
Only the matched item's availability decreases; order and other records remain.
Refusal returns a reason with no partial stock. The input is an immutable value.

## Exact refusal order

1. Invalid request: amount below1 or request SKU outside1–32 UTF-8 bytes.
2. Invalid stock: negative availability, invalid item SKU or duplicate exact SKU,
   including non-adjacent duplicates.
3. Requested SKU not found.
4. Insufficient availability.

SKU equality is exact Unicode text equality with no normalization. The subtraction
occurs only after positive amount is no larger than nonnegative availability;
Int64 boundary values do not overflow that operation. Malformed typed arguments
and a seventeen-element Stock fail at the reference argument boundary rather
than becoming application refusals. Work and other existing runtime limits apply.

## Use and evidence

Use `record_text.py prepare` with explicit `--form 5` and an argument array
`[stock, sku, amount]`, then a separately reviewed profile11 reference under an
approved execution profile. A typical stock value is
`[{"sku":"a","available":10},{"sku":"b","available":3}]`.
Reserving4 of a returns availability6 and3 in the same order.

Nineteen literal full outcomes were frozen before implementation: partial/exact
reservation, maximum Int64, Unicode SKU, sixteenth-entry update, request/stock
refusals and their precedence, and a typed capacity refusal. All19 matched the
reference, and the readable graph round-tripped exactly. The portable
`tests/probes/inventory_reserve_checks.py` uses the existing explicit reader and
reference path/hash arguments plus a new output directory. Same-maintainer
bounded conformance is not independent reproduction or a performance result.

This function does not reserve real goods, write a database, serialize competing
clients or deduplicate retries. A caller must retain and explicitly feed the
returned stock into a later computation; evaluating again on the old input gives
the old-input result. Durable operations require the separate stateful component
route and its acceptance conditions. The older scalar stock-adjustment component
example remains unchanged.

The [focused business-change walkthrough](inventory-focused-change.md) adds a
five-unit reservation limit while preserving this original example and oracle.

## Separate Json request and native route

The [inventory Json wrapper](inventory-json.md) preserves these business
functions and adds an explicit shape-checked request envelope. Its selected
reference/native observations do not change this typed example's contract.
