# Explicit form6 authoring

The data-only form6 codec selects typed-record/12 and supports `json.bool_or`.
Choose `--form 6` explicitly; old tool defaults and versions are unchanged.

- `tools/record_text.py`: decode, encode (also `--named-calls`), inspect.
- `tools/record_diagnose.py`: source identity, syntax validity and error context.
- `tools/record_format.py`: token-preserving formatting and optional soft
  `--width 40..120`. Comments and named calls are retained; complete program
  graph equality is checked. Reformatting is idempotent on the tested cases.
- `tools/record_json_prepare.py`: lossless Json-only invocation12 data.
- `tools/record_source_map.py`: expression ranges with required `--program-pin`,
  optional `--source-sha256` and `--pointer`. Raw layout identity is separate
  from the complete graph pin; repeated equal literals retain distinct ranges.
- `tools/record_function.py`: read-only `extract` and `context --name NAME`,
  including `--locations` or `--source-body`. Canonical fragments contain only
  the selected function and type environment; direct callers/callees carry
  signatures/pins. Original body text/hash refers to the original full source,
  including internal comments, never the canonical fragment's coordinates.

Each command needs an input and a new `--output` path; the preparer also needs
`--arguments`. Generic record_text prepare6 and inspect6 `--bounds` refuse
`TOOL_USAGE` before reading inputs. Form6 function `replace` and
`--callee-context` also refuse before I/O; draft/export tools remain on existing
profiles. A diagnostic's `valid_form` is syntax/lowering
validity only. All tools report no semantic checking or execution admission;
none runs the program or a compiler. Follow the existing bounded regular-file,
exclusive-output and execution-authority contracts.

Tests cover actual Boolean source, named calls/comments, all four width modes,
the active-total application graph, transport refusal order, version/context
spans, missing named functions and exclusive outputs. These are finite layout
and transport observations, not runtime/native conformance or performance.

See [the compact reference](choose-and-start.md),
[projection semantics](record-json-bool-proposal.md) and
[lossless preparation](json-argument-prepare.md).
