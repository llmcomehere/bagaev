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

## Explicit discovery revision 2

Select the additive report explicitly:

    python tools/record_capabilities.py --form 5 --revision 2

It uses bagaev-record-capabilities/2. The default and explicit --revision 1
retain the earlier report byte-for-byte. Existing error envelopes stay on
bagaev-record-capabilities/1.

Revision 2 additionally distinguishes the strict typed-argument route from
[lossless Json-only preparation](json-argument-prepare.md), including exact
arity, preserved numeric lexemes, frame/depth limits and refused syntax classes.
It lists that new data tool without turning preparation into execution.

The native-preparation section identifies the selected profile's checked emitter
source, module/binding schemas, target and success-wire magic. Form4/profile10
uses BCMPRES3; form5/profile11 uses BCMPRES4. Both require a zero-argument or
Json-only entry and exclude Json results. These are eligibility requirements,
not a promise of general native conformance. The report never compiles,
discovers an executable, loads a kernel or supplies execution admission.

Two frozen revision-2 additions passed 12 data CLI checks, four CLI refusals
and three API refusals, including deterministic fresh results. The unchanged
legacy check passed its five CLI calls and six API/CLI refusals. Default output
for both forms also matched the preceding accepted implementation byte-for-byte
in four additional CLI calls. No programme/runtime or model calls occurred.

## Explicit revision 3: source debugging

`python tools/record_capabilities.py --form 5 --revision 3` adds discovery of the
[checked node inspector](native-source-locations.md) and the
[layout-bound readable source map](record-source-map.md). It states required and
optional flags, identity formats, pointer joining, scalar/byte coordinates,
coarse versus exact ranges and additional map bounds. It does not claim that a
compiled inspector is available, authenticate native output or grant execution.

Form4 revision3 explicitly reports this combined path unsupported and retains
its typed-record/10 identity. It never upgrades to form5. The default revision1
and explicit revision2 responses remain byte-for-byte unchanged for both forms.
Eleven fresh data-only CLI calls and three portable tests passed. No programme
or native-kernel execution or performance measurement is involved.

## Revision4: lazy forms and prepared/result consumers

Select `--revision 4` explicitly for current form5 lazy Boolean spellings,
prepared reference/native API names, and the source-pinned native success JSON
reader. `profile11_extensions` identifies these paths and their guides; the
native call remains unsafe and requires separate exact-kernel admission. The
result reader executes no code and does not authenticate execution origin.
For form4, that profile11 section is unavailable without upgrading the source;
this does not disable or deny the separately documented prepared profile10 APIs.

Compatibility correction: adding lazy spellings initially leaked their names
into revisions1–3 through a dynamically inherited list. Revision4 restores the
original captured bytes for all prior form4/form5 revisions and both defaults;
only explicit revision4 advertises the new spellings. The default is still1.
Frozen prior-output hashes were not updated to accommodate the regression.
Sixteen data-only CLI observations checked eight prior/default packets, repeated
revision4 responses for both forms, and four refusals. No program or kernel was
executed, and this metadata conveys no execution authority or performance claim.
