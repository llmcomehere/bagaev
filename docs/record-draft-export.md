# From a focused draft to runnable input data

A focused function draft contains a candidate program, but is not source or an
execution permission. The explicit data-only `record_export.py` command closes
that handoff without asking users to manually strip envelope fields.

```sh
python tools/record_export.py original.bagaev --form 5 \
  --draft draft.json --base BASE_SHA256 --target TARGET_SHA256 \
  --output candidate.bagaev
python tools/record_text.py prepare candidate.bagaev --form 5 \
  --arguments arguments.json --output invocation.json
```

The exporter requires the original source and independently supplied expected
base/target pins. It recomputes the complete focused replacement instead of
trusting the draft's delta or flags. Exactly one existing function body may
change. Entry, types, function set, signature and all other bodies are preserved.
Forged metadata, stale pins, scope expansion, additional envelope fields and
true or non-boolean admission flags are refused. Output files must be new.

Form4 is the default; form5 must be selected explicitly. Each accepts only its
corresponding focused draft schema. Whole-program drafts with multiple edits or
added helpers are outside this exporter. The source formatter can subsequently
change whitespace while retaining decoded program identity.

Expected pins identify reviewed data, not who approved it. Neither command runs
a reference, persists application state, grants execution permission or proves
that the change meets a business requirement. An explicitly admitted reference
may later consume the prepared invocation under the operator's bounded profile.

## Observed end-to-end check

Both forms exported the exact pre-frozen single-function candidate. Sixteen API
refusals across the forms and five CLI operations passed, including existing
output preservation. The form5 output was actually fed to preparation, and its
invocation to the reviewed profile11 reference. The complete sixteen-entry
application response matched the existing frozen literal expectation. Original
source files remained unchanged. One runtime call was made by the separately
admitted check, not by the exporter or preparation command.

The portable `tests/probes/record_export_checks.py` accepts the existing explicit
reader/reference path/hash and new-output arguments. Establish execution
permission independently before running it. These are same-maintainer bounded
conformance observations, not independent reproduction or performance evidence.
