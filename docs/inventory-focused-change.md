# Make one real business change

The [pure inventory example](pure-inventory-reservation.md) can be changed without
replacing its helpers or types. This separate example limits a single reservation
to five units. It preserves the original source and nineteen-case oracle.

The new condition is inserted in reserve after request validation and before
stock validation:

```bagaev
else if 5 < amount then Outcome.Rejected("order-limit")
```

That position is part of the contract. An invalid request still wins; a valid
request above five is rejected before examining malformed stock or looking for
the SKU. Exactly five follows the old stock/existence/availability checks.
This is a business-rule example, not a new execution or access policy.

## Artifacts and handoff

- [Focused replacement](../examples/probes/inventory-change/ReserveLimited.fragment.bagaev):
  all required type declarations and just the reserve function.
- [Complete candidate](../examples/probes/inventory-change/ReserveLimited.bagaev):
  a reviewable full source, with all other functions unchanged.
- [Expected identities](../examples/probes/inventory-change/pins.json):
  original program/function and candidate program hashes.
- [Complete expected outcomes](../examples/probes/inventory-change/cases.json):
  separately frozen before candidate implementation; the original oracle is untouched.

Use the [focused command](wide-function-editing.md) to get context and create a
draft with the expected base/function pins. Feed that actual draft to the
[pinned exporter](record-draft-export.md), then its actual output to form5
preparation. A separately admitted profile11 reference consumes that prepared
invocation. These steps do not infer execution authority from a hash.

The portable `tests/probes/inventory_change_checks.py` performs this exact chain
under an independently approved execution profile, with explicit reader/reference
paths/hashes and a new output directory. It verifies direct call context, the
complete single-function delta, candidate identity, and unchanged original bytes.
It then prepares and runs all24 literal cases and refuses an attempted old-base
replacement against the new candidate. There were28 CLI calls and24 reference
calls. All passed in the bounded same-maintainer run.

The new expectations include the limit boundary and request/stock/missing-item
precedence. Two formerly successful large reservations now return order-limit;
this is an observable semantic change, not a formatting-only edit or dead wrapper.
The full outcomes still distinguish typed argument refusal from business refusal.
No real stock was changed. Performance, model cost, independent reproduction and
model preference were not measured.
