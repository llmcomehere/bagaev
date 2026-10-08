# Explicit profile11 native-call boundary

`json_native_adapter_v11.rs` pairs the checked profile11 Json invocation with the
[separate wide output graph/wire](probe-native-wide-wire.md). Older adapters remain
unchanged. This is an unsafe library boundary, not a launcher or artifact loader.

Before calling the supplied function pointer, the adapter checks the exact
source profile, Json-only entry arguments, result graph and exact scratch lengths.
The sealed input owner lives through the synchronous call. The adapter initializes
output metadata, invokes once, rechecks scratch bases/capacities/used lengths,
and exports owned bytes before releasing input owners.

The caller must separately admit that exact source, signature, kernel and result
contract. Binding bytes are caller-supplied and copied into the owned result;
this API does not authenticate them or turn them into execution permission.
Shape checks cannot establish the safety or semantics of an arbitrary pointer.
The kernel must respect live disjoint storage, initialize reachable outputs,
retain no pointers and never unwind. Host execution profiles are unchanged.

## Controlled boundary observations

A constant sixteen-record source and complete expected wire were frozen before
implementation. Its 33 expression-node ticks are reflected in the expected work
field. The qualification uses reviewed Rust callbacks, not generated LLVM code.
A controlled callback builds sixteen records in the first 32 owned scratch cells.
Two different dirty scratch fills produce the same complete 1,120-byte output,
which remains readable after scratch owners are dropped.

Short scratch and an old source schema refuse before callback invocation.
Controlled callbacks with a changed arena capacity or oversized output list are
detected afterward as NATIVE_ARENA and NATIVE_VALUE. Four callback calls occurred:
two successful fills and two invalid-output controls. Four refusals passed.
A test-only counter observes calls and is not part of the language program.

`native_wide_adapter_check.rs` was built with Rust edition 2021 and warnings denied
and run under the existing bounded profile. This establishes the selected adapter
and ownership observations only. No generated LLVM kernel was compiled or called;
full native semantic qualification, performance and independent reproduction
remain open. The LLVM preparation and owned-wire checks are separate evidence.
