# Discover a pure profile before choosing it

Models and tools can inspect a small structured description before loading a
whole example. This supports an informed choice of profile; it does not show
that a model prefers bagaev or that a workload will finish inside its bounds.

```sh
python tools/record_capabilities.py --form 5
```

The command prints one deterministic `bagaev-record-capabilities/1` JSON object.
Explicit form4 and form5 are supported by this discovery endpoint; it does not
replace documentation for older forms or stateful/native profiles. No files are
written and no program, provider or reference is invoked.

The report identifies source/program/invocation/result schemas, parser bounds,
selected reference bounds, named intrinsic spellings and arities, and data-tool
operations. Intrinsics come from the selected codec. Operators, declarations,
fold/match syntax and complete typing rules are deliberately not enumerated.
A null arity means a variable-argument spelling; records.list begins with a
literal declared type name. JSON/record field keys are literal strings. Literal
argument indices in the report are zero-based.

## Choose without mixing versions

- Form4 maps to typed-record/10 and record-list capacity4.
- Form5 maps to typed-record/11 and record-list capacity16.
- Both provide explicit preparation, syntax-context diagnostics, formatting,
  focused function context/replacement and pinned focused-draft source export.
- Tool defaults differ. Pass the reported form explicitly for the selected path.
- The pure profiles do not provide program filesystem/network effects or durable
  state. Reference CLI input-file handling is a separate operator action.

A request within individual declared capacities can still exceed combined
shape/work bounds. Parser acceptance is not a runtime typecheck, and capability
metadata supplies no execution admission. The report is not an exhaustive
semantic specification or a production-support guarantee.

Two frozen profile/bound expectations, all31 named intrinsic spellings,
deterministic/detached API results, five CLI calls and six API/CLI refusals passed.
No runtime calls or model-choice measurements were made. The form5 codec's stale
introductory docstring was also corrected to identify profile11; its behavior
was not changed.
