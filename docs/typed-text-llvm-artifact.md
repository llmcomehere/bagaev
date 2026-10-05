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

## Small CLI example

Review the source and arrange an admitted Rust build/run profile before using
these commands. From the repository root, with Rust 1.93.0 and an existing
owned `target` directory:

```sh
rustc --edition=2021 -D warnings examples/probes/backend/rust/text_main.rs -o target/typed-text
target/typed-text run --input examples/probes/text-example-invocation.json
target/typed-text emit-llvm --input examples/probes/text-example-program.json
```

The [invocation](../examples/probes/text-example-invocation.json) computes the
UTF-8 byte length of `Hello`. Its complete result is:

```json
{"location":null,"reason":null,"schema":"bagaev-typed-text-result/1","status":"success","value":5,"value_type":"Int64","work":7}
```

Work7 is one length-expression tick, one literal tick and five literal bytes;
it is not time. The [program-only input](../examples/probes/text-example-program.json)
produces a `kind=module` envelope with `execution_admission=false`. Printing that
envelope does not execute the program or invoke LLVM. Both example commands were
checked in the bounded profile; the example is not an unqualified native runner.
