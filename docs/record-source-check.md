# Check a typed source without executing it

## Explicit form6 / profile12 option

For typed-record/12 program JSON, select `check --profile 12 --input FILE`.
The unchanged command without this option remains /11; there is no automatic
profile detection. Decode authored form6 with explicit `--form 6` beforehand.
The result schema is bagaev-record-source-check/12, with the same input binding, false admission
and checked/refused/environment distinction. The library adds check_source_v12.
This checks general source signatures without the Json-only preparation limit.

Eight profile cases passed, including the existing ActiveJson application,
json.bool_or, wrong-profile refusals, invalid fallback type, unused-helper type
error and non-Json entry parameters. All13 existing /11 verdicts and2I/O controls
also passed with the new executable, preserving default output bytes. No source
program was evaluated. The portable /12 harness reuses the same controls.
The separate source-location join currently supports /11 envelopes only; selecting
/12 does not silently broaden that mapper. Profile-specific malformed-option and
oversized-input cases were not separately rerun beyond shared /11 transport checks.

The experimental source-only checker accepts `bagaev-typed-record/11` program
JSON, including inventory entry points with Stock, Text and Int64 parameters.
It does not need runtime arguments. It checks every function, including unused
helpers, using the existing /11 structural, reference, cycle and type rules.

After separately establishing build/execution authority for the checker:

```sh
rustc --edition=2021 examples/probes/backend/rust/record_check_main.rs -o record-check
python -B -S tools/record_text.py decode selected.bagaev --form 5 --output program.json
./record-check check --input program.json
```

A selected source can first be recovered from a portable revision package.
The decoder establishes syntax; this explicit checker establishes the declared
bounded semantic rules. Neither action admits the program for execution.

The result schema is `bagaev-record-source-check/11`. A checked result contains
the canonical program hash as bare lowercase hexadecimal, null reason/location,
and `execution_admission:false`. A source refusal contains null program hash and
the stable checker reason/location. Both are protocol results with exit0.
Usage, input I/O and checker environment failures exit1 with stderr, without
manufacturing a source verdict. Input frames are limited to1MiB. Inherited file
transport assumes stable owned paths; it does not promise hostile-race isolation.
Each complete in-bound input is bound by `input_sha256`, the bare hash of its
actual transport bytes. Whitespace changes this hash without changing canonical
program identity. Oversized input reports null because only a bounded prefix
was read. This linkage does not authenticate the result producer.

The library entry is `typed_record::check_source_v11`, returning the existing
SourceCheck checked/refused representation while keeping environment failure
separate. It never constructs Runtime or evaluates source expressions. Therefore
a well-typed MAX_INT64+1 expression checks successfully, although evaluating it
would overflow. Successful checking is not totality, business acceptance, producer
authentication or permission to run.

Eleven real checker CLI observations covered two existing inventory revisions,
scalar and overflow-expression checking, incorrect main/unused-helper types,
missing calls, wrong profile, extra fields, malformed JSON and oversized input.
Two usage/I/O controls verified exit1 and no stdout. Exact output bytes and
input preservation were checked. The first local attempt exposed an internal
`sha256:` tag mismatch, corrected to the specified bare hash before the passing
run. These observations execute the checker, not the submitted programs.
The input-binding successor passed thirteen verdict cases, adding whitespace
and changed-program identity controls, plus the same two usage/I/O controls.
Earlier eleven-case observations are historical, not additional semantic cases.

`tests/probes/record_source_check_v11.py` replays these frozen controls with an
explicit checker path/hash and a new output directory. A matching binary hash
does not grant execution authority. There is no performance or model-cost claim.
