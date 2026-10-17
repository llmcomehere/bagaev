# Review two authored sources without preparing a patch

`record_source_diff.py` compares two explicitly pinned record-form/5 sources as
data. It fills the review gap between a full source inspection and preparing an
apply packet. The existing draft tool keeps its narrower change rules; this
comparison accepts no-op, removal, declaration and signature differences.

```sh
python3 -B -S tools/record_source_diff.py BEFORE.bagaev AFTER.bagaev \
  --before-sha256 BEFORE_SOURCE_SHA256 --after-sha256 AFTER_SOURCE_SHA256 \
  --output NEW_REPORT.json
```

The equivalent authored entrypoint is `python3 -B -S tools/record.py diff` with
the same remaining arguments. No flags or identities are inferred by the route.

Use caller-established input identities and trusted ancestor directories. Each
source and the report are limited to 1 MiB. A different form header is refused;
the tool does not auto-detect or convert profiles. Both equal and different
comparisons complete with exit zero. Inspect the report rather than using the
exit code as an equality test. Invalid input or usage returns two.

## What the report means

The report fixes source and canonical decoded-program SHA256 identities on both
sides. `source_equal` compares exact bytes; `program_equal` compares the existing
canonical JSON programme representation. Comments, whitespace or declaration
ordering can change source bytes without changing that representation.

Entry names are shown before and after. Record, list, variant and function
namespaces each contain sorted `added`, `removed` and `changed` arrays, including
empty arrays. Rows contain item names and canonical before/after item hashes.
Changed functions also separate `signature_changed` from `body_changed`.
Signatures consist of params and result; a function item's hash includes its
complete params, result and body. Whole bodies and local filesystem paths are
not included. Use the existing function-context command for a selected body.

Canonical bytes use sorted JSON keys, compact separators, UTF-8 text and no
non-finite values. Arrays retain order. This is structural identity, not semantic
equivalence: parameter spelling and decoded binding structure can matter to the
comparison even if two programmes would return the same value.

Parsing is not semantic validation. The report always sets `semantic_check`,
`execution_admission` and `patch_application` to false. It is neither an apply
packet nor permission to execute. No checker, compiler, programme evaluator,
database or provider is invoked.

## API and errors

The pure API is `bagaev_record_source_diff.compare_sources(before, after,
before_sha256=..., after_sha256=...)`, where both inputs are bytes. It returns
the report dictionary. `DiffError` exposes `code` and `side` (before, after, or
None). Pin syntax precedes input type/size, identity checks and parsing; each
stage checks before then after. Existing form parser error codes are preserved.

The CLI emits a compact `bagaev-record-diff-tool/1` JSON envelope. Success names
the report byte count and SHA256; refusal names the error code and side. Existing
output is never replaced. Source preservation and report readback are checked,
but this does not protect against hostile filesystem races or untrusted report
ancestors. A write/readback failure can leave partial new output.

Stdout delivery is separate from report creation. A failed or short stdout write
returns one and attempts `DIFF_DELIVERY` on stderr. It neither retries stdout nor
deletes a completed report. If stderr also fails, exit one is the only signal.
Reconcile the retained file instead of assuming that no report was created.

## Bounded controls

The literal [source pairs](../examples/probes/source-diff/cases.json) and
[manually specified programme values](../examples/probes/source-diff/programmes.json)
were fixed before comparison implementation. They cover exact equality, trivia,
ordering, body/signature/add/remove/entry changes, declaration changes and sorted
output. The original typed journey supplies a separate one-function example.
Hashes of fixture items are mechanical identities, not execution evidence.

The portable test is `tests/probes/test_record_source_diff.py`. Its fault seams
are explicitly labelled. A real report-overflow control uses two source files
with different long unused-function names: each input fits its limit, while the
combined added/removed names exceed the report limit. This is possible within
the form parser's syntax bounds and does not claim semantic acceptance of those
identifiers. No performance, model benefit or general-correctness claim follows.
