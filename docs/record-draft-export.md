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

## Preserve unrelated source layout (form5 opt-in)

For a focused body change, add `--preserve-layout --source-sha256 HEX` to the
existing form5 export command. `HEX` is the lowercase SHA-256 of the exact original
UTF-8 file, in addition to the existing base and target program pins. Both flags
are required together, and other forms refuse the option before reading input.

The exporter first runs the complete existing focused-draft validation: base,
target, packet reconstruction, single changed function and unchanged signature.
It then uses exact source-map root-body ranges to replace only that expression
slice. Every byte outside it is preserved, including unrelated functions,
declarations, comments, CRLF and whitespace. Comments inside the intentionally
replaced expression can be replaced. This is not a promise to preserve that
body's annotations. There is no heuristic text or brace matching.

The complete result must decode to the accepted target graph before the existing
exclusive output writer is used. Stale raw-source pins, invalid scope/packets,
coarse/missing ranges and oversized output refuse without partial output. The
explicit receipt adds `input_source_sha256` and
`preservation_scope:"outside-changed-function-body"`. Default canonical export
and its receipt remain unchanged. The pure library entry is
`export_source_preserving_layout` in `bagaev_record_export`.

Five layouts of the existing batch-to-total10 change (LF, Unicode comments,
CRLF, lazy guards and named calls) preserved exact prefix/suffix bytes and the
same target graph. Nine data CLI observations and six library refusals passed.
The unchanged legacy export regression separately passed both forms, 16 refusals,
five CLI calls and one existing reference case. No new target semantics, native
execution or measurement is claimed by preserving source text.

### Retain the replacement's authored expression

Add `--replacement-source FRAGMENT` to the form5 `--preserve-layout` command
when the replacement body should keep its authored spelling and internal
comments. The fragment must independently reconstruct the exact validated draft:
only the selected existing function, unchanged declarations/signature, and the
same pinned target. A merely similar fragment is refused.

The library entry is `export_source_with_fragment_layout`. It performs the
existing complete layout-export validation, checks fragment reconstruction, then
splices the fragment's exact root expression bytes into the original body range.
Both ranges must be exact. The complete result is size-bounded and decoded again
against the target. Every byte outside the original expression stays unchanged.
Leading/trailing fragment trivia outside its expression range is excluded;
interior comments, Unicode and CRLF survive. Fragment comments remain untrusted
data and confer no execution authority.

The extra flag without layout mode, paired source hash and explicit form5 is
refused before input. Existing input readers and no-overwrite output writer are
unchanged. Only this opt-in receipt adds `replacement_source_sha256` (the entire
fragment file) and `replacement_scope:"body-expression"`.

A standalone single-function fragment still needs positional calls to external
functions: named calls require declarations in that same source. A named self-call
can be preserved as data, but this says nothing about its runtime admissibility.
This option does not weaken signature or scope checks to accommodate missing
callee context.

Six portable tests cover literal Unicode/CRLF spliced bytes, unchanged inputs,
packet/pin/fragment refusals, declared named spelling as data, paired CLI flags,
combined output bounds and existing-output preservation. Existing layout and
annotated-walkthrough tests retain their frozen hashes. No program was executed.
