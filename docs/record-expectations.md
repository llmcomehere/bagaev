# Compare retained runs with explicit expectations

These tools are offline. They validate retained run consistency and compare it
with caller-selected expectations; they never invoke a checker or reference.
The caller must independently choose adequate expectations and trusted pins.

## One selected case

record_run_expectation.py takes RUN_DIRECTORY, --receipt-sha256,
--expectations FILE, --expectation-sha256, --case ID and --output NEW_FILE.
The output must be outside the bundle. Every case in the expectation document
is validated before the selected bundle is inspected.

Schema bagaev-record-run-expectations/1 has exactly schema, form and cases.
The form is record-form/5 or record-form/6. There are1–256 distinct ASCII case
IDs. Each case has id, arguments and expected. The expected projection contains
status, value_type, value, reason and location; expected invalid-ir is excluded.
The schema/1 comparison domain has strict Int64 tokens, with booleans distinct
from integers. Decimal/exponent arguments are outside that comparison domain.

Schema/2 keeps the same top-level keys but each case has id, arguments_raw,
argument_count and expected. arguments_raw is the full argument-array JSON text
inside a string; argument_count is an exact integer0..8, excluding bool.
The raw array is validated losslessly, without converting its number tokens to
binary floats. Its UTF8 bytes are then compared exactly, preserving whitespace,
key order, escapes, -0 and number spelling. The decoded outer string determines
the inner bytes; the raw expectation hash also binds outer document spelling.
No representation is inferred or converted automatically.

The source verifier separately checks actual entry arity. A wrong expected
argument wire refuses rather than silently testing another input. A valid
comparison reports matched or mismatched; both exit zero. Inspect status.
Result authentication and execution admission remain false. The outer single-case
report records application_expectation_checked=true because comparison occurred;
that is not proof that it matched or that the expectation was independent.

## Complete fixed set

record_expectation_set.py takes ROOT, --expectations FILE,
--expectation-sha256, --runs FILE, --runs-sha256, --source-sha256,
--program-sha256 and --output NEW_FILE outside ROOT. Each supplied case lives in
ROOT/CASE_ID. ROOT must contain exactly the supplied directories; each retains
the seven original run files. The runs document has exactly schema
bagaev-record-expectation-runs/1 and runs, an array of objects with case and
receipt_sha256. Unknown or duplicate IDs refuse.

The complete required case list comes from the pinned expectation document.
Any supplied mismatch yields mismatched. Otherwise omitted cases yield incomplete.
Only a complete matched set yields matched. These three report statuses exit zero;
refusals exit one. Reordering the runs manifest does not reorder results, but
changes its raw digest. A repeated receipt can satisfy identical obligations;
compared_cases counts comparisons, not independent executions. Empty supplied
evidence reports all cases missing and echoes unverified caller source/program pins.

## Bounds and trust

Expectation/runs documents and ordinary bundle members are limited to1MiB each;
stderr to4096bytes. Aggregate preflight retained payload is limited to64MiB and
reports to1MiB, inclusive. This does not bound all repeated I/O or CPU work.
Raw argument nesting is limited to128, counting the outer array as depth1.
Schema/2 additionally checks its embedded UTF8 byte length. Malformed JSON,
duplicate decoded keys, nonfinite tokens and unpaired surrogates refuse.

Aggregate preflight requires the run root, case directories and retained members
to be owned and nonsymlink. The single-case verifier checks file kinds/symlinks
but does not impose that ownership check.
Expectation/runs documents must be regular nonsymlink files; ownership is not
checked for those documents. Hostile same-user parent replacement races are
outside scope. Outputs are exclusive; a late write error can leave a partial file.

Schema/1 reports retain their established formats. Schema/2 reports use explicit
verification schema/2 and add argument_comparison="raw-utf8"; nested run reports
and runs-manifest versions stay unchanged. A coherently fabricated bundle can
match a supplied expectation. Neither tool proves provenance, universal semantic
correctness, an independent oracle or execution authority.

Portable tests: run_expectation_process_checks.py and
raw_expectation_process_checks.py each accept --output pointing outside the
source tree. The fixtures are synthetic consistency/expectation examples, not
new application executions. Public adaptations are not claimed to predate the
production implementation. No reference binary is needed for these tests.
Invoke each with `python3 -B -S`, using a different fresh output directory, for
example `python3 -B -S tests/probes/run_expectation_process_checks.py --output ../expectation-checks-new`.
Repeat with raw_expectation_process_checks.py and another fresh directory.
The `-B` flag prevents bytecode files from modifying the verified source tree.
