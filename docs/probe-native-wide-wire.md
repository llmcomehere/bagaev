# Separate profile11 owned output wire

This data boundary pairs with [profile11 LLVM preparation](probe-native-wide-emitter.md).
It does not select or invoke a kernel. The three new modules are
`variant_admission_v11.rs`, `composite_export_v11.rs` and
`composite_result_decode_v11.rs`.

The checked graph accepts nominal record-list capacities 0–16 through the
existing wide type-graph checker. Older admission remains 0–4. Named type count,
field counts, cycles, expanded shape, scratch and input-cell bounds are retained.
A checked graph validates data; it does not grant source or execution authority.

Success bytes start with `BCMPRES4`. The existing header/node layout is retained:
64-byte header, 32-byte nodes, at most 4,096 nodes and 4 MiB of text, exact binding
bytes and at most 65,536 work units. Old /10 success bytes use `BCMPRES3`; each
reader refuses the other's magic. This new reader does not silently broaden old
wire acceptance. Language failures retain the separately scoped 32-byte metadata
and existing allowed status/reason pairs. Arena/environment failure is not a
successful result or ordinary language refusal.

## Ownership and safety

The exporter still has an unsafe live-descriptor contract. Every recursively
reached nonempty region must be aligned, initialized, readable and alive for the
call, with no concurrent mutation. Bounds checks do not prove pointer ownership.
The caller must separately bind the exact admitted source and kernel. Exported
bytes own their data and can be checked after all descriptor owners are dropped.
No broader pointer or artifact authority is implied by this module.

## Qualification performed

Before implementation, a complete literal wire was frozen for sixteen one-field
records containing integers 0 through 15, work 7, and a 32-byte binding filled
with byte value 42. The exported 1,120 bytes matched exactly: 33 nodes including
the root list. The owned reader then accepted those bytes after the original
vectors were destroyed.

Twelve refusal observations covered capacity 17, unchanged old capacity 4,
cycles, expanded shape, output metadata/length, forged wire binding/count/magic,
arena status and inactive failure metadata. An empty old-format success and a
valid language-failure metadata record remained accepted by their scoped paths.
The Rust qualification source `native_wide_wire_check.rs` was built with edition
2021 and warnings denied and run under the existing bounded profile. Its first
compile omitted the existing transport module declaration and failed before
execution; adding that declaration fixed the qualification crate without
changing implementation or expected bytes.

These are own initialized-data export/decoder checks. No generated LLVM kernel
was compiled or called. Native language conformance still requires the separately
versioned exact-kernel adapter and compiler/runtime qualification. Independent
reproduction, performance and production readiness are not established.
