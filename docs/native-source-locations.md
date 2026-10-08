# Checked source locations for profile11

The data-only Rust reader
[json_source_locations11.rs](../examples/probes/backend/rust/json_source_locations11.rs)
maps checked profile11 node IDs to source JSON pointers. It uses the existing
checked Json invocation frontend; it does not evaluate a programme, emit or
compile LLVM, load a library or invoke a native kernel.

Two modes are available after separately reviewing/building the reader:

    locations11 locations --input invocation.json --source-pin sha256:EXPECTED
    locations11 locate --input invocation.json --source-pin sha256:EXPECTED --node 7

The source pin must equal the checked canonical programme identity, such as the
source_pin in its native binding description. The invocation must use the exact
/11 schema and a zero-argument or Json-only entry. Existing frontend type,
argument and resource checks apply. No old profile is selected implicitly.

The bagaev-native-source-locations/1 report gives the total node count and all
locations, or one existing node. Each record includes:
- One-based node ID and owning function.
- Invocation-prefixed JSON pointer, for example /program/functions/main/body/5/5/5.
- Operation spelling.
- Type category. Record, RecordList and Variant are categories, not nominal names.

These are programme JSON pointers, not line/column ranges in a readable source
file. Record-form formatting can change text positions without changing the
programme identity. The report checks semantics through the existing frontend
but explicitly says program_executed=false, native_output_authenticated=false
and execution_admission=false.

## Failure attribution boundary

A 32-byte native language-failure record has no authenticated source binding.
This tool can map its claimed node under an explicitly selected checked source;
it cannot establish that the record actually came from that source or kernel.
The caller must separately bind the admitted source, artifact and result.
A matching digest identifies bytes and is not permission or authentication.

For the previously frozen work-limit source, node 7 is the innermost loop at
/program/functions/main/body/5/5/5. For the four earlier overflow/index/push
failure sources, node 1 is their root expression. These mappings are useful
diagnostic context without repeating the programme's execution.

## Bounds and checks

Input is a bounded regular file using the same stable-file checks as the existing
data emitter. Complete output is bounded to one MiB and constructed before stdout
is written. Wrong pins, absent/zero/out-of-range nodes, wrong profiles, invalid
source/signature/arguments and invalid modes refuse without a partial report.
The filesystem and executable remain separately trusted local inputs; no hostile
race or arbitrary native-pointer safety guarantee is added.

Six literal source/count/location expectations were frozen before implementation.
The reader built with Rust edition 2021 and warnings denied. Thirty-one data calls
checked six complete maps, six selected locations, six key-order permutations,
eleven refusal cases and two argument variants yielding the same source map.
No programme evaluation or native-kernel call occurred.
The [portable check](../tests/probes/native_source_locations_checks.py) takes an
explicit separately admitted --reader and --reader-sha256 plus a new --output
directory. Its observations include complete input/output bytes; the checker
itself grants no execution authority.

The portable run repeated the same 31-call suite; repetition adds no independent
cases. Existing frontend, reference and native emitter behavior is unchanged.

A separate [readable form5 source map](record-source-map.md) maps those programme
pointers to byte and line/column ranges after matching programme pins. It labels
coarse enclosing-expression ranges explicitly and does not perform semantic checks.
