# Native typed Text execution proposal

The generated LLVM kernel is implemented and bounded observations are recorded.
The experimental outer adapter is implemented for valid caller-owned buffers. It does not change
old scalar ABI or grant execution admission. The existing typed Text source and
invocation contract remains authoritative for types, evaluation order, work,
first-error semantics and source locations.

## Two boundaries

1. A reviewed native adapter validates the entire 8272-byte call-frame using the
   portable decoder, using the entry signature from the exact checked program.
2. Only after successful admission, the adapter passes eight internal value
   slots to a generated kernel. Each slot is 32 bytes, aligned to 8: Int64/Bool
   scalar at offset 0, Text byte pointer at 8, byte length at 16, scalar count at
   24. Scalar unused fields and inactive slots are zero. Text scalar field is 0.
   This internal representation is local to one admitted process, not transport.

The adapter owns and keeps the input frame alive and immutable throughout the
call. Literal bytes are immutable generated globals, and Text values in locals,
loop accumulators and internal function returns are borrowed from either those
globals or the current input. No Text can escape the entry result or be saved
across calls. No allocation, host callback, I/O, threading or external capability
is available to generated kernels.

## Output and caller obligations

The new outer symbol is `bagaev_text_probe_entry`; the existing scalar symbol is
not reused. Caller-owned input and output regions must be valid for the complete
call, disjoint, and correctly sized/aligned. A byte-slice decoder cannot establish
raw pointer validity. The admitted harness, not candidate input, establishes
these obligations. An eventual public general-purpose FFI would need its own
review and is not supplied by this experiment.

Output uses a fully initialized 32-byte little-endian record for comparison:
status u32@0, value_type u32@4, value i64@8, work u64@16, reason u32@24,
location u32@28. Success: status0, type1 Int64/type2 Bool, reason/location0.
Overflow: status1/reason9. Work limit: status2/reason10. Runtime failure has type
and value0, exact accumulated work and one-based structural node ID. The source
map for the exact checked program resolves that ID to an invocation pointer.
Admission refusal: status3/reason8, type/value/work0, location `0x80000000 + offset`
where offset is the decoder's first error byte. Detailed call-frame refusal
category remains available from the portable decoder, not encoded redundantly.

Every output byte must be written for each valid admitted call, regardless of
prior output contents. The complete input must remain unchanged. The adapter
must not call the kernel on an admission refusal. Language work starts at0 after
admission, counts unit entry ticks before operands, and reserves Text byte costs
atomically in the same order as the reference interpreter.

## LLVM lowering

Use LLVM21 x86-64 baseline. Represent internal Text as `{ptr,i64,i64}` and scalars
as i64. Use checked signed arithmetic intrinsics, explicit lazy branches and
bounded loops, entry-allocated typed locals, and scalar-value lexicographic Text
comparison via strict UTF-8 byte order. Carry shared work/status/location through
internal function calls; failure propagates without evaluating later operands.
All literals use hex byte escaping, never raw source interpolation. Module and
binding sizes remain bounded. The generated data descriptor pins exact source,
signature, ABI revision and output mapping; it never supplies authority.

## Acceptance before claims

Reuse the pre-frozen complete invocation results for every valid program and
argument case. Static/argument refusals stay checked before native compilation.
Exercise O0/O2, distinct output prefills, full output bytes, full input retention,
Text helper/loop/lazy/overflow/exact-work boundaries and call-frame refusals.
Compare against literal expectations, not just interpreter agreement. Mutations
must produce complete wrong results and be detected. Report build failure,
NOT_RUN, profile refusal and mismatch distinctly; no performance claim from
conformance, compiler success or work counters.

## Bounded observations and reproduction inputs

The [emitter](../examples/probes/backend/rust/text_llvm.rs) returns data bytes
only. It accepts a checked Text program; the source checker exposes a checked
constructor and read-only structural accessors, with no unchecked constructor.
The [comparison helper](../examples/probes/backend/rust/text_compare.ll) is
embedded as fixed LLVM text. The old scalar emitter and ABI are unchanged.

All 19 valid-program/argument cases selected from the pre-frozen invocation
fixture were mapped to [literal 32-byte expectations](../examples/probes/text-native-cases.json)
before native implementation. Structural node IDs use sorted function names
and expression preorder. The 7 static/argument refusals are not native runs.

The admitted Rust call-frame harness linked generated LLVM objects at O0 and O2,
then ran each with output prefilled 0 and 165. All 76 complete outputs matched
the literal expectations and all complete input frames were unchanged. See
[observations](../examples/probes/text-native-observations.json). No timing
measurement or native outer-adapter admission result is inferred from this.

The [harness template](../tests/probes/backend/text_native_harness.rs.in) is
build input, not an automatically executable test. Under a separately admitted
profile, substitute the two module paths and the exact checked entry signature
(`Type::Int64`, `Type::Bool`, `Type::Text` in order); do not derive it from a
candidate call frame. Obtain a checked program using `typed_text::checked_program`,
then `text_llvm::emit_program`. Compile the returned LLVM with LLVM21 `-c -x ir
-O0` or `-O2`; compile the instantiated Rust harness using edition2021 and warnings
denied, linking that exact object. Supply the literal call frame and prefill
byte as its two arguments. Compare all stdout bytes to the frozen native hex.
The template and source paths convey no permission to run compilers or artifacts.

The evidence is a same-maintainer bounded probe. Full source conformance, adversarial pointer validation, negative native
controls and production isolation remain open.

## Experimental outer adapter

The [adapter](../examples/probes/backend/rust/text_native_adapter.rs) validates
call frames before dispatch and constructs initialized internal value slots. Its
unsafe interface requires an already admitted, exact-signature kernel. The
[outer entry template](../tests/probes/backend/text_native_entry.rs.in) fixes the
signature and kernel at build time, exports `bagaev_text_probe_entry`, and writes
the complete output record. The caller must still supply valid disjoint buffers;
no test attempts arbitrary invalid addresses or establishes general FFI safety.

The outer entry passed the same 76 valid-frame native output comparisons with
input preservation, reusing the exact already compiled LLVM objects. A separate
single-test [admission harness](../tests/probes/backend/text_native_adapter_tests.rs)
covers all 25 frozen call-frame cases with a counting witness kernel: rejected
frames produced the exact refusal record with zero calls, and admitted frames
called once. This checks dispatch refusal, not 25 additional program semantics.
See [adapter observations](../examples/probes/text-native-adapter-observations.json).

## Native negative controls

Six concrete emitter/helper mutations were detected in 24 native observations
(O0/O2, both output prefills): free literals, XOR instead of sum for comparison
charge, byte length substituted for scalar length, reversed byte order, an
over-strict work limit, and partial failed reservation. All generated witnesses
exited normally with complete wrong output records and preserved input frames.
Failed builds, crashes and timeouts did not count. Exact edits and expected/actual
bytes are retained in [mutation observations](../examples/probes/text-native-mutation-observations.json).
The original emitter/helper and frozen expectations were unchanged. This finite
same-maintainer pass does not prove detection of arbitrary defects.
