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
