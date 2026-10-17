# Find a source-check refusal in readable code

`tools/record_check_location.py` joins a retained, input-bound
`bagaev-record-source-check/11` refusal to authored form5 source. It consumes
data only; it does not run the checker or evaluate the submitted program.

```sh
python -B -S tools/record_check_location.py source.bagaev \
  --checked-input program.json --result refusal.json \
  --source-sha256 SOURCE --program-sha256 PROGRAM \
  --input-sha256 INPUT --result-sha256 RESULT --output location.json
```

Select the four expected lowercase SHA-256 pins independently: exact authored
UTF-8 source, canonical decoded program, exact JSON submitted to the checker,
and exact retained result bytes. The tool recomputes them, requires the input
JSON to represent the same decoded program, and checks the verdict's input
binding. Merely similar source or a verdict about different bytes is refused.

RR_TYPE and RR_REFERENCE locations map only when their exact pointer has an
existing expression-map entry. The result retains exact-expression or
enclosing-expression precision, UTF-8 byte offsets, line/column coordinates,
and an excerpt capped at256Unicode scalars. It does not guess the nearest
expression. Root, schema, declaration, signature and other unmapped locations
retain the original reason/pointer with null location/excerpt. Invalid data and
pins are refusals, not unmapped successes. Checked results are outside this tool.

The library entry is `bagaev_record_check_location.locate`. Its
semantic_check, result_authentication and execution_admission flags remain false:
binding supplied data does not prove that the claimed checker ran or was trusted.
All inputs are bounded to1MiB. Output must be a new path; an I/O failure may
leave a new incomplete file, without replacing an existing file.

Eight bounded test methods passed after separate review, covering literal type
and missing-call locations, unused-helper Unicode/CRLF positions, coarse spans,
unmapped pointers, identity/envelope refusals, strict JSON controls,
noncanonical input, excerpt truncation and existing/absent output preservation.
The [retained type refusal](../examples/probes/record-check-location/type-refusal.json)
is an actual source-checker observation for main returning Bool instead of Int64.
Its reuse is not a new checker invocation. Two earlier test attempts exposed
fixture mistakes (a comment before the mandatory header and a one-based column
miscount); corrected literal fixtures passed without changing production code.
