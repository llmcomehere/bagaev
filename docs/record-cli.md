# Authored-record command entrypoint

`python3 -B -S tools/record.py --help` lists existing authored-record stages.
The launcher selects one delegate lazily and forwards its remaining arguments.
It does not change language semantics, output formats, resource bounds or authority.
The existing `src/bagaev.py` command family remains the separate L2 interface.

| Command | Existing delegate and boundary |
| --- | --- |
| `check` | `record_source_check.py`: explicit source, form, checker and pins; no evaluation. |
| `run` | `record_source_run.py`: reference execution, form5 default or explicit form6; requires its own reviewed execution scope. |
| `inspect` | `record_text.py inspect --form 5`; pass `--form 6` explicitly for form6. |
| `diff` | `record_source_diff.py`: pinned form5 source/structural comparison, not semantic equivalence or an apply packet. |
| `function` | `record_function.py`: extract/context/replace. Replace emits a draft packet. |
| `draft` | `record_draft.py`: restricted multi-body packet, forms1/4/5 only; not applied source. |
| `export` | `record_export.py`: validate and export a draft to new source. |
| `compile-cpython` | `record_cpython_compile.py`: form5/profile11 checked artifact, never generated execution. |
| `preview-cpython` | `record_cpython_preview.py`: exact form5 compile-packet Python text for review, never execution or authentication. |
| `run-cpython` | `record_cpython_run.py`: fresh checked source execution with separately reviewed emitted-Python pin; requires its own authorized profile. |
| `locate-cpython-failure` | `record_cpython_run_location.py`: retained form5/profile11 bundle failure location, descriptive only. |
| `verify-cpython-run` | `record_cpython_run_verify.py`: nine-file CPython bundle consistency, no execution or authentication. |
| `verify-cpython-run-expectation` | `record_cpython_run_expectation.py`: raw-argument identity and literal expected-result comparison, no execution. |
| `history` | `record_revisions.py`: form5 default or explicit form6 portable history. |
| `history-store` | `record_history_store.py`: explicit form, local candidate storage, not acceptance or admission. |
| `verify-run` | `record_run_verify.py`: retained-run consistency, not authentication. |
| `verify-run-expectation` | `record_run_expectation.py`: one run against supplied expectations. |
| `verify-expectation-set` | `record_expectation_set.py`: complete supplied obligation set, including missing evidence. |
| `check-location` | `record_check_location.py`: bind a checker refusal to explicit form5/form6 source. |
| `failure-location` | `record_failure_location.py`: older scalar-capture failure mapping; not a CPython run bundle. |
| `format` | `record_format.py`: token-preserving source formatting. |
| `diagnose` | `record_diagnose.py`: source syntax diagnostics. |
| `source-map` | `record_source_map.py`: explicit form5/form6 and source/program identities. |

Use the delegate's documented flags and return codes. For example, replacing
`tools/record_source_check.py` with `tools/record.py check` preserves all subsequent
arguments. Replacing `tools/record_revisions.py` with `tools/record.py history`
preserves its operation and flags. No argument names are guessed or normalized.

A data-only inspection, under an authorized profile:

```sh
python3 -B -S tools/record.py inspect SOURCE.bagaev --form 5 --output NEW_INFO.json
```

Inspect defaults to form5; an explicit later `--form` option follows the existing
delegate's last-option behavior. Other routes keep their own form requirements.
Use separate fresh invocations for compilation. The launcher does not unload
project modules or hide a stale compiler import. `-B -S` alone is not a sandbox.

Use one command per fresh process. In particular, do not call a retained reader
and then compilation or execution in the same Python process. Existing delegates
keep their own import-integrity checks; the launcher never clears their caches.
See [CPython source runs](record-cpython-run.md) and
[offline CPython readers](record-cpython-retained.md). A matched result or a
consistent bundle supplies no execution authorization. For retained-expectation comparisons,
both matched and mismatched return zero; inspect the report status.

The launcher has no generic authored `patch` or LLVM `compile` command.
The bounded form5 [source diff](record-source-diff.md) reports review data only.
Use function/draft/export as explicitly named stages; packet creation and source
application are different actions. Form6 CPython execution is not introduced here.
Global `--help`/`-h` imports no project module. Empty or unknown commands return2
with `RECORD_COMMAND` on stderr; selected delegates retain their own diagnostics.

See [source checks](record-source-check-flow.md), [retained runs](record-retained-run.md),
[portable histories](record-revisions.md), [form6 histories](record-revisions-form6.md),
[CPython artifacts](record-cpython.md) and [expectations](record-expectations.md).
Compilation, pins, packets and consistency checks do not grant execution authority.

The data-only facade probe is `tests/probes/test_record_frontdoor.py`. Invoke it
by absolute path with `python3 -B -S` from a fresh working directory outside the
checkout. It retains `frontdoor-inspection/` there and refuses to reuse that
fixture directory. Its run/storage route tests use stubs; they do not execute a
program or mutate a database. Source-check and compilation need their separately
reviewed pinned-checker process profiles.
