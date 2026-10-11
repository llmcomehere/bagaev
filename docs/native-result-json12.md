# Explicit profile12 native success JSON

`examples/probes/backend/rust/native_result_json_v12.rs` adds the data-only
`decode_success(source_bytes, wire_bytes)` boundary for explicit profile12
all-Json or zero-argument sources. It returns owned UTF-8 JSON with schema
`bagaev-native-result/12`, source_pin, work and value. It never evaluates the
source or dispatches a kernel. The profile11 API and CLI remain unchanged;
changing a source header is not migration.

The existing BCMPRES4 decoder validates the complete wire and exact nominal
result graph before projection. Record fields, optional omission, text escaping,
list order and variant case/value follow the existing
[profile11 projection rules](native-result-json11.md). Existing wire bounds and
the32MiB output bound remain. No partial JSON is returned on refusal.

Source binding is consistency, not authentication or proof that a kernel
produced the value. Synthetic structurally valid values can pass even when they
differ from source evaluation. Unbound32-byte runtime failure packets refuse;
this reader must not silently assign them to the supplied source.

## Bounded evidence, 2026-10-11

Five serial Rust tests passed with warnings denied, including SHA known answers.
Controls cover primitive/optional/text-list values, omitted fields, Unicode/JSON
escaping, malformed text, explicit12 output, old11 refusal, wrong source binding,
unbound failure refusal and Boolean-projection sources with both payloads.
The unchanged profile11 reader also freshly passed its four serial tests.

Data-only replay of the188 previously captured native12 wires projected176
successes to their exact prior business values, work and source pins. All12
unbound failure captures refused with empty stdout. These reuse47 existing
semantic cases across optimization/fill controls; no new native or reference
execution occurred. [Projection observations](../examples/probes/record-json-bool/result-json12-observations.json)
record prior wire hashes and projection outcomes. They do not establish
independent reproduction, performance, provenance or production acceptance.

A separately authorized build can run `native_result_json12_tests.rs` with
Rust edition2021, warnings denied and `--test-threads=1`. This slice adds no CLI,
workflow, execution admission, dependency or default profile selection.
