# Change the readable catalogue without changing its result

The fixed form4 diagnostic and detached-draft tools extend the existing pure
workflow to the complete [readable catalogue](pure-json-form.md). Select --form4
explicitly; both tools still default to1 and do not auto-detect source versions.
The form1 API and its contracts are unchanged.

```console
python3 -B tools/record_diagnose.py Catalog.bagaev --form 4 --output syntax.json
python3 -B tools/record_draft.py Catalog.bagaev Candidate.bagaev --form 4 --base BASE_PIN --target TARGET_PIN --output draft.json
```

Use `record_text.py inspect --form 4` to obtain identities for the sources you
independently selected. Diagnostic locations are syntax context, not type errors.
The returned draft fixes the entry/type graph and existing function signatures,
refuses stale pins/removals/no-op, and reports false semantic/admission flags.
It does not publish, apply, store or execute the candidate.

The example extracts `id_ok`'s body into `id_ok_body`. The old function calls the
helper with the same Text argument and keeps its Bool result. The detached delta
adds one function and replaces one body; the candidate has25functions. Every one
of the existing99literal catalogue responses is compared after actual candidate
execution by a separately reviewed reference. This is behavioral preservation
for that finite corpus, not proof for all possible inputs or lower cost.

The portable `catalog_edit_workflow_checks.py` checks the draft/pins, syntax
identity, two file CLI calls, stale-base refusal,99reference calls and preserved
source/input bytes. Existing form1 diagnostic/draft suites are retained as
compatibility controls. Business refusal remains a complete application payload,
not a successful language refusal. No native or production acceptance is added.

For replacing a single existing body, [focused function fragments](focused-function-edits.md) avoid resending unrelated bodies.
