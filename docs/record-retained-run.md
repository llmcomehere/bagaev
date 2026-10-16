# Retain and verify a bounded source run

The standalone record_source_run.py accepts an authored source, exact source and
argument byte hashes, and a separately authorized reference executable with its
hash. It preserves seven files: source.bagaev, arguments.json, program.json,
invocation.json, reference.stdout, reference.stderr and receipt.json. The output
directory must be new. Inputs, executable identity, stream bounds and retained
bytes are checked; a delivery failure may leave useful partial evidence.

Form5/profile11 is the default; explicit `--form 5` is equivalent. Form6
requires `--form 6` and a separately authorized profile12 reference. A pin only
identifies bytes. It never grants permission to execute a binary or submitted
source, and the tool neither installs a runtime nor changes execution policy.
Every entry parameter must be Json. Raw JSON arguments preserve numeric tokens;
duplicate decoded keys, invalid JSON and unsupported source forms refuse.

A completed run can contain an application refusal, integer overflow or invalid
IR result. Inspect the typed result, not merely the wrapper exit status. The
receipt identifies retained bytes and claimed reference; it does not authenticate
execution, validate an independent application expectation or grant admission.

record_run_verify.py is offline. Supply the retained directory, explicit
--receipt-sha256 and a new --output file outside the bundle. It checks all seven
members, source decoding, arguments, invocation, result and receipt consistency.
It never invokes a reference. Internally consistent fabricated evidence can pass;
the output keeps authentication, application-expectation and admission flags false.

Core inputs/results have a1MiB cap, reference bytes32MiB and captured stderr4096
bytes. Processes run only under the caller's independently authorized bounded
profile. Symlink/file-kind guards do not claim protection against hostile
same-user parent-directory replacement races or system compromise.

Reproducible tests are in test_record_source_run.py, test_record_run_verify.py
and test_source_run_form6.py. Their reference captures are mocked. The optional
retained_run_process_checks.py takes --reference11, --reference11-sha256,
--reference12, --reference12-sha256 and --output outside the source tree. It
checks seven form5 fixtures under both default and explicit selection, plus27
form6 fixtures, with one offline verification per run. Expected logical work is
retained fixed-profile evidence, not a new performance measurement. Functional
qualification is separate from documentation-only CI and formal integration.
