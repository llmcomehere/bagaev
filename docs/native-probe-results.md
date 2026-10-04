# Bounded native kernel observations

Recorded on October 4, 2026. This is an experimental typed-kernel slice,
separate from the L2/CPython beta and from a production native backend.
See [the contract](probes.md), [independent oracle](probe-oracle.md),
[frontend](../examples/probes/backend/rust/README.md),
[LLVM lowering](../examples/probes/backend/rust/LLVM.md), and
[ordinary C11 baseline](../examples/comparison/pure/native/README.md).

## Observed profile

Linux x86_64, baseline x86-64 CPU target, Rust 1.93.0 (Rust2021/std only),
LLVM/Clang 21.1.8, and the system C ABI. Rust harnesses were built at O0.
The native kernel artifacts used O0, O2 and Os without LTO. All test data
was synthetic and frozen before implementation. No model calls were made.

- Frontend harness: 18 tests passed.
- LLVM emitter harness: 12 tests passed.
- Native caller library harness: 10 tests passed. This excludes a real linked
  call through the Rust caller's unsafe FFI path.
- The 40 harness test invocations include the shared SHA-256 known-answer
  regression once in each harness; they are not 40 independent properties.
- Fixture preparation: 13 tests passed, covering 48 named kernel cases and
  51 ordered stages. Publication fault checks in this harness were mocked.
- Frontend CLI: 49 JSON invocation stages checked. The 26 static refusals
  matched exact canonical result bytes; 23 valid outputs had the expected
  checked-invocation schema. The latter is not a runtime result or a complete
  independent validation of every intermediate-artifact field.
- Native execution: 25 fixed program/ABI variants, two implementations
  (handwritten C11 and generated LLVM), three optimization modes, and two
  output-buffer prefills: **300 complete ABI observations matched** the
  independently frozen expected 32 bytes. All 64 input bytes were preserved.

The native run covers signed endpoints, arithmetic/comparisons, scoped bindings,
function calls, zero/max loops, lazy arms, arithmetic overflow, first-failure
order, both semantic work-boundary variants, and invalid/valid argument slots.
The 25 variants include one ordered lazy after-stage and two ABI-only inputs;
these are not 25 new independently sampled programs.

The LLVM library was observed through a small read-only-input/stdout adapter,
then the emitted modules were compiled and linked with the ordinary C byte
observer. The existing file CLI's /out publication path was not exercised.
Each fixed entry was compiled separately and invoked once per observation.
Exact bytes, exit status, mode, input/prefill and artifact identity were retained.
A separate same-maintainer checking pass re-read the result captures. This is
self-review, not a new independent review.

## Limits and remaining work

This does not establish full L2/L3 parity, Cranelift conformance, the forms/context
profiles, AP1 effects/persistence/recovery, a production compiler choice, a native
Rust caller's real-object safety, or the complete 128-case/40-mutation protocol.
No actual compiler/interpreter mutants were executed. No general correctness,
performance, memory-efficiency, model-quality or cost advantage is claimed.

Tool installation and observation preparation required setup corrections;
an initial launch-path error and a recorder assumption about two literal
expectation records were corrected before the successful run. The frozen
inputs and expectations were not changed. Failed preparation is not a language
result and must be included if later whole-lifecycle costs are measured.

Compiler/build resource limits are separate from language semantic work.
This run does not certify the earlier host-specific isolation controls,
filesystem durability, hostile concurrent writers, or power-loss recovery.
The JSON summary records bounded counts and source identities; it is a report,
not execution authority or a replacement for inspecting code and outcomes.
