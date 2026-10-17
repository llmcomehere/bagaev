# Read retained CPython results offline

The CPython source runner produces a nine-file bundle. These two commands read
that bundle as data, without invoking the checker or executing its Python text.
Use a trusted checkout in a fresh process, with assertions enabled, `-B -S`,
and `PYTHONPATH` and `PYTHONHOME` unset. Do not import the reader and then run a
compiler in the same process. This guide depends on the pinned source-run route.

## Check consistency

```sh
python -B -S tools/record_cpython_run_verify.py RUN_DIRECTORY \
  --receipt-sha256 RECEIPT_SHA256 --source-sha256 SOURCE_SHA256 \
  --program-sha256 PROGRAM_SHA256 --arguments-sha256 ARGUMENTS_SHA256 \
  --runner-sha256 RUNNER_SHA256 --output NEW_REPORT.json
```

Supply identities retained by the caller. Obtaining every expected hash from an
untrusted bundle would only check that the bundle agrees with itself. A report
with `status: consistent` checks exact membership, bounded metadata, source and
program identity, raw arguments, receipt links and result-wire shape. It does
not authenticate the producer, regenerate Python, independently check programme
semantics, establish freshness, or grant execution permission.

Someone who replaces the artifact text and all dependent hashes can still
produce a consistent bundle. The reader deliberately never executes that text.
Nested result values are not independently validated against nominal language
types. Use a separate literal expectation to test the required business result.

## Compare an independent expectation

```sh
python -B -S tools/record_cpython_run_expectation.py RUN_DIRECTORY \
  --receipt-sha256 RECEIPT_SHA256 --source-sha256 SOURCE_SHA256 \
  --program-sha256 PROGRAM_SHA256 --arguments-sha256 ARGUMENTS_SHA256 \
  --runner-sha256 RUNNER_SHA256 --expectations EXPECTATIONS.json \
  --expectation-sha256 EXPECTATIONS_SHA256 --case CASE_ID \
  --output NEW_COMPARISON.json
```

The expectation document uses `bagaev-record-run-expectations/2` and
`record-form/5`. Each case has `id`, `arguments_raw` (the exact UTF-8 JSON text),
`argument_count`, and `expected`. Expected fields are `status`, `value_type`,
`value`, `reason`, and `location`. Work is an observation, excluded from this
business-result comparison. JSON whitespace in `arguments_raw` matters.

Both `matched` and `mismatched` mean that comparison completed and return exit
zero. Inspect the report status. Comparison is recursively type-exact, so true
does not equal integer 1. Invalid input or a stale pin returns exit one; usage
errors return two. The command cannot prove that the expectation was authored
independently: choose and review it separately from the implementation.

## Output and failure boundaries

Reports must be new files outside the input bundle, with trusted, existing
parent directories. Existing files are refused. These helpers do not defend
against a hostile filesystem racing path checks or changing report ancestors.
Partial reports can remain after a write, close, preservation or readback error;
retain and inspect them rather than assuming a failed command wrote nothing.

A partial run bundle is refused. Missing receipts do not prove that execution
never started. A complete bundle retained after stdout delivery failed can be
read without repeating the application. A completed language refusal, such as
integer overflow, can also be consistent; consistency is not business success.

These commands do not add a receiver, database, provider connection, profile12
support, execution sandbox, model evaluation or cost claim.

## Finite acceptance, 17 October 2026

The separately reviewed data-only acceptance completed 89 fresh process cases:
35 complete retained bundles, 34 independent literal comparisons, 16 verifier
controls and four comparison controls. The bundles include the prior runner's
closed-output case and a completed integer-overflow result. No checker dispatch,
generated execution, programme evaluation or database attempt was observed.

Wrong pins, extra/missing members, duplicate receipt keys, Boolean invocation
counts, source drift, invalid Bool results, partial bundles and occupied or
inside-bundle report targets were refused. A fully rebound inert artifact
remained consistent. A wrong Bool result and a nested integer replaced with true
were reported as mismatched. Raw-argument whitespace and a wrong expectation
pin were refused. Original source and retained packets remained byte-identical.

These synthetic mutations demonstrate the stated boundaries; they are not new
application executions or naturally observed application failures. The 34
expected results come from the earlier frozen presence and typed-journey cases.
No independent work-cost oracle or model outcome is claimed.

The compact portable controls are explicitly synthetic, without a real checker
receipt or authentic compiled artifact. Run them separately with:

```sh
python -B -S tests/probes/cpython_retained_process_checks.py
```

They exercise inert-artifact consistency, literal matching and mismatching,
type-exact comparison, stale pins, raw argument identity and report overwrite
refusal. They are a separate process check, not implicitly included by unittest
discovery, and do not repeat the prior application qualification.

## Locate a retained failure in readable source

Use `tools/record_cpython_run_location.py` for a failed form5/profile11 run.
It first performs the same nine-file verification above, then maps the retained
runtime pointer against the verified source bytes. It never executes the Python
stored in the artifact or reruns the application.

```sh
python3 -B -S tools/record_cpython_run_location.py RUN_DIRECTORY \
  --receipt-sha256 RECEIPT_SHA256 --source-sha256 SOURCE_SHA256 \
  --program-sha256 PROGRAM_SHA256 --arguments-sha256 ARGUMENTS_SHA256 \
  --runner-sha256 RUNNER_SHA256 --output NEW_LOCATION_REPORT
```

Select all five pins independently. Use a new output path outside the bundle.
Even help inherits the runner's fresh `-B -S` profile, with assertions and no
`PYTHONPATH` or `PYTHONHOME`. These flags do not provide isolation.

The report keeps the verified run identity, runtime status/reason/work and exact
pointer. A matched expression includes its exact or enclosing precision, UTF-8
byte range and one-based Unicode-scalar line/columns; the end is exclusive.
Excerpts contain at most 256 Unicode scalars, with explicit truncation. A valid
unmatched pointer produces `unmapped` with no invented range. Success is refused
with `CPY_LOCATION_STATUS`; this command describes failures only.

Matching a location does not authenticate the retained failure or prove causality.
All semantic-check, authentication, freshness and execution-admission flags stay
false. The report is bounded to 64 KiB. The old scalar capture locator remains a
separate command and format. No form6/profile12 support is implied.

On 17 October 2026, three fresh acceptance processes passed 2, 3 and 28 controls
respectively, including 16 CLI-main calls. One existing operand-overflow packet
mapped to the independently counted expression `9223372036854775807 + 1`
at bytes [88,111), line 2, columns [67,90). This reuses a retained observation;
no application was rerun. The complete report matched a frozen expectation.

Controls covered success refusal, all five stale bindings, missing/tampered
packets, output preservation, pin/output error precedence, Unicode layout,
repeated expressions, explicit unmapped pointers, excerpt/report bounds and
labelled malformed-map seams. No checker, compiler, generated evaluation,
database or network dispatch was observed. Inputs remained unchanged.

Portable tests in `tests/probes/cpython_location_process_checks.py` use inert,
synthetic records, including invented failure pointers. They do not claim those
failures really occurred. Run them separately under an authorized bounded profile:

```sh
python3 -B -S tests/probes/cpython_location_process_checks.py
```
