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

## Explicit data-reader CLI

`examples/probes/backend/rust/native_result_json11_main.rs` exposes the same
projection as a standalone Rust executable. In a separately authorized build
context, compile that file with Rust edition 2021; it has no package dependencies.
The data command is:

```
native_result_json11 --source program.json --source-pin sha256:HEX --wire result.bin
```

All three flags are required exactly once. `HEX` is the 64-character lowercase
canonical source digest already selected by the caller. The CLI checks that pin
before reading the result, then delegates to the accepted projection. Success
prints the JSON object and LF. A refusal exits 2, leaves stdout empty, and prints
`{"status":"refused","reason":"..."}` on stderr. `--help` alone prints usage.
No output file is created or overwritten. The CLI never launches processes,
loads kernels or evaluates the supplied source.

Inputs must be regular, non-symlink files at the initial file-kind check. Reads
are bounded to 1 MiB for source and 4,325,440 bytes for wire. These file checks
are not a race-free filesystem security boundary. The pin is a caller selection
check, not execution-origin authentication.

Fifteen bounded CLI observations passed: three existing captures across both
policies plus help, and eleven refusals (wrong/malformed pin, duplicate/unknown/
missing flags, malformed/unbound failure result, directory, symlink, and both
file-size limits). No generated kernel or measurement was involved.
