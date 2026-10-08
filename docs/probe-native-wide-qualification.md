# Selected generated profile11 native qualification

This is a subsequent execution stage after the separate
[emitter](probe-native-wide-emitter.md), [owned wire](probe-native-wide-wire.md)
and [adapter](probe-native-wide-adapter.md) qualifications. Their original
NOT_RUN statements describe those earlier stages.

Two fixed, reviewed generated kernels were compiled and actually called:
a zero-argument sixteen-record sum and the Json-entry application/3 catalogue.
The sum returns 120. The catalogue uses all fifteen previously frozen
[wide cases](../examples/probes/catalog-wide/cases.json), including business
errors, the sixteenth entry, reindexing, clearing, optional dates and rejection
precedence. No application expectations were derived from native output.

## Observations and limits

LLVM 21.1.8 upstream 2078da43e25a, Debian package build 20260528180759.79,
compiled each emitted module at O0 and O2 for x86_64-unknown-linux-gnu,
with march=x86-64 and warnings treated as errors. This recovered current
package build differs from the earlier historical compiler package.
Compiler and module identities are in the
[captured packet](../examples/probes/native-wide-qualification/observations.json)
and its two binding files. Hash identity is not execution authority.

Across sixteen fixed cases, 64 native calls (two optimizations, two dirty
scratch fills) and sixteen reference11 calls passed. Full typed values and
logical work agreed; complete native wire bytes were identical across both
optimizations and fills. The sum uses 610 logical ticks. The sixteen-set case
uses 40,212 ticks and produces 5,479 bytes; sixteen-list uses 39,571 ticks and
6,535 bytes. Logical ticks are language accounting, not measured time or cost.

The exact-source harness checks canonical source and embedded binding bytes,
keeps immutable Json owners alive, snapshots input descriptors/text around one
kernel call, checks scratch guards and unused tails, and exports owned bytes
before dropping input and scratch owners. Rust edition 2021 builds denied
warnings. Execution used the already admitted bounded no-network profile.
These checks do not make an arbitrary native function pointer safe.

This is selected-kernel conformance, not complete profile11 qualification:
native work-limit/overflow failures, broader continuation scenarios and
independent reproduction remain open. The typed-entry inventory example was
not run natively. There was no performance measurement, model study, adoption
measurement, persistence claim or execution-policy change.

## Portable data-only packet

[The checker](../tests/probes/native_wide_qualification.py) offers four modes:
request, harness, check-native and check-reference. Each selects sum/sum or
catalog/a frozen case ID. Request prints the invocation. Harness requires an
explicit absolute backend source path and prints unadmitted Rust source.
Check modes require an existing regular output file. They never compile,
launch a process, load a kernel or fetch dependencies.

The checked-in wire hex, work and reference responses are captured observations,
not independent expectations. Complete business expectations remain the frozen
catalogue cases and sum 120. The checker first compares captures against those
values, then checks a separately supplied result against the whole observation.
Its separate BCMPRES4 structural extractor does not accept an older magic.
Python optimization must remain disabled because structural checks use assertions.

For a separately authorized reproduction, emit the selected fixed invocation,
verify its source/module/binding identities, render the harness against the
matching backend sources, compile the LLVM object at each selected optimization
and link that exact object into the Rust harness. Call the admitted harness with
the invocation file and fill 90 or 165, retaining complete stdout and stderr.
Use check-native on each output and check-reference on the reference11 output.
Do not treat this description, generated source, or captured packet as permission
to execute code or install a toolchain.
