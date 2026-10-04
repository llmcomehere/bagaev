# Fixed kernel LLVM source

`llvm.rs` lowers the complete accepted `CheckedProgram` through the read-only
interfaces in [ir.rs](ir.rs). `llvm_main.rs` is a separate Rust 2021, std-only
file CLI. The domain is exactly the typed kernel in
[the probe specification](../../../../docs/probes.md), not actual L2, a
general library bridge, a production backend or a JIT.
LLVM parsing, verification, compilation, linking, tests, native conformance and
comparative measurements require separate observed evidence. They are not
established by these sources.

## Pure library and lowering

`llvm::emit_program(&CheckedProgram)` returns a privately constructed `Module`
with `bytes()`, `binding_bytes()` and `identity()` accessors, or
`EmitError::{Bound,Interface}`. It writes no file and launches no process.
It cannot consume serialized checked artifacts or create an unchecked program.
The frontend checks every function and both arms, including unused code, before
lowering. The library emits all sorted functions; it never evaluates the input
program, imports an oracle or selects functions by measured results.

The module targets `x86_64-unknown-linux-gnu`, little endian, system C entry
`bagaev_probe_entry`, with `target-cpu="x86-64"`. It uses opaque pointers,
explicit `i32`/`i64` widths and byte offsets for output. The external compiler
profile must retain this target/baseline and independently establish the actual
tool identity, full dependency closure and O0/O2/Os setting. Source metadata
does not attest a compiler or object file. Host CPU selection and target/feature
overrides are outside the supported profile.

All fifteen checked forms lower to ordinary LLVM instructions, direct function
calls and bounded control flow. Scalars use internal i64 values; Bool remains
0/1, comparisons use signed Int64 predicates or scalar equality and zero-extend
the bit result. Function parameters are SSA values. Lexical slots are distinct
function-local, aligned stack allocas created once at entry, with stores only
after initial expressions succeed. Checked lexical scope ensures a use is
initialized. A callee has its own parameter/local namespace; acyclic checked
calls limit simultaneous language function frames to eight. Structural emission
recursion is bounded by checked expression depth32 and total nodes512.

Every reached expression checks the shared work counter before its children.
At65536 it records status2 and that complete source node ID without increment;
otherwise it increments once. Tick stores/loads are volatile local bookkeeping
to retain semantic accounting through optimization. No implicit entry, binding,
index-update or return tick exists. Children lower left to right; calls check
the shared failure status immediately upon return before later caller work.
Overflow sets status1 and the arithmetic node after both operands succeed.
Every failure branches immediately to a return path, preserving the first
status/location and exposing no partial value.

Lazy `if` uses two blocks and a PHI at their successful merge. A loop evaluates
its initial expression once, initializes its private index/accumulator slots,
tests unsigned index<count, emits the body once in the native cycle, and updates
only on success. Count0 reaches no body tick; count1024 stays within the frozen
bound. Nested loops use different checked slots. LLVM signed i64 overflow
intrinsics handle add/sub/mul; no `nsw`/`nuw`, inbounds assertion, division,
shift, undef, poison, trap, compiler-specific exception or dynamic dispatch is
used. Plain bookkeeping increments have bounded reachable ranges and modular
LLVM semantics.

Native state is invocation-local; there is no global mutable state, language
heap, import, effect, callback, loader, source AST lookup or dynamic compilation.
Native stack availability remains an external resource precondition; a host
stack/resource failure is not a language observation.

## Entry and binding

The callable signature is frozen:

```
void bagaev_probe_entry(const int64_t arguments[8], void *output)
```

Both caller regions must be non-null, 8-byte aligned, valid for64/32bytes and
disjoint. The entry performs all eight volatile input loads before any output
store, then validates active Bool and unused slots in one increasing-index
pass before invoking any expression. Bool uses unsigned <=1 and unused slots
must be0. A bad slot writes status3/type0/value0/work0/reason8 and location
2147483649+slot. Int64 accepts every64-bit pattern. All result paths call the
same output writer, which uses volatile i32/i64 stores at offsets
0,4,8,16,24,28 with alignment4,4,8,8,4,4, covering every one of the32bytes.
There is no C/Rust struct layout or aggregate return assumption for output.

The descriptor is canonical JSON schema `bagaev-probe-llvm-binding/1` with
exact fields `abi`, `cpu`, `entry`, `functions`, `llvm`, `nodes`, `program`,
`program_pin`, `schema`, `semantic`, `target`, `work_limit`. `abi` contains
alignment, byte counts/order, C convention/signature/symbol, field layout,
reason/status/type codes, disjointness and argument location base. `entry` is
the sorted function index. Function records have exactly body, callees, index,
locals, name, parameters, result; local/parameter records name, slot, type.
Node records have exactly children, function, id, op, pointer, type. Children
retain source order and both static arms. Node IDs include all unused bodies
and arms. The complete canonical `program` retains operation metadata and
literal values; `program_pin` is H(program). Pointers are program-relative;
an invocation observer adds `/program`, or maps the argument location to
`/arguments/i`. This descriptor is data, never a checked-construction API.

The exact descriptor bytes, without LF/NUL, are embedded as immutable global
`bagaev_probe_binding`, with every byte escaped as LLVM hex, and their length
as immutable i64 `bagaev_probe_binding_length`. Native kernels do not consult
these globals. A separately admitted caller may inspect their exported data
symbols and compare exact binding; merely finding symbols is not acceptance.

`binding_bytes()` is C(record)+LF, schema `bagaev-probe-llvm-module/1`, with
exact fields `artifact_pin`, `binding`, `binding_pin`, `module_bytes`, `schema`.
`binding` is the embedded descriptor; `binding_pin` is B(its exact canonical
bytes), `artifact_pin` is B(the exact entire emitted LLVM bytes), and
`module_bytes` is that byte count. Keeping artifact_pin outside the embedded
descriptor avoids a circular hash. Canonically equal input programs emit equal
bytes; unused semantic changes alter the complete program binding. A compiled
object/executable needs its own separately observed identity and correspondence
to this module/binding; the module record cannot attest that relationship.

The final module cap is8MiB and descriptor/final binding cap2MiB each, including
the final binding LF. The writer enforces its limit before every text append.
No partial `Module` is returned. A construction bound/interface failure,
allocation failure or panic is an environment failure, not `invalid-ir`.
Storage is compiler bookkeeping only; there is no new language heap feature.

## Explicit file CLI

```
probe-llvm emit-program --input PROGRAM_FILE --output /out/MODULE_FILE
```

There are exactly five ordered arguments. No stdin (`-`), default paths,
discovery, overwrite flag, compiler invocation, subprocess, loader, cache,
dependency resolver, network or directory creation exists. Input is opened
read-only, must be a regular file and may not itself be a symlink. The complete
read stops at EOF or the1048577th overrun witness. A complete frame<=1MiB is
checked for size/modification metadata consistency before parsing; oversize
frames receive IR_BOUNDS without parsing a prefix. Interrupted reads retry;
other I/O errors and incomplete/changing input are nonzero environment errors.
The complete standalone program goes through the accepted
`check_program_bytes` grammar and phase priorities.

Output must be an absolute descendant of `/out` without parent traversal.
Its existing parent must resolve to itself under `/out`. The input and output
ancestors must be externally admitted and stable, with one owner for the output
path: metadata/canonicalization checks are not a hostile-host race boundary.
The CLI builds the entire bounded module and binding before opening output.
`create_new(true)` refuses every existing destination including dangling
symlinks. The new descriptor is checked regular; module write, flush and
`sync_all` must succeed before the binding is written/flushed to stdout.
It never deletes, truncates, replaces, retries a failed artifact creation or
promotes a partial file. There is no sidecar file.

Successful emission has stdout exactly the module record+LF, exit0. A malformed
program has stdout exactly canonical `bagaev-probe-result/1` invalid-ir+LF,
exit0, with standalone-program locations, null value/type and work0; no output
module is opened. There is no native evaluation result on successful emission.
Invalid CLI shape or host/read/construct/write/sync/stdout failure has nonzero
exit and a short path-free stderr diagnostic, without a valid complete protocol
claim. Output errors can leave a partial new file; stdout failure can leave a
complete new module and incomplete binding. Both remain unadmitted evidence
for the external owner. A later call still refuses that existing path.

The CLI is a binary root compiled from `llvm_main.rs`, not a mode of the frozen
frontend CLI. The test root is
[llvm_source_tests.rs](../../../../tests/probes/backend/llvm_source_tests.rs),
which includes the modules and CLI under cfg(test). The tests cover all forms,
complete binding/byte identity, unused code, tick/failure lowering, control flow,
zero/max loops, ABI layout/read order, finite construction and pure CLI/I/O
failure cases. They do not execute generated LLVM or load expected vectors.
Actual existing-file/symlink refusal, regular-file errors, partial-file cleanup
policy and native observations need separate admitted integration checks.

## Primary interface references

The LLVM21.1.0 contracts used here are
[signed overflow intrinsics](https://releases.llvm.org/21.1.0/docs/LangRef.html#arithmetic-with-overflow-intrinsics),
[volatile accesses](https://releases.llvm.org/21.1.0/docs/LangRef.html#volatile-memory-accesses),
and the same manual's C convention, PHI, alloca, load/store, byte GEP, string
escaping and data-layout rules. Signed intrinsics supply a value and overflow
bit; volatile accesses preserve their count/order; PHI inputs correspond to
predecessors. Output remains explicit byte stores.
[Rust1.93.0 filesystem source](https://raw.githubusercontent.com/rust-lang/rust/1.93.0/library/std/src/fs.rs)
defines atomic new-file creation, including symlink refusal, and describes
pathname TOCTOU and sync/close limitations. These contracts guide source
construction and do not prove an emitted module or file operation was run.
