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
Rust edition2021, warnings denied and `--test-threads=1`. The original library slice adds no CLI; the command below adds no
workflow, execution admission, dependency or default profile selection.

## Explicit data-reader command

The subsequent CLI slice adds `native_result_json12_main.rs`, built separately
with Rust edition2021 and warnings denied. Its command is:

```
native_result_json12 --source program.json --source-pin sha256:HEX --wire result.bin
```

The three flags occur exactly once; `--help` alone is the only alternative.
Source and wire are bounded regular, non-symlink files (1MiB and4,325,440bytes).
The caller-selected lowercase64-hex source pin is checked before reading wire.
Success prints JSON plus LF. Refusal exits2, leaves stdout empty and prints a
fixed JSON reason on stderr. The command creates no files and runs no source,
process or kernel. File-kind checks are not race-free filesystem isolation.

All16 frozen command observations passed: three prior success captures plus
help; twelve refusals cover wrong/malformed pins, repeated/unknown/missing flags,
malformed/unbound wire, directory, symlink, both file-size limits and old11 source.
These are data-reader checks, not new native executions. The observations file
includes this separate CLI evidence; the original library observations remain.

## Focused successor consumer

The connected route is explicit [form6 authoring](json-bool-authoring.md),
focused replacement/export, lossless argument preparation, separately admitted
[prepared native12 execution](probe-prepared-native12.md), then this data reader.
Pass the complete canonical successor JSON source and its pin, not the readable
form or the original programme. Each execution still needs its own admission;
neither the detached draft nor the captured wire grants that authority.

After integration on 2026-10-11, the unchanged reader was rebuilt and applied
to all184 previously captured focused-successor wires (23 cases, two compiler
options, two fills and two repeats). It preserved168 full successful values,
work and successor pins and refused16 unbound failures. Two additional controls
refused an original-source/successor-wire mismatch and a successor-source/old-pin
mismatch; the latter refused before reading a deliberately absent wire file.
The pre-existing pinned oracle was unchanged. This pass made zero native or
reference calls and adds no semantic cases or performance evidence.

Fresh integration regressions also passed17 Rust tests across four selected
reference/native/consumer suites and24 Python tests across six form6 suites.
These are selected checks, not a full repository test run or independent review.
