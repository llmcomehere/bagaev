# Data-only LLVM preparation for pure profile 11

The separate `json_native_emit11.rs` entrypoint accepts exactly checked
`bagaev-typed-record-invocation/11` data. It emits LLVM text or a binding descriptor.
It does not compile, link or execute the emitted module.

The entry signature must have zero or only Json parameters; its result cannot be
Json. Internal functions can use the existing supported typed values. The new
symbol is `bagaev_json_view11_kernel`, with descriptor schemas
`bagaev-json-view11-llvm-binding/1` and `bagaev-json-view11-llvm-module/1`.
Older emitters and their schemas remain unchanged and refuse profile 11.

The implementation uses the existing checked profile 11, including record-list
capacity 16 and combined shape/work bounds. LLVM target and CPU remain
x86_64-unknown-linux-gnu / x86-64. Text and Cell arenas remain 65,536 units;
module and binding limits remain 8 MiB and 2 MiB. No host execution profile,
resource policy, source authority or dependency is changed.

## Binding and qualification

Each descriptor binds the exact canonical checked source, binding bytes and
emitted module bytes with the existing `sha256:`-prefixed identities. The binding
retains `execution_admission: false`. A matching hash is identity, not permission.

Own reviewed emitter sources were compiled with Rust edition 2021 and warnings
denied under an existing bounded build profile. A zero-argument sixteen-item sum
and the wider catalogue produced deterministic modules and bindings. Twelve
data-tool calls covered repeated emission, all source/binding/artifact hash
links, old-emitter rejection and unsupported entry/schema rejection. A portable
repeat passed. The first checker compared prefixed identities to bare hex;
only that comparison was corrected, and the original failure was retained.

Use `tests/probes/native_wide_emitter_checks.py` with explicit emitter/legacy
paths, their SHA-256 hashes and a new absolute output directory, only after
establishing execution permission independently. The legacy binary is the /10
emitter. This check executes the data emitters, never generated native code.

## Open native boundary

Generated modules have not yet been compiled or executed in this qualification.
The two emitted artifacts and their hash consistency do not demonstrate native
semantic conformance, performance or runtime readiness. A separately versioned
output graph/exporter and exact-kernel adapter must be paired and checked before
native execution results can be claimed. Existing /10 adapters must not be
reused with the new binding or symbol. Existing pure reference /11 observations
remain separate evidence.

A [separate profile11 owned output boundary](probe-native-wide-wire.md) is now
qualified with initialized data only. It does not complete kernel execution.
