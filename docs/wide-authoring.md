# Read and repair form5 source

The [sixteen-entry catalogue](catalog-wide.md) now has explicit source diagnostics
and graph-preserving formatting as well as [focused editing](wide-function-editing.md).
These tools handle source as data and launch no runtime.

```sh
python tools/record_diagnose.py Catalog.bagaev --form 5 --output diagnostic.json
python tools/record_format.py Catalog.bagaev --form 5 --output formatted.bagaev
```

Both outputs must be new files. Diagnostics default to form1 and formatting to
form4; explicit selectors are required for form5. No version is inferred from
the input. Old modules and their literal fixtures are unchanged.

Diagnostics preserve the existing structured diagnostic schema and report
`form: record-form/5`. Byte offsets are half-open UTF-8 spans; line/column pairs
are one-based Unicode scalar positions. Parsing failures identify a context,
not necessarily a uniquely wrong token. Lowering refusals can have no span.
A valid form is not a typecheck, business acceptance or execution permission.

The formatter preserves token order and literals and checks exact decoded-graph
equality before returning output. Reformatting its output is idempotent. Raw
source hashes and diagnostic locations can change; decoded program identity is
preserved. The new [formatted catalogue](../examples/probes/wide-authoring/Catalog.formatted.bagaev)
has 365 lines. That is a presentation observation, not a model-cost result.

Seven inherited literal diagnostic observations were frozen with only the
same-length accepted header changed to form5; wrong header9 remained unchanged.
All seven API/CLI results and four transport controls passed. Two literal
formatting expectations, full catalogue graph preservation/idempotence, two CLI
operations and two refusals passed. Original form1 diagnostic and form4 format
checks passed unchanged. These checks made no runtime calls and do not establish
independent reproduction or production readiness.

The preparation tool already supports explicit form5 and writes invocation/11.
The focused replacement tool supports form5 separately. Whole-program draft
support remains limited to its existing versions; use the focused path when
changing a single function in this profile.

## Explicit soft line width

`record_format.py SOURCE --form 5 --width 80 --output NEW_FILE` selects an
optional token-preserving wrapped view. The library entry is
`format_source_wrapped(source, width=80)`. Width must be an integer from40 through120;
the CLI refuses other values and form4 before reading input. Omit the option to
retain the previous formatter bytes and receipt. The opt-in receipt adds
`soft_width` only.

This is a soft Unicode-character goal, not display-cell or byte width. Long
quoted literals/comments are indivisible; closing punctuation and indentation
can exceed the goal. Continuation indentation counts open braces/parentheses,
capped at12levels. Comment text/order is retained with the existing trailing
whitespace normalization. Output remains LF text within the existing1MiB limit.
Token order, literals and parentheses are preserved; the complete decoded graph
is checked again. No expression rewriting or execution is performed.

Five portable tests cover old frozen bytes, widths40/80/120, exact token/comment
and graph preservation, idempotence, Unicode/CRLF and long atomic text, input/output
bounds, invalid usage before reads and exclusive output files. On the accepted
named batch source, width80 produced243lines with maximum81characters and no
lines over100, compared with186lines/max178/eight over100 in that input. These
are presentation counts, not token-cost, model preference or speed measurements.
