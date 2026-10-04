# Pinned source-location lookup

Experimental contract: `bagaev-typed-source-location/1`. Frozen before the
location-lookup implementation. This is a pure mapping operation, not a native
result decoder, execution witness validator or grant of admission.

## Inputs and ordering

Inputs are complete `bagaev-typed-scalar/1` source bytes, an expected lowered
program pin string, and a node number in the unsigned 16-bit domain. No caller
origin table is trusted.

1. Recheck the source and its exact lowering with the existing source checker
   and frozen kernel checker. A source-language refusal returns
   `TS_LOCATION_SOURCE`. Environment/allocation/lowering inconsistencies remain
   environment failures rather than location refusals.
2. Compare the caller's expected pin byte-for-byte with the rechecked lowered
   identity. Any difference, including malformed/uppercase pins, returns
   `TS_LOCATION_PIN`. There is no repair or implicit repinning.
3. Require a node number from 1 through the complete expression count. Zero or
   an out-of-range number returns `TS_LOCATION_NODE`.
4. Return the corresponding source and lowered program-relative expression
   pointers, using the rechecked complete-preorder origin map.

These phases are ordered: invalid source wins over pin/node problems, and a pin
mismatch wins over a node-range problem. Every branch, including unused bodies,
belongs to the same complete numbering established by the source contract.
Inserted type metadata is not a node. Argument slots and metadata fields cannot
be translated by passing them as expression IDs.

## Exact output variants

Mapped output has exactly `schema`, `kind`=`mapped`, `source_pin`, `lowered_pin`,
`node`, `source_location`, `lowered_location`, `execution_admission`=false.
The schema is `bagaev-typed-source-location/1`. The pointers are relative to each
complete program, without an invocation `/program` prefix.

Refused output has exactly `schema`, `kind`=`refused`, `code` and
`execution_admission`=false. Codes are the three listed above. Canonical JSON
plus one LF is used on the wire. The existing 8 MiB output bound remains an
environment limit. No input/source/location is silently truncated.

A matching pin and node establish only a deterministic mapping for those source
bytes. They do not authenticate where an alleged native result came from, prove
that the node executed, establish a valid ABI capture or certify a trustworthy
compiler. A caller must independently bind and validate its execution evidence.
Neither a source draft nor this mapping may provide its own execution authority.

## Pre-implementation fixture set

[Location fixtures](../examples/probes/typed-source-location-cases.json) cover all
581 expression origins in the twelve successful source cases from the earlier
frozen scalar-source suite, plus eight refusals/priority collisions. Inputs are
referenced by case ID in the two pinned source-fixture files; expected locations
come from their pre-existing origin records, not a location implementation.
The raw invalid-UTF-8 case is retained as bytes.

This initial 589-case scope covers nested index shifts and the 512-node boundary.
It does not define a full source-runtime result API or argument-slot translation.
The original contract publication made no implementation or native execution claim.

## Implementation and bounded observations

The [Rust source module](../examples/probes/backend/rust/typed_source.rs) now
provides `project_node(source_bytes, expected_lowered_pin, node_u16)`. The
[explicit-file CLI](../examples/probes/backend/rust/typed_main.rs) accepts
`project-node --input FILE --lowered-pin PIN --node U16`. CLI node spelling is
canonical unsigned decimal; negative, signed-plus, leading-zero and >65535
arguments fail the CLI boundary. Do not narrow an argument-slot tag into a node ID.

All 589 frozen wires matched, and all 43 earlier source-check wires still matched
with the extended binary. Four CLI numeric-domain controls refused with nonzero
exit and no stdout. Compilation with Rust 1.93.0 and `-D warnings` passed. The
[pinned fixture runner](../tests/probes/typed_source_location_contract.py) requires
an explicit binary and new output directory inside an authorized bounded profile.

The [observations](../examples/probes/typed-source-location-observations.json)
also include 72 mappings of already captured overflow/work-limit ABI failures
from the earlier native composition run. Those repeat six failing kernel stages
across backends, modes and prefills. Their source/lowered identities and expected
origin records were checked; no new native program ran for this mapping test.
This still does not authenticate arbitrary supplied runtime evidence. Review
was a separate same-maintainer pass.
