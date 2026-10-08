# Readable source formatting without semantic change

```console
python3 -B tools/record_format.py input.bagaev --output formatted.bagaev
```

The fixed form4 formatter changes whitespace between tokens only. String literals,
identifiers, numbers and token order are retained. It decodes both forms and
requires exact typed-program graph equality before returning output. It does not
check types, run the program or grant execution admission. Outputs are bounded
and must be new files; the input and existing outputs are preserved.

The layout separates declarations and record fields, with line breaks around
then/else/in expression boundaries. This is a small deterministic formatter,
not a comment-preserving editor: this form has no comment syntax. Formatting is
idempotent and keeps canonical program pins unchanged, while raw source pins and
source diagnostic positions change. Never reuse an old raw-source location pin.

[The formatted catalogue](../examples/probes/record-format/Catalog.formatted.bagaev)
contains the same 24-function graph as the compact accepted source: 340 lines and
11,973 UTF-8 bytes for this snapshot. The compact source is retained unchanged.
These sizes are presentation facts, not model-cost or performance measurements.

Two literal formatting examples cover punctuation/Unicode inside strings and
let/if layout. The complete catalogue preserves its graph and is idempotent;
two CLI calls check output and existing-output refusal, with an old-version
refusal control. No reference or native kernel is newly executed by these tests.
