# One-function inventory change through native execution

Start with the [Json inventory example](inventory-json.md). The new policy is:
a request for more than five units returns order-limit, after positive
amount/valid SKU checks and before stock validation. The wrapper's shape gate
still runs before all business rules.

Only reserve changes. The entry, all nominal definitions and the other ten
functions remain identical. The original typed and Json examples and their
expectations are preserved. The
[replacement fragment](../examples/probes/inventory-json-change/ReserveLimited.fragment.bagaev)
contains the one added branch. This is a hand-written policy change, not a model
study.

## Pinned authoring path

The [pins](../examples/probes/inventory-json-change/pins.json) identify the base
programme, original reserve function and target programme. Context reports main
as its caller and decrement, find, sku_ok and stock_ok as direct callees.

The actual data CLI path was:
1. Extract form5 context for reserve from the original readable Json source.
2. Replace only that function using the exact base and function pins.
3. Export the detached draft with exact base and target pins.
4. Prepare each argument through the explicit lossless Json-only route.
5. Separately run the admitted reference on the resulting invocation.

The draft remained unadmitted data until the externally authorized execution.
Applying the old base pin to the exported successor refused with FUNCTION_BASE,
without creating its output. The original source bytes remained unchanged.

Thirty-seven complete expected values were frozen before the new draft:
twenty-four existing cap-five cases translated into the explicit envelope,
plus thirteen existing shape edges. Cap17 remains request-shape in this
envelope. The initial attempt using the unchanged strict typed preparer stopped
at its intended fractional-number refusal. That was retained as a tool-layer
observation; the [separate Json preparer](json-argument-prepare.md) resolved the
data-path gap without changing the old route or business expectations.

## Fresh bounded observations

The complete resumed path passed 41 data CLI calls and 37 reference11 calls.
The emitted target source was then compiled at O0/O2 with the same admitted
LLVM 21.1.8 compiler identity as the prior native qualification. Across all
37 cases and fills 90/165, 148 actual native calls matched full typed values
and logical work; complete output bytes were identical across builds/fills.
The exact-source and embedded-binding harness retained input snapshots,
scratch guards/tails, one-call accounting and owned output export.

These counts describe the final fresh reconstruction and replay. An earlier
successful execution is not added as new case coverage. No performance,
model preference, cost, live inventory or durable transaction claim follows.

The [data packet](../examples/probes/inventory-json-change) includes source,
fragment, programme, pins, frozen cases and captured work/wire digests.
Captured observations are not the independent business oracle.
The [packet helper](../tests/probes/inventory_json_change_packet.py) emits a
selected request or unadmitted harness and checks an existing native output,
using the same modes as the original inventory packet. It never invokes a
compiler, reference or kernel.

A separate portable pass made 189 data CLI calls: 148 existing native captures,
37 requests, one byte-identical harness and three refusal controls.
Three source/context/packet tests and static documentation checks passed.
This pass made no new native calls. A clean external reproduction still needs
its own source/toolchain review and execution profile.
