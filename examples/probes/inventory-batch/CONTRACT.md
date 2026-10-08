# Pure ordered inventory reservation batch, revision 1

Next application slice over the accepted limited Json inventory programme.
Preserve the single-request example and its frozen 37 outcomes unchanged.
Reuse its reserve policy (positive amount, valid SKU, cap five before stock
validation) and underlying eleven functions. Add a separate Json batch entry.
No language/runtime/execution-control change or durable transaction claim.

Input is exactly {interface, stock, requests}, interface inventory-batch/1.
Stock uses the existing exact two-key item shape, at most sixteen entries.
Requests is an array of at most four exact {sku, amount} objects; SKU is Text
and amount is a lexical Int64 under the existing json.int semantics. Validate
all envelope/item/request shapes before business processing. Shape errors return
BatchRejected with step -1, reason request-shape and empty stock (the malformed
input cannot necessarily be represented as a typed Stock).

Process requests in source order against the previous successful stock. On the
first business rejection, return BatchRejected {step: zero-based index, reason,
stock: original typed stock}; discard the tentative receipts. No later business
request is processed. This is pure returned-value rollback, not filesystem,
external side-effect or durable exactly-once atomicity. On full success return
BatchCommitted {stock: final stock, receipts: ordered prior Receipt values}.
Each Receipt retains its stock snapshot after that request. Empty requests is
accepted only after stock business validity is checked; invalid stock gives
step -1 and reason invalid-stock. Nonempty requests retain the existing reserve
policy ordering, including cap checks before stock validity.

Freeze complete literal outputs before implementation: empty valid/invalid,
one success, two sequential reservations of the same SKU, exact exhaustion,
insufficient second request with original-stock rollback, first rejection,
not-found later, cap-six earlier/later, malformed later request taking shape
precedence, duplicate stock, invalid amount/SKU, sixteen stock items and four
requests, fifth-request shape refusal, extra/missing keys and fractional amount.
Work remains bounded by profile11. If the proposed four-request worst case
exceeds 65536, preserve this contract as a refused/inconclusive profile rather
than silently changing the work budget or oracle. No performance claims.

Implementation sequence: freeze literal cases and independent ordinary oracle;
write form5; reference check full outcomes/work; separately review generated
native code and existing harness; finite O0/O2 conformance; exact-head PR review
and CI. Reuse approved bounded profiles only. No automatic invocation helper.
