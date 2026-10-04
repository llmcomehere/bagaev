# Bounded Cranelift AOT probe

The [experimental crate](../examples/probes/backend/cranelift/Cargo.toml)
constructs ELF objects from the existing complete checked kernel IR. It shares
the unchanged Rust checker, node numbering, canonical program and SHA-256
implementation with the LLVM probe. It does not implement full native L2/L3,
replace the CPython beta or select a production backend.

The implementation pins Cranelift 0.136.2 and Rust 1.96.0. The
[upstream release manifest](https://github.com/bytecodealliance/wasmtime/blob/v49.0.2/Cargo.toml)
sets that minimum Rust version; the
[object crate](https://github.com/bytecodealliance/wasmtime/blob/v49.0.2/cranelift/object/Cargo.toml)
provides native object emission. Cargo.lock records the exact dependency
closure. Artifact generation uses the fixed x86_64-unknown-linux-gnu target,
baseline target features and system C calling convention. No host-CPU feature
discovery, JIT, dynamic loading or model/provider call is used.

## Interface

The library's `lower::object(&CheckedProgram, Mode)` returns bounded object
bytes. `Mode` selects exactly none, speed or speed_and_size. These mode names
do not assert equivalence to particular LLVM optimization settings.

The driver accepts exactly `emit-object MODE`, reads one bounded complete
program from standard input, checks it, and writes the object to standard
output. Static refusals and environment failures exit unsuccessfully; they
are not emitted as native results. The driver neither links nor executes the
object. Review source, the lockfile and the separately authorized build/run
profile before using it; an example invocation is not execution permission.

The output exposes `bagaev_probe_entry` with the
[frozen 64-byte-input/32-byte-output ABI](probes.md#fixed-native-abi).
The complete canonical semantic program is embedded as data under
`bagaev_probe_program`; it is an identity aid, not execution authority or proof
that an arbitrary object is trustworthy. Receivers must retain exact object,
source and build identities from a trusted construction path.

Each node charges work before evaluating its operands. Signed overflow
instructions feed explicit refusal branches. Branches remain lazy, function
failures propagate their original location and work, and loop accumulators use
SSA block parameters. Active Bool and inactive zero slots are checked in index
order before any semantic work. Memory accesses retain their default trapping
flags; no no-trap or alias promises are introduced to discard required ingress
reads. The caller must satisfy the frozen pointer, alignment and disjoint-region
preconditions. These checks do not make arbitrary pointers safe.

## Observed checks, October 4, 2026

The crate built offline with its locked dependencies using one build job.
Three unit tests passed: SHA known answers, unchanged checked program identity,
and deterministic ELF construction for all three declared modes. They do not
alone establish runtime conformance.

The [native observations](../examples/probes/cranelift-observations.json)
record 25 fixed variants in three modes and two output-buffer prefills:
150 complete output-buffer matches against the unchanged frozen kernel oracle.
All 64 input bytes were also checked before and after each invocation. Cases
include arithmetic boundaries, signed overflow, laziness, calls, zero/maximal
loops, first failure, exact/refused work bounds and invalid ABI slots.
The same existing C observer used for the C11/LLVM probes was linked at O2.

The Cranelift compiler executable was built in the dev profile with no debug
information and 16 codegen units. These are conformance observations, not a
compiler-performance benchmark. No claim about speed, memory, dependency-size
advantage or total model/development cost follows. Full native-language parity,
the original linked Rust caller and production acceptance remain separate.
Review used a separate same-maintainer pass, not independent review.

## Concrete negative controls

On October 4, 2026, three separately copied `lower.rs` mutations were checked
against the frozen kernel oracle: omitted overflow guard (`K-OVER-ADD`), an
early work-limit boundary (`K-WORK-EXACT`), and reversed operand evaluation
(`K-LEFT-FAIL`). Each was detected in all three modes and both output prefills,
giving 18 complete ABI deviations. All 64 input bytes remained unchanged.
The [recipes and observations](../examples/probes/cranelift-mutation-observations.json)
include the correct literal bytes and actual mutant bytes. Prior unmodified
conformance receipts matched the same witnesses; the baseline source and
compiler identities were unchanged after this experiment.

These are three specific negative controls, not full mutation coverage or proof
against arbitrary bugs. Mutants were temporary experiment inputs, not changes
to the production candidate. Review was a separate same-maintainer pass.
