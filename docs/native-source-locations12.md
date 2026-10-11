# Checked profile12 nodes and readable ranges

The explicit data reader
[json_source_locations12.rs](../examples/probes/backend/rust/json_source_locations12.rs)
checks a Json-only invocation12 and maps node IDs to programme pointers. Build
it separately with Rust edition2021 and warnings denied after reviewing source
and execution scope. Its modes are:

    locations12 locations --input invocation.json --source-pin sha256:EXPECTED
    locations12 locate --input invocation.json --source-pin sha256:EXPECTED --node 1

The report retains bagaev-native-source-locations/1 with explicit profile
bagaev-typed-record/12. It includes checked source pin, complete node count and
either all rows or the selected row. IDs are one-based checked-IR IDs; rows
carry function, programme pointer, operation and type category. Old11 reader
bytes and selection are unchanged. Source checking never evaluates the programme.

To join the [form6 source map](json-bool-authoring.md), require equal checked
source_pin and map program_pin, then match program_pointer. Readable byte and
line/column ranges belong to the exact source layout hash. Never use map array
position as a node ID. Unbound native failure packets supply no authenticated
source: this tool can explain a claimed node under the chosen source only.
The [original inspector bounds](native-source-locations.md#bounds-and-checks)
remain: bounded regular input, complete bounded output before writing, explicit
pin/node/profile/argument refusals, no race-free filesystem or provenance claim.

On2026-10-11 three serial Rust tests passed, including inherited SHA known
answers. Literal expected rows cover root json.bool_or, Json argument and Bool
fallback, complete/selected output equality, unchanged mapping across argument
values, wrong pins/nodes, valid old11 source refusal and malformed argument shape.
Twelve further data CLI calls checked complete maps and selected first/last rows
for a three-node literal and the93-node active-total application, plus wrong-pin,
zero-node and out-of-range refusals. Every node joined the existing readable map
under the same source pin. These are two selected sources, not universal mapping
proof. No programme/reference evaluation, native execution or measurement ran.

Capability revision6 remains pinned to its earlier conservative metadata and
does not list this subsequent inspector. Select this file explicitly; it does
not alter defaults or authorize a native kernel.
