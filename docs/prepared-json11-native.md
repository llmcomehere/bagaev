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

## Reused scratch and retained results

A subsequent bounded qualification reused the same guarded scratch addresses
for the entire forward/reverse case sequence, refilling the buffers before each
call. The input source bytes were overwritten and released after preparation.
Callback entry checked zeroed work/output metadata and arena used counters.
All returned byte vectors were retained; after overwriting and releasing scratch,
argument bytes and the prepared source, their hashes were checked again.

This made 576 business calls across eight processes, with exact prior wire
matches. Four already qualified runtime failures (add overflow, subtract
underflow, empty index and push seventeenth) were each repeated twice under both
optimizations and prefills, adding 32 calls. Their complete 32-byte failure
outputs, including work and node location, matched the frozen observations.
Work-limit failure is not included in this native replay. The production
adapter was unchanged. This is bounded conformance, not a memory-safety proof.

The data-only `tests/probes/backend/prepared_native11_reuse.rs.in` template
preserves the qualification checks. Fill the existing source/binding/backend
markers, `EXPECTED_CALLS` (64/80 for the business sequences, 2 for a repeated
failure), and a declaration of `EXPECTED_FAILURE` as an empty byte slice for
success or the frozen 32-byte failure. Input is the argument-array JSONL file;
output is a sequence of little-endian u32 lengths and owned wire bytes. Rendering
or inspecting this template does not authorize compiling or executing it.

The final published template was rendered and replayed for all 24 processes
(608 additional calls); every output capture was byte-identical to the first
reuse qualification. These repeated calls add no new semantic cases.

Consumers can use the separate [data-only JSON projection](native-result-json11.md)
to read validated success bytes without executing a kernel or hand-decoding the
nominal result tree. Unbound failure packets require a different provenance path.
