# Prepared Json native boundary, profile 11

`examples/probes/backend/rust/prepared_json_native_v11.rs` adds an explicit
source-once adapter alongside the unchanged full-invocation and profile 10 APIs.
`prepare` owns the checked source, nominal result definitions and canonical source
binding. `evaluate` accepts changing argument-array bytes and returns owned
BCMPRES4 output. There is no implicit cache or process launcher.

Every call checks the supplied source binding, prepares owned Json arguments,
rechecks the actual text/cell scratch lengths and result graph, resets arenas and
output, invokes the kernel once, checks arena metadata and exports the result.
Argument envelope limits come from the prepared reference 11 API. Typed entry
parameters and Json entry results remain unsupported.

## Safety boundary

Evaluation is unsafe. The caller must separately admit the exact native kernel
for the source, result graph and binding. Inputs and scratch/output must be live
and disjoint; the kernel must respect all bounds, initialize reachable output,
preserve immutable input, retain no pointers and never unwind. Neither a digest,
a matching shape nor a prepared handle authenticates or admits arbitrary code.
The adapter cannot validate arbitrary pointers supplied by a malicious kernel.

## Observed conformance

The original 32 and total-10 40 frozen batch cases were replayed using previously
qualified linked kernels, each at LLVM O0/O2 and output prefills 90/165. Eight
processes prepared their source once and made 288 sequential native calls with
changing arguments. Every complete BCMPRES4 byte sequence matched the prior
full-invocation capture, including source binding, work and full returned value.
Input snapshots, scratch guards and untouched tails were checked each call.

Three Rust tests (including SHA-256 known answers) passed. A reviewed fixed
constant-zero callback executed once as a sanity check; six refusal calls made
zero additional dispatches: wrong source binding, malformed arguments, wrong
arity, non-array arguments and short text/cell storage. Three preparation
refusals cover profile 10, typed entry and Json result. An initial negative-test
expectation incorrectly expected the Json result to reach interface conversion;
it was corrected to the exact existing frontend Type refusal at
`/functions/main/result`. Production behavior was unchanged by that correction.

The portable Python test verifies capture framing and fixture/source hashes.
It does not execute native code. These are conformance observations, not timing,
memory, safety proof, model quality or adoption measurements. CI source checks
are separate from the bounded native runs described here.
