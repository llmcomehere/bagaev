# Read emitted Python before choosing an execution pin

The form5/profile11 compiler keeps emitted Python inside `artifact.json`.
This data-only stage extracts those exact UTF-8 bytes for review. It accepts a
six-file compilation packet, not a completed run or arbitrary Python filename.
It never imports, compiles, parses or executes the extracted text and never
invokes the checker, a database or a provider.

```sh
python3 -B -S tools/record.py preview-cpython \
  --compiled /absolute/compile-directory \
  --receipt-sha256 COMPILE_RECEIPT_SHA256 \
  --source-sha256 SOURCE_SHA256 --program-sha256 PROGRAM_SHA256 \
  --output /absolute/new-preview-directory
```

The direct delegate is `tools/record_cpython_preview.py` with the same flags.
Use a reviewed reader under an authorized bounded profile, with assertions,
`-B -S`, and no `PYTHONPATH` or `PYTHONHOME`. These flags alone are not isolation.
Input/output paths must be absolute with trusted directory ancestors. The output
must not exist or overlap the input. Inputs are regular nonsymlink single-link
files. Hostile filesystem races are not covered.

## What to review

The new directory contains only:

- `python.txt`: exact extracted bytes, with no newline or other text added;
- `report.json`: caller-selected identities, packet consistency and limitations;
- `MANIFEST.json`: hashes and sizes of the other two files, written last.

Read `python.txt` as data and independently hash its exact bytes, for example
with `sha256sum`. Only after reviewing that text, its source/compiler/runtime
and the execution profile should the resulting hash become the separately
chosen `--python-sha256` for [source execution](record-cpython-run.md). Do not
automatically copy the packet's declared hash into an execution command or
change the expected hash just to bypass a runner refusal.

No expected Python hash is required by this preview: discovering text for
review is its purpose. The externally selected receipt/source/program pins
bind the input bytes but do not authenticate who produced them.

## Exact boundary

Only `record-form/5`, program profile11, compile receipt schema1, artifact
schema1 and checker-report profile11 are accepted. Form6/profile12 is not
auto-detected or converted. Exactly six files are required: `source.bagaev`,
`program.json`, `checker.stdout`, `checker.stderr`, `artifact.json`, `receipt.json`.
Receipt, checker and artifact field sets and hash links are checked; flags require actual JSON Booleans,
and checker stderr must be empty. Source is UTF-8 data; its language syntax is
not checked. A program's declared schema is checked, not its semantic validity.

Receipt, program and artifact JSON must be canonical: sorted keys, compact
separators, UTF-8 and no noninteger/nonfinite numbers. Checker JSON may contain
whitespace. Duplicate keys and invalid Unicode are refused. Metadata depth is
at most64 from rootdepth0, with at most32,768 nodes including object keys and
values. Source/program/checker stdout each fit1MiB; checker stderr4KiB;
artifact4MiB; receipt64KiB; the packet8MiB. Extracted Python is at most1MiB;
report and manifest each16KiB. These are finite reader limits, not language
qualification or performance measurements.

The report status `consistent` means only this bounded packet relationship.
`claimed_checker_sha256`, `claimed_generator_sha256` and `claimed_runtime_sha256`
remain claims from input metadata. `fresh_compilation`, `checker_invoked`,
`compiler_authentication`, `semantic_check`, `source_program_equivalence_checked`,
`program_python_equivalence_checked`, `python_syntax_checked` and
`execution_admission` are always false. An internally consistent fabricated
packet can pass; this reader does not authenticate a compiler or accept code.

## Failures and preservation

Success exits0 and writes a JSON summary. Invalid invocation profile exits1;
usage exits2; definite pre-output refusal exits3. Once output creation is
attempted, write/readback/interruption/delivery failures exit4 with
`PREVIEW_UNCERTAIN` and `uncertain:true` when the error can be delivered.
Lost stdout can leave the complete three-file preview. Inspect retained files;
do not overwrite, automatically retry an execution, or delete partial evidence.

Inputs and the reader's own source are reread for preservation. This is not
crash durability or hostile-filesystem protection. The public portable checks
are `tests/probes/cpython_preview_process_checks.py`; run them explicitly with
`python3 -B -S` under a reviewed profile. They use synthetic unauthenticated
packets, exact output expectations and labelled failure seams. Their presence
alone is not execution evidence.
