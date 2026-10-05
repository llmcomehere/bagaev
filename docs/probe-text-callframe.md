# Typed Text call-frame proposal

Status: experimental data-boundary contract with a portable Rust decoder; native Text code generation remains future work.
The old scalar ABI is unchanged. This frame carries values, not pointers or
execution authority. Future native code must receive separately admitted buffers
and a checked program; accepting this data alone never grants execution.

## Input bytes

A frame is exactly 8272 bytes, byte-addressed and little-endian. No native struct
layout, padding or host alignment is implied.

- Bytes 0..8: literal magic `BTXTIN1\0` (8 bytes).
- Bytes 8..12: unsigned argument count, at most 8.
- Bytes 12..16: zero.
- Eight consecutive slots begin at byte 16. Each is 1032 bytes: unsigned 32-bit
  tag, unsigned 32-bit payload length, then exactly 1024 payload bytes.
- Active tags: 1 = Int64 (length 8, two's-complement little-endian); 2 = Bool
  (length 1, payload byte exactly 0 or 1); 3 = Text (length 0..1024, strict UTF-8,
  at most 256 Unicode scalar values, existing Text value semantics).
- Every byte after the declared payload length is zero. Embedded NUL in Text is
  ordinary content and does not end a value.
- Inactive slots have tag 0, length 0 and all payload bytes zero.

The separately supplied expected signature contains 0..8 Bool/Int64/Text types.
A mismatched argument count or tag is refused. Signature validation is a caller
precondition supplied by a checked program, not inferred from the frame.

## Deterministic validation

No partial argument list is returned. Input is immutable and Text borrows its
payload from the entire input lifetime. Decoding allocates no Text payload.

Refusals have a stable category and a byte offset (no raw input echo):
1. Wrong frame size: `FRAME_SIZE`, offset 0.
2. Wrong magic: `FRAME_MAGIC`, first differing magic byte.
3. Invalid signature length (>8): `SIGNATURE`, offset 8.
4. Count >8 or not equal to expected signature length: `ARG_COUNT`, offset 8.
5. Nonzero header reserved byte: `RESERVED`, first nonzero byte 12..16.
6. Visit slots in index order. Inactive slot: first nonzero byte anywhere in its
   1032 bytes gives `UNUSED` at that byte. Active slot: tag mismatch/unknown gives
   `ARG_TAG` at slot start; invalid length gives `ARG_LENGTH` at slot+4; then
   validate the payload (Bool >1 gives `BOOL_VALUE` at slot+8, invalid UTF-8 or
   >256 scalar Text gives `TEXT_VALUE` at slot+8); finally nonzero tail gives
   `PADDING` at its first nonzero byte.

Successful decoding consumes zero language work: this is admission/transport,
not evaluation. No timing/memory advantage is claimed. Missing output buffer,
overlap, external pointer validity and generated function ABI are not addressed
by a byte-slice decoder and require a later native-call contract.

## Acceptance plan

Freeze exact byte edits and expected values/refusals before implementing a
portable Rust decoder. Include signed extrema, empty/NUL/supplementary Text,
UTF-8 invalidity, scalar/byte bounds, every header/tag/padding gate and competing
errors. Confirm unchanged inputs and borrowed Text pointer identity. Later
cross-check the same literal frames with the native entry adapter before any
native Text conformance claim.

## Portable decoder evidence

The [safe Rust decoder](../examples/probes/backend/rust/text_callframe.rs)
implements this byte-slice boundary without unsafe code, I/O or allocation.
All 25 [literal cases](../examples/probes/text-callframe-cases.json), frozen before
implementation, passed the [test source](../tests/probes/backend/text_callframe_tests.rs)
compiled with Rust 1.93.0 and warnings denied. Successful Text cases check borrowed
pointer identity; every case checks that the complete input is unchanged.

These are bounded data-decoder tests. Generated native Text calls, hostile pointer
validity, output-buffer guarantees and performance have not been established.
The review was a separate same-maintainer pass, not independent reproduction.
