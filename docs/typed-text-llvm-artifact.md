# Typed Text source-to-LLVM envelope

Experimental schema: `bagaev-typed-text-llvm/1`. Input is a complete bounded
`bagaev-typed-text/1` program, not an invocation. Check the whole program with
its current validation order. Arguments are not part of this interface.

A source refusal is canonical JSON plus LF with exactly `kind`="refusal",
`location` (relative to the program root), `reason` (TX_*), and `schema`.
A success has exactly `execution_admission`=false, `kind`="module", `llvm_ir`
(exact LLVM UTF-8 string), `module_record` (the complete existing canonical
bagaev-text-llvm-module/1 object), `schema`, and `source_pin` (exact checked source
identity). The embedded record omits only its outer LF. Hashes retain their
existing sha256: prefix and distinct source/module/binding byte domains.

Whole envelope bound: 64 MiB. Existing emitter module8MiB/binding2MiB caps stay.
Any emitter/encoding/output-construction failure is environmental, not a source
refusal or a truncated module. The operation returns data only. It never runs a
compiler, links/loads an artifact, chooses a kernel, or grants execution rights.

The existing bounded Text CLI adds `emit-llvm --input FILE`, reusing its complete
regular-file input and stdout error handling. Existing `run --input FILE`
retains the original invocation behavior. No file publisher or settings change.

Before wrapper implementation, capture module/reference pins from the already
canonical corrected library for valid source programs; derive refusal locations
from existing source cases. These are shared-library integration references,
not independent semantic or native-execution proof. Acceptance checks exact
keys, canonical full wire, refusal fields, all pins/lengths and complete record
hashes, plus unchanged run-command regressions.

## Bounded implementation

The [wrapper](../examples/probes/backend/rust/text_emit.rs) and existing Text CLI
implement the envelope. All 44 [pre-wrapper references](../examples/probes/text-llvm-envelope-cases.json)
passed: 37 module records and 7 exact source/transport refusals. The original
`run` command passed all 26 frozen invocation cases. Six CLI environment controls
(missing/extra arguments, unknown command, absent file, directory, symlink)
returned nonzero with no domain output. [Observations](../examples/probes/text-llvm-envelope-observations.json)
record the bounded checks. Separate same-maintainer review, no independent
semantic proof, new native execution or performance result from envelope tests.
