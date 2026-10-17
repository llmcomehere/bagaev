# Run caller-reviewed source through checked CPython

This form5/profile11 command starts from source and raw Json arguments. It
compiles and verifies in the current process, then requires the emitted Python
bytes to match the caller's reviewed hash before creating the generated module.
It never accepts an artifact file or retained receipt as executable input.

This is a candidate execution route. Review the exact source, compiler/runtime,
checker, emitted Python and bounded execution environment separately. A digest
establishes identity; it does not grant permission or authenticate the source.
No Python sandbox, hostile-filesystem race resistance or production isolation
is claimed. Use a trusted source checkout with fresh standard-library imports.

## Two stages

First use the existing data-only compiler with a fresh output directory:

```sh
python -B -S tools/record_cpython_compile.py SOURCE \
  --source-sha256 SOURCE_SHA256 --checker /absolute/path/to/record-check \
  --checker-sha256 CHECKER_SHA256 --output /new/compile-directory
```

Review `artifact.json`'s Python text as data. Independently hash those exact UTF-8
bytes and retain the reviewed hash. Do not execute downloaded code merely
because a receipt supplies the same hash. Compilation invokes the explicit
checker but does not execute generated Python.

After separate execution authorization, use the same reviewed source and its
raw one-element Json argument array (or the entry's documented arity):

```sh
python -B -S tools/record_cpython_run.py SOURCE \
  --source-sha256 SOURCE_SHA256 --arguments ARGUMENTS.json \
  --arguments-sha256 ARGUMENTS_SHA256 --checker /absolute/path/to/record-check \
  --checker-sha256 CHECKER_SHA256 --python-sha256 REVIEWED_PYTHON_SHA256 \
  --output /new/run-directory
```

The runner checks and compiles afresh. A compiler/runtime or source change may
produce new Python bytes; review those bytes before supplying a new pin. Do not
silently replace the expected pin after a refusal. Assertions, `-B` and `-S` are
required. `PYTHONPATH` and `PYTHONHOME` must be unset. No package download or
background process is part of the command.

## Retained result and failures

Success returns one canonical receipt followed by a newline. The output has
exactly nine files: the compiler's six files under `compiled/`, plus
`arguments.json`, `result.stdout` and `receipt.json` at the root. The receipt
binds source, program, arguments, checker, generator/runtime, emitted Python,
runner and result identities. `execution_admission` remains false; the receipt
is an observation, not an authorization token.

A successful command may contain a completed language refusal, such as
`integer-overflow`. Inspect `result_status` and the complete result wire rather
than assuming every delivered receipt is a business success. Existing source,
argument and checker pins are checked before checker dispatch. A wrong Python
pin returns `CPY_RUN_PYTHON` after checking/compilation but before generated
module loading or evaluation. Existing output is refused, never overwritten.

Partial output is retained on failure. Malformed arguments can be refused by
preparation after the generated module was loaded. Interruption or missing
receipts do not prove that execution never started. `CPY_DELIVERY` means receipt
stdout failed after retained execution output; reconcile the retained data
instead of automatically rerunning the request.

The public `record_run_verify.py` currently understands reference-run bundles,
not this CPython bundle schema. Do not route these receipts through it or call
a matching collection of hashes independent authentication. This command does
not mutate application state, connect to a database, invoke a provider, support
profile12 or expand the compiler to every typed-record operation.

## Presence predicates

The companion lowering correction supports existing `json.is_text` and
`option.is_some` semantics. `json.is_text` tests bounded language Text, not merely
the JSON string kind: empty strings and up to256Unicode scalar values fit;
257scalars do not. It adds no text-byte work charge. `option.is_some` returns
true for Some(0), and false for None. Neither is a new language operation.

## Bounded acceptance, 17 October 2026

The first attempt to compile the [typed journey](https://github.com/llmcomehere/bagaev/blob/48e611d2270c482cf58b6c6d7823742dc24628db/docs/typed-journey.md)
with the preceding public subset returned `CPY_UNSUPPORTED` after a successful
source check. It performed no generated execution. The two presence predicates
above were the concrete missing lowerings; the task's expected values were not
changed to make compilation or execution pass.

After separate source, emitted-Python and harness review, the bounded run passed
45 fresh Python process cases and 22 Rust reference calls. Twenty-two
[presence cases](../examples/probes/cpython-presence/cases.json) matched literal
complete values and work, including operand-overflow propagation. Twelve typed
journey cases matched their retained complete reference wires; those earlier
reference calls were not repeated or counted as new runs.

The remaining eleven Python cases cover stale source/argument/checker pins,
existing output, wrong Python pin, malformed arguments, closed receipt stdout,
help, missing Python pin, unknown option and a deliberately cached-compiler seam.
Observed counters were 37 checker subprocesses, 36 generated module loads,
36 evaluate entries, 35 programme-driver entries and zero database connections.
Malformed arguments loaded a module but never entered its programme driver.
The closed-output control repeated one simple case and retained its result and
receipt; stdout delivery remains unknown. The cached sentinel was refused
before compiler dispatch and remained unchanged.

Nine earlier compile-only calls prepared the distinct programme texts for
review, and four separate helper-level unit methods passed. These preparations
are not additional generated programme executions. The wrong-profile branch is
statically reviewed but was not exercised by the 45-case run. Other unsupported
operations, hostile filesystem races and production isolation remain outside
this finite evidence.

The observed journey source hash was
`dbab1ba6b3fabcfc6031ad0b7f9e58a6950b8264b1d0e5e179251b5d14cdb65e`;
its reviewed emitted Python hash was
`76e9330c50a90431dd104a12653145b9fc97f1df34d577bbec6900348801e6a6`.
The selected compiler closure had generator
`8e5230db4d605729e0dc90ffce89fa3a27d4068f18b8118a0c6afbc524477974`
and runtime
`7ab92ba4ffb2a8721732075125ea20706457eb8a04e26a463e79cf40acbd0def`.
These identify this observation, not permission to execute a later artifact.
The observed work agreement is not an independent work oracle, performance
measurement, model-completion result or adoption claim.
