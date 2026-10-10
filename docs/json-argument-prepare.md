# Lossless preparation for Json-only entries

The existing record_text prepare route intentionally accepts only Int64 JSON
numbers. That is suitable for its strict typed-argument transport, but rejects
fractional or larger numeric values inside a Json argument before an application
can inspect and refuse them.

The separate [record_json_prepare.py](../tools/record_json_prepare.py) route
requires explicit form4/profile10, form5/profile11 or form6/profile12 and an entry whose
parameters are all Json. A zero-argument entry is allowed. It keeps existing
source codecs and the old preparation route unchanged.

Arguments must be one complete UTF-8 JSON array of exact entry arity. Duplicate
decoded object keys, unpaired surrogates, non-JSON NaN/Infinity, trailing content,
invalid syntax and argument nesting over 128 refuse. Source and argument files
use the existing regular-file/no-follow input reader. Each input and the complete
emitted invocation are bounded to one MiB. Output creation is exclusive.

Numeric tokens are opaque during syntax validation. They are not converted to
binary floating point, rounded or coerced to Int64. The complete original argument
bytes, including whitespace, exponents and negative zero, are embedded unchanged
beside a canonical programme. Returned SHA-256 identities cover programme,
arguments and complete invocation. They grant no semantic or execution admission.
Runtime input and semantic bounds still apply independently.

## Explicit usage

After separately reviewing the selected source and data:

    python tools/record_json_prepare.py       examples/probes/inventory-json/Reserve.bagaev       --form 5 --arguments arguments.json --output invocation.json

The tool constructs data only. It never launches a reference, compiler, kernel or
network request and does not select an execution profile. Execution of the output
requires separate authority and the existing checked runtime.

For the explicitly versioned Boolean operation and JSON active-total specimen:

    python tools/record_json_prepare.py examples/probes/json-active-total/ActiveJson.bagaev --form 6 --arguments arguments.json --output invocation.json

Here arguments.json contains an outer argument array with the application's item
array as its sole element. Form6 never falls back to form5, and selecting form6
for a form5 source refuses. This adds no native execution or prepared native12 API.

## Checks and scope

Thirteen literal argument cases were frozen before implementation. Five data-only
tests cover those cases, depth and UTF-8 boundaries, both explicit profiles,
byte-preserved numeric lexemes, exact arity, typed-entry refusal, exclusive output
and final-frame size. The unchanged old parser still refuses fractional and
out-of-Int64 numbers. An initial invalid Python test-string escape warning was
fixed; the five final tests passed with warnings treated as errors.

Forty-five CLI calls checked the thirteen transport cases and prepared all
thirty-two accepted inventory-envelope cases. Each successful output retained
the complete original argument bytes. All thirty-two prepared inventory
invocations then passed the already admitted reference11 with complete expected
outcomes, including the fractional/large-number application refusals.
This does not change the earlier typed preparation refusal or claim universal
Json-runtime acceptance, native execution by this tool, or performance benefit.

On 2026-10-10 the explicit form6 extension passed three new and five unchanged
data tests with Python warnings treated as errors. Twenty-three actual CLI calls
preserved the JSON active-total argument bytes, including -0, -0.0 and1e0 tokens.
All23 resulting invocations matched the previously recorded complete reference12
responses. These are new reference calls, not native calls or performance results.
