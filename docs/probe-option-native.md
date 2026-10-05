# Native optional Int64 probe boundary

This is a separate experimental successor to the Text native probe. Preserve its
valid-buffer/disjointness, static checked-signature, borrowed Text lifetime,
source-map, full output, work and error requirements. Existing scalar/Text
symbols and call-frame formats are unchanged.

The new input frame keeps 8272 bytes and the same header/8x1032-byte slots, but
uses magic `BTXTIN2\0`. Tags1/2/3 retain Int64/Bool/Text and validation order.
Tag4 is OptionInt64 with length exactly16. Its payload must be the canonical
`bagaev-option-int64-value/1` value encoding. On payload refusal, report
`OPTION_VALUE` at slot+8+the optional-value decoder offset, before tail padding.
Argument count and tag must match the exact checked program signature. All
inactive slots and all bytes after active payloads remain zero.

Internal value descriptors stay32 bytes. For optional values, scalar@0 contains
the Int64 payload (zero for None), pointer@8 is null, length@16 is presence0/1,
and scalar_count@24 is0. This is a separately versioned internal interpretation,
not an extension silently applied to old Text kernels. Optional LLVM values are
`{i64 presence,i64 payload}`; None is bothzero. Only the new adapter constructs
entry descriptors, and source constructors preserve the invariant internally.

New symbols: generated `bagaev_option_kernel`, outer
`bagaev_option_probe_entry`. Output remains the same32-byte layout/code mapping,
with OI_ meaning at the JSON boundary. Kernel runtime locations are structural
node IDs of the new exact source; admission locations are 0x80000000+frame offset.
No optional value is exported as an entry result. Fallback lowering branches on
presence and evaluates the fallback only when absent, preserving ordered work.

Before implementation, derive literal native outputs from the 24 frozen source
cases for the17 valid-program/argument cases. Exercise O0/O2 and both output
prefills with full input preservation. Re-run the existing Text semantics after
explicit schema adaptation. Freeze new frame cases for None, Some(0), extrema,
wrong flag/padding/payload/length, old magic and refusal precedence. No arbitrary
pointer, performance, full application or production-isolation claim follows.

## Bounded implementation and observations

The [LLVM emitter](../examples/probes/backend/rust/option_llvm.rs),
[v2 call-frame decoder](../examples/probes/backend/rust/option_callframe.rs),
[adapter](../examples/probes/backend/rust/option_native_adapter.rs) and
[entry template](../tests/probes/backend/option_native_entry.rs.in) implement this
separate profile. All 17 [pre-frozen valid invocation cases](../examples/probes/option-native-cases.json)
matched complete native records at O0/O2 and both output prefills: 68 observations,
with input frames preserved. Another 34 [schema-adapted Text cases](../examples/probes/option-native-text-regression-cases.json)
matched 136 native records; these are regressions, not new independent oracles.

Twenty [new frame cases](../examples/probes/option-callframe-cases.json) and 25
explicit Text-frame adaptations passed 45 decoder tests. A separate admission
test repeats those 45 cases and checks no kernel dispatch on refusal, one call
on admission. Two initial generated test names collided; numeric prefixes fixed
the build preparation without changing candidate semantics or expectations.
See [observations](../examples/probes/option-native-observations.json).

This is bounded same-maintainer conformance, not arbitrary-pointer safety,
independent reproduction, production isolation, full language/application
acceptance or a measured advantage. Existing profiles and original fixtures
remain unchanged.
