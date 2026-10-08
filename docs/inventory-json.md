# A native-eligible pure inventory request

The [typed reserve example](pure-inventory-reservation.md) now has a separate readable
[Json wrapper](../examples/probes/inventory-json/Reserve.bagaev). It uses the
existing form5/profile11 Json entry, so the same useful stock calculation can
follow the existing native path. All six original business functions and nominal
types are unchanged. The original typed entry and its nineteen cases remain.

A request has exactly four fields: interface="inventory-reserve/1", stock,
sku and amount. Stock is an array of at most sixteen exact sku/available objects.
Sku fields must be bounded Text; amount and available must convert through
existing json.int to Int64. Missing/extra fields, wrong interface/type, fractional
or Boolean counts and oversized stock return Outcome.Rejected("request-shape").
Shape validation completes before business validation.

For valid shapes, the original reserve order remains: positive amount and
nonempty SKU up to 32 UTF-8 bytes, valid nonnegative uniquely named stock,
requested item existence, then sufficient stock. Success returns an immutable
updated stock plus the requested SKU/amount. This wrapper uses the original
unlimited-per-order example, not the separate cap-five policy-change example.

The seventeenth-item case deliberately maps to a shape rejection in this new
application envelope. The old typed-entry argument refusal is unchanged.
No coercion, persistence, actual stock mutation, transaction, concurrency or
authentication is introduced.

## Complete observations

Thirty-two full outcomes were frozen before implementation: eighteen unchanged
business outcomes, the explicit seventeenth-item mapping and thirteen shape
edges. Original function graphs and all nominal definitions matched exactly;
readable source round-tripped without graph changes.

Thirty-two reference11 calls passed. The one exact source was then emitted and
compiled at O0/O2 with the same LLVM 21.1.8 toolchain identity as
[the prior qualification](probe-native-wide-qualification.md). The qualified
source/binding-pinned harness actually made 128 native calls across those cases
and fills 90/165. Full typed outcomes and logical work matched reference; complete
wire bytes were identical across optimizations and fills. Input snapshots,
scratch guards/tails and owned output checks remained in force.

These are selected correctness observations, not speed, cost, model preference,
durable inventory operation or complete language acceptance. Captured work and
wire digests are observations; the [frozen cases](../examples/probes/inventory-json/cases.json)
remain the business expectations.

## Reproduction data

The [data-only helper](../tests/probes/inventory_json_packet.py) emits a selected
request or exact-source harness and checks an existing native output. It does
not compile, launch a process or admit execution. Modes are request CASE,
harness CASE --backend ABSOLUTE_BACKEND_SOURCE_PATH, and check-native CASE
--output FILE. Use the unchanged separately admitted reproduction procedure
from the linked native qualification.

[Packet tests](../tests/probes/test_inventory_json_packet.py) check the source
roundtrip, unchanged business graphs, all request bindings and explicit cap
mapping without executing the language program. Original programme, ordinary
typed usage and policy-change examples remain separate.

The portable check pass used 164 data-only CLI calls: 128 existing native
captures, 32 requests, one byte-identical harness and three intentional refusals.
Four source/data tests and static documentation checks passed. This pass did
not run another native kernel.

For readable-source preparation that preserves fractional or large numeric
arguments until this application's shape check, use the explicit
[lossless Json-only preparation route](json-argument-prepare.md). The original
typed preparer refuses those numeric tokens earlier by design.
