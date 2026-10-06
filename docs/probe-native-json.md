# Experimental native JSON composition profile

This source slice adds `bagaev-json-view8-llvm/1` for the existing
[structured /8 source family](probe-record-source.md). It accepts Json-only entry
arguments and primitive or declared composite results. Json may flow through
helpers, locals and loops, but cannot be an entry result or named record/variant
payload. Mixed Json/non-Json entry signatures are explicitly unsupported.

The emitter produces deterministic LLVM and a source/module binding. It does not
compile, load or execute that output. A checked source, a digest and a parsed
invocation are data evidence; none authorizes running arbitrary native code.

## Data and native boundary

`CheckedJsonInvocation` is constructed by full invocation admission: the original
frame, source and argument graph are checked together. Raw JSON number tokens and
isolated surrogate code units are retained, rather than passed through the source
canonicalizer. Missing is an internal null view, distinct from a present JSON null.
The immutable codec owns stable node, entry and byte storage for the entire call.

The fixed x86-64 ABI uses Node80 and Entry24 descriptors. The raw JSON argument
pointer occupies the pointer word of NativeValue; all inactive words are zero.
The node stores generic kind/count, original integer-token work charge, a cached
integer projection and bounded scalar-text projection. Invalid scalar text keeps
kind=text and selects the lazy fallback. Non-scalar object keys remain counted
but cannot match a scalar literal key. Duplicate decoded keys are transport errors.

`json_native_adapter_v8` derives the output type graph from the checked source,
checks scratch capacities, creates immutable input views, calls one separately
admitted exact kernel, verifies arena identity/capacity/usage and exports owned
bytes before dropping any input owner. It never retries a kernel. Its unsafe
contract requires valid live extents, no concurrent mutation, no retained pointers,
no unwinding and a kernel bound to that exact source. Pointer shape checks cannot
establish these properties for arbitrary code.

The named compound graph remains bounded by eight definitions and 4096 logical
units. The /8 source has at most 32 functions and 2048 expression nodes; earlier
source schemas retain their previous limits. Logical work is capped at 65536.
The /8 exporter admits failure locations 1..2048; the older 512-location export
profile is unchanged. The detached BCMPRES1 form contains a 64-byte header,
preorder 32-byte nodes and an exact text pool. Nominal wire IDs cover records,
record lists and variants in that order. Optional None fields remain explicit in
the typed wire; the declared field metadata governs omission in structural JSON
extraction. No date or catalogue policy is hidden in the exporter.

## Reproduction surfaces

- `examples/probes/backend/rust/json_native_emit.rs`: data-only `emit --input FILE`
  and `binding --input FILE`, with bounded regular-file reads.
- `examples/probes/native-json/profile8-cases.json`: 25 parent fixtures promoted
  to /8 with fresh source bindings. These are compatibility replays, not 25 new
  independent scenarios.
- `tests/probes/backend/json_native_adapter_tests.rs.in`: admission/one-call/output
  marker tests. Substitute `{{BACKEND}}` with the reviewed backend source folder.
- `tests/probes/backend/catalog_native_harness.rs.in`: the exact catalogue harness
  template, linked only to its separately admitted generated kernel. Arguments
  are invocation file, scratch fill (90 or 165) and expected logical work.
- `tests/probes/native_catalog_wire.py`: data-only `request CASE` and
  `check CASE --output FILE`. For a chain successor, `request CASE --previous FILE`
  reads the actual checked predecessor result. It never compiles or executes code.

The catalogue harness is specific to the existing frozen catalogue program and
its declared result graph. It is not an arbitrary-kernel launcher. Compilation,
linking and execution need a separately reviewed bounded profile and trusted
compiler inputs. No workflow, installation or permission change is included.

## Evidence and limits

Local qualification used LLVM 21 and Rust 1.93.0 for the fixed Linux x86-64 target.
The unchanged [catalogue source](../examples/probes/catalog-source/program.json)
and [literal oracle](../examples/beta/catalog-cases.json) matched 99 complete
responses and four actual predecessor-fed chain steps at O0/O2 with fills 90/165:
412 native observations. Checks included complete wire bytes, source/module
bindings, recursive input preservation, dirty output, scratch guards/unused tails
and result ownership after input/scratch release. Seventeen prior source-level
negative controls also compiled and returned normal-exit, valid typed, wrong
application responses; the literal checks detected them.

Logical work matched the previous portable same-source receipts, with maximum
observed value 10190. This is differential semantic evidence, not an independent
work oracle, elapsed-time measurement or speedup. The 25 smaller fixtures, marker
checks and deliberate errors test additional boundaries; counts must not be added
as if repeated runs were independent application families.

The review was a separate pass by the same maintainer, not independent review.
These finite cases do not establish conformance for all abstract Python values,
whole-domain acceptance, memory/latency benefits or production suitability.
Frame, type, work and allocation limits remain part of the narrower native domain.

The existing exact-head `validate` CI checks documentation structure and links
using the trusted base validator. It does **not** run these native probes. Passing
that CI is source-integration evidence and must not be reported as a native run.
