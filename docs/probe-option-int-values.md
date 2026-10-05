# Bounded optional Int64 value precursor

Experimental value contract: `bagaev-option-int64-value/1`.
The public synthetic catalog distinguishes missing dates from day zero; this
value is a reusable precursor for representing missing scalar data explicitly.
It does not change catalog date validation (0..31 when present), add a language
operator, or claim application integration. The source/native profile remains
separate until its own frozen grammar, work, invocation and ABI rules exist.

A value is exactly None or Some(Int64), with all signed 64-bit payloads allowed
when present. There is no automatic conversion from Bool, Text or a sentinel
integer. None is distinct from Some(0). Equality compares presence first, then
payload only when present. A fallback operation evaluates its supplier exactly
once for None and never for Some, including Some(0).

## Portable value encoding

Exactly 16 bytes: byte0 is presence0/1, bytes1..7 are zero, bytes8..15 contain the
little-endian two's-complement Int64 payload. None requires payload zero; Some
allows every Int64. This is a byte format, not a promise about Rust enum layout.
No raw pointers, allocation, I/O, execution authority or runtime selection.

Validation order and refusal:
1. Length !=16: OPT_SIZE at offset0.
2. Presence >1: OPT_FLAG at offset0.
3. Nonzero reserved bytes: OPT_PADDING at first offending offset1..7.
4. Presence0 with nonzero payload: OPT_PAYLOAD at offset8.

Successful decode consumes the whole immutable input and preserves all bytes.
Encoding always returns exactly16 canonical bytes. A Rust wrapper must keep
fields private and expose only checked decoding or explicit none/some factories.
Roundtrip equality does not alone establish correctness: tests include literal
wire/value expectations, failure precedence and a counted lazy supplier.

No native language admission, timing, performance or production-safety result
is implied by this library. Integration must separately define work ticks and
preserve fallback laziness without changing existing scalar/Text profiles.

## Bounded library implementation

The [Rust value library](../examples/probes/backend/rust/option_int.rs) implements
private checked values and canonical encoding without allocation or unsafe code.
All 17 [pre-implementation literal wire cases](../examples/probes/option-int-value-cases.json)
and three API contract tests passed. Five concrete mutations were detected by
named unit assertions: treating zero as missing, accepting a noncanonical None
payload, reversed endianness, eager fallback and ignored padding. Mutation
builds succeeded; a failed build or timeout would not count as a detection.
[Observations](../examples/probes/option-int-value-observations.json) disclose
exact edits, witnesses and limits. The [tests](../tests/probes/backend/option_int_tests.rs)
include unchanged full inputs and exact successful encodings.

This is a same-maintainer value-library precursor. Source-language integration,
work accounting, native ABI and catalog/application acceptance remain future work.
