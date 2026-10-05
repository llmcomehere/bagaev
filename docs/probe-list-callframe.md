# Separate native-list byte frame, revision 1
Frozen before implementation, 2026-10-05. Data decoder only; no kernel calls or execution authority.

Frame length 37,008 bytes; magic BTXTIN3 followed by NUL; u32le argument count at 8;
zero bytes 12..15. Eight slots each 4,624 bytes, beginning 16. Slot has u32le tag,
u32le length,4616 payload bytes. Tags1 Int64(length8),2 Bool(length1),3 Text
(length0..1024),4 OptionInt64(length16),5 TextList(length 4,616). Earlier v1/v2
frames remain unchanged and are refused by v3. Signature comes from checked
source, max8 arguments, count must match.

TextList payload: u32le item count at 0, max 64; bytes 4..7 zero;64 descriptors
(offset u32le,length u32le) at 8; byte pool of 4,096 at 520. Offsets are relative to
pool and must equal cumulative lengths of preceding entries, including empty
entries. Each length <=1024, cumulative end<=4096; each slice valid existing Text
(UTF8 <=256 scalars). No normalization, duplicates/NUL retained, no pointers in
input. Inactive descriptor bytes and unused pool tail must be zero.

First refusal order: frame size, first bad magic byte, signature length, count,
header reserved bytes; then each slot in order. Inactive slot: first nonzero
byte UNUSED. Active slot: tag, length, value validation, first nonzero trailing
slot padding. List validation order: count LIST_COUNT at payload 0; first bad
reserved byte LIST_RESERVED; then each active descriptor: offset LIST_OFFSET at
descriptor start, length LIST_LENGTH at descriptor+4, cumulative bound LIST_BYTES
at descriptor+4, Text validation LIST_TEXT at pool+offset. Only then inactive
descriptors first nonzero LIST_UNUSED; then unused pool first nonzero
LIST_PADDING. Other scalar errors preserve names and relative offset policy of
option_callframe. Returned offset always absolute frame byte offset.

Values borrow immutable frame bytes. Decoder returns owned fixed-capacity
containers of Text descriptors, no heap or unsafe. This is not the native
invocation arena nor a promise of arbitrary-pointer safety. Decoder has no
function pointer and does not execute a program. Success is data conformance,
not kernel admission, application correctness or performance evidence.

## Bounded observations

Twenty cases were frozen before implementation; eight supplemental cases were
specified after implementation and before their checks. All28 passed in the
recorded profile. Four concrete unit mutants were detected by named expected-
result assertions. These are data-decoder observations, not generated list
kernel conformance. Review was a separate same-maintainer pass.
