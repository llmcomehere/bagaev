# Read native success results as JSON

`examples/probes/backend/rust/native_result_json_v11.rs` provides the data-only
`decode_success(source_bytes, wire_bytes)` function. It returns owned UTF-8 JSON:

```
{"schema":"bagaev-native-result/11","source_pin":"sha256:...","work":7,"value":...}
```

Supply explicit profile 11 source with all-Json or zero entry parameters and
its BCMPRES4 success bytes. The library prepares the source without evaluating
it, derives its nominal result graph, and validates the complete wire using
`composite_result_decode_v11` before reading values. Records get checked field
names; lists retain order; variants use `case` and `value`. Absent optional
`omit_none` fields are omitted just as in the reference renderer. Other absent
OptionInt64 values become JSON null. Text is scalar UTF-8 with JSON escaping.

No kernel, process or source program is executed. There is no unsafe code in
the projection. Existing wire limits apply: up to 4096 nodes, 4 MiB text pool,
work at most 65536, exact nominal shape/source binding, zero reserved bytes,
and complete consumption. Returned JSON is bounded to 32 MiB; refusal returns
no partial result. Existing source, reference and native ABI behavior is unchanged.

The source digest establishes byte consistency, not origin authentication or
proof that this source produced a supplied value. A fabricated but well-formed
wire can pass these structural checks. Execution provenance remains external.
The unbound 32-byte runtime-failure packet is deliberately rejected: it contains
no source digest and must not be silently attributed to the supplied source.

## Checked observations

72 existing original/total-10 batch wire captures projected to their complete
frozen business values, exact work and source binding. Fourteen malformed or
unsupported packets refused with no JSON output, covering short/unbound failure,
trailing data, magic, counts, pool/work bounds, binding, reserved bytes, nominal
identity and child layout. Four serial Rust tests (including SHA known answers)
cover primitive values, optional omission, Unicode/JSON escaping, text lists and
three malformed-text controls. No generated kernel was run for projection.

These checks establish bounded data conversion, not performance, memory usage,
semantic execution provenance or adoption. Native conformance is documented in
[the prepared native guide](prepared-json11-native.md).
