# Candidate native12 Boolean projection

Status: source/data checks only. Generated LLVM compilation and generated-kernel
execution are NOT_RUN. This candidate is not accepted native12 support.

The [reference Boolean operation](record-json-bool-proposal.md) and
[JSON active-total application](json-active-total.md) already have finite reference
observations. The previous native input representation retained Boolean kind but
discarded true/false, so extending only the emitter would have been incorrect.

The additive input12 owner retains the80-byte Node and24-byte Entry layout.
The former reserved word at byte72 is Boolean payload0/1 for kind2; every other
kind has zero there. Old input and adapter modules are unchanged. A separate
invocation12 bridge rejects older checked profiles. This representation is for
owned, validated immutable inputs and is not an unchecked pointer admission API.

The candidate emitter12 accepts only checked profile12 Json entry parameters and
uses a distinct kernel symbol and module/binding schemas. Existing emitter11
still rejects profile12. json.bool_or charges the normal node/operand work,
checks kind2, reads the Boolean word or branches to a lazy fallback. No new
payload-byte charge is added. The generated fallback must remain control-dependent.

The separate unsafe adapter12 reuses the wide result graph and BCMPRES4 owned
wire format. It verifies the caller's source binding before dispatch. That check
does not authenticate or admit a function pointer: the caller must separately
establish exact source/module binding, ABI, live disjoint scratch, immutable input
preservation, complete initialized output and no retained pointers/unwinding.
Prepared/source-once profile11 APIs are unchanged; no prepared12 API is added.

## Actual checks on 2026-10-10

- Four input preparation tests passed: true/false payload, zero payload for other
  kinds, nested ownership/layout and input refusals. They execute no kernel.
- Three emitter/adapter test functions passed, including an inherited SHA256 test.
  One reviewed fixed zero-result callback executed once. Wrong source binding,
  old schema and undersized scratch refused before dispatch. This callback is
  not emitted LLVM and establishes no generated-kernel conformance.
- Rust1.93 edition2021 builds denied warnings for these tests and the emitter.
- Of the existing thirty Boolean/schema cases, twenty-four valid invocations
  emitted data and six invalid invocations refused. The JSON active-total source
  also emitted module/binding data with matching artifact digest.

Before acceptance: compile reviewed generated modules with the admitted LLVM
toolchain, check actual kernels at O0/O2 and two scratch fills, compare complete
values/work/refusal locations with reference, retain frozen application outcomes,
and verify input snapshots, scratch guards/tails and owned output. Keep separate
exact-head review and successful CI. No speed, cost or model-benefit claim follows
from the current source/data checks.
