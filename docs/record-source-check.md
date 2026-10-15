# Check a typed source without executing it

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

`tests/probes/record_source_check_v11.py` replays these frozen controls with an
explicit checker path/hash and a new output directory. A matching binary hash
does not grant execution authority. There is no performance or model-cost claim.
