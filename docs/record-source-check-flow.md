# Check authored source in one retained workflow

`tools/record_source_check.py` joins decode, source-only checking and readable
refusal mapping. It supports form5 (/11, default) and explicit form6 (/12).
It never evaluates the submitted Bagaev program.

```sh
python -B -S tools/record_source_check.py Program.bagaev --form 6 \
  --checker /path/to/reviewed-record-check --checker-sha256 CHECKER_SHA256 \
  --output /new/check-directory
```

The checker must already be separately reviewed and authorized for execution in
an appropriate bounded profile. A SHA-256 pin establishes identity, not trust or
permission. This command does not download, build or sandbox the checker. Use
stable owned source/executable paths; hostile replacement races and arbitrary
descendant isolation are outside this profile.

## Retained result

The new directory contains exact source.bagaev, canonical program.json and raw
checker.stdout/checker.stderr. Refusals also produce location.json, preserving
exact/enclosing precision and explicit unmapped fallback. Invalid envelopes are
errors, not successful unmapped locations. A final receipt.json has schema
bagaev-record-check-flow/1, checked/refused status, selected form, five bare
SHA-256 identities (source, program, input, result, checker), checker_invoked=true
and execution_admission=false. Program and input identities bind the decoded
canonical input even when checking refuses. No result authentication is claimed.

Preflight rejects wrong binary pins, invalid syntax/profile and existing output
directories before dispatch. The source is limited to 1MiB and checker to 32MiB.
One checker child is captured incrementally, with 1MiB stdout and 4096-byte stderr
limits and a 15-second deadline after process creation. Timeout/overflow triggers
direct-child termination and at most 2 seconds cleanup wait. Process creation
itself and arbitrary descendants have no separate wall-clock guarantee here.

The original source, checker and retained artifacts are rechecked before the
receipt is written. Validation failure leaves no completion receipt but may leave
partial new files. Publication I/O failure may leave partial or fully written
receipt bytes and reports CHECK_FLOW_OUTPUT; existence alone does not establish
successful publication. This is not crash-atomic storage. Later stdout delivery
failure reports CHECK_FLOW_DELIVERY while preserving an already completed check.

## Evidence and limits

After separate review, seven test methods passed. Four literal workflows use
mocked checker results; negative controls cover wrong bindings, malformed JSON,
preflight refusals, retained-input mutation, unmapped root and delivery failure.
Four fixed Python child controls exercised actual bounded capture: oversized
stdout, oversized stderr, timeout and success. These are synthetic controls,
not Bagaev executions or real injected filesystem failures.

The portable `tests/probes/source_check_flow_process_checks.py` then passed four
actual workflow processes against the reviewed source-only checker: checked and
type-refused programs in each form. Complete verdict/receipt bytes and refusal
spans matched frozen literal expectations; source and checker were preserved.
Four checker calls follow from the inspected successful paths, not an independent
dispatch counter. Submitted-source evaluations: zero. Documentation CI is separate
from these local process observations; no performance or full-beta claim follows.
