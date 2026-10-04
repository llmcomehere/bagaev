# Inferred source to LLVM data

Experimental envelope: `bagaev-typed-llvm-module/1`. This contract and the
reference identities below are frozen before its wrapper implementation.
The operation constructs inspectable bytes only. It does not invoke LLVM tools,
link an executable, load code, publish a file or grant execution authority.

## Inputs and order

Input is the complete bounded `bagaev-typed-scalar/1` source frame. Perform its
ordered source checking, inference and exact lowering, including final checking
by the unchanged scalar kernel checker. A source-language refusal is exactly the
existing `bagaev-typed-source-result/1` refusal wire. No module fields or partial
module are returned with a refusal.

For a valid source, call the existing pinned LLVM byte library on the complete
checked lowered program. Target, CPU, ABI and generated semantic work behavior
remain the frozen kernel's x86_64 Linux profile. This interface has no user flags,
optimization-mode selection, arbitrary backend path or target discovery.
Assembly/link optimization remains a separate explicitly admitted step.

## Exact module variant

The successful envelope has exactly:

- `schema`: `bagaev-typed-llvm-module/1`;
- `kind`: `module`;
- `source_pin`: canonical inferred-source identity;
- `lowered_pin`: the existing lowered-kernel identity;
- `llvm_ir`: a JSON string preserving every generated LLVM-text byte;
- `module_record`: the existing complete `bagaev-probe-llvm-module/1` object;
- `execution_admission`: false.

The module record is the LLVM library's existing record, without its outer LF
when embedded as an object. It retains module byte count, artifact pin, full
binding descriptor and binding pin. Its bound program and program pin must be
the exact checked lowering. The artifact pin hashes the LLVM-text bytes, not the
JSON-escaped string spelling. Source, lowered-program and module identities are
different objects and must not be substituted for one another.

Wire representation is canonical JSON plus one LF. LLVM text must be valid UTF-8;
encoding failure, LLVM bounds/interface failure or output construction failure
is an environment failure, never a source refusal or truncated success.
The complete envelope limit is 64 MiB. The existing LLVM library limits remain
8 MiB for module text and 2 MiB for the binding record. JSON string encoding can
expand each input byte by at most six, so these payloads plus fixed envelope
fields fit below 64 MiB. This bound is not an aggregate process-memory claim.

## Authority and I/O boundary

Returning a module does not certify safe or correct native execution, available
dependencies, a matching compiled binary, ownership of output directories or
permission to run a compiler. The receiving caller must independently enforce
its build/execution profile and retain exact source, toolchain and artifact pins.
No commands in data are executed. An input or output field cannot select a
compiler, shell, plugin or native library.

An optional CLI may expose `emit-llvm --input FILE` through the existing bounded
read-only source CLI, returning the envelope on stdout. It must not change the
older `/out` file publisher or claim that stdout generation tested that
publisher's write/flush/sync behavior. No new file-creation path is included.

## Pre-wrapper reference identities

[Reference cases](../examples/probes/typed-llvm-envelope-reference.json) cover the
same 43 pinned source cases: 12 valid modules and 31 unchanged source refusals.
For valid cases, source/lowered pins come from the earlier source fixtures.
Module and record hashes were captured from the existing pinned LLVM byte
library on those expected lowered programs before a new envelope wrapper existed.
These are shared-backend integration references, not an independent semantic
oracle or native-execution result. Module text hashes include every LLVM byte;
record hashes use its canonical JSON plus LF.

Tests must check exact envelope keys, canonical wire bytes, source/lowered pins,
module byte count/hash and complete record hash. The complete descriptor must
still bind the expected lowered program. Compilation and native conformance are
separate evidence; emitting a matching string does not replace those checks.

## Bounded wrapper implementation

The Rust typed-source CLI now exposes `emit-llvm --input FILE`. It uses the same
bounded input reader and returns only the canonical envelope on stdout. The
source library provides `emit_llvm_source`; the old kernel and LLVM backend are
unchanged. Source refusals reuse the existing exact result serializer.

The [explicit fixture runner](../tests/probes/typed_llvm_contract.py) matched all
43 pre-frozen references: 12 complete module identities and 31 exact refusals.
The earlier 43 source wires and 589 source-location wires also passed with the
same binary; Rust 1.93.0 compiled it with warnings denied. See the
[observations](../examples/probes/typed-llvm-observations.json).

This is a separate same-maintainer checking pass. It does not add independent
review, a native execution experiment, compiler performance evidence, production
isolation or coverage of the original file publisher.

## Concrete negative controls

Five separately copied envelope mutants were detected on the fixed
`S-LOCAL-INT` witness: substituted source pin, substituted lowered pin, an extra
LLVM-text byte, an incorrect admission flag and a wrong schema. Each produced
a complete JSON wire different from the pre-mutation reference. Compiler
failures, timeouts and crashes were not counted as detections. The admission
flag remained untrusted data and never authorized an action.

The [exact edits and output hashes](../examples/probes/typed-llvm-mutation-observations.json)
record this finite checking pass. Production source was unchanged; these five
mutants do not prove complete defect detection, independent semantic correctness
or native execution conformance.
