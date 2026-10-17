# Portable form6 source history

Use `tools/record_revisions.py --form 6` for explicit form6 history. The default
remains form5; neither path auto-detects or migrates a package. This extends
[the portable source history](record-revisions.md), not the durable Store or
application-state protocol.

```sh
python -B -S tools/record_revisions.py init Program.bagaev --form 6 \
  --source-sha256 RAW_SOURCE --program-sha256 DECODED_PROGRAM --output first.json
python -B -S tools/record_revisions.py append first.json --form 6 \
  --source Changed.bagaev --source-sha256 NEW_RAW --program-sha256 NEW_PROGRAM \
  --package-sha256 FIRST_PACKAGE --head FIRST_HEAD --output second.json
python -B -S tools/record_revisions.py inspect second.json --form 6 --output view.json
python -B -S tools/record_revisions.py checkout second.json --form 6 \
  --revision FIRST_HEAD --output Original.bagaev
```

Supply independently selected lowercase SHA-256 pins. Source pins bind exact
UTF-8 bytes; program pins bind canonical decoded typed-record/12 JSON. Package
pins bind canonical package bytes. The new schema is bagaev-record-revisions/2
with form record-form/6. Each revision identity hashes canonical JSON containing
form, parent, source_sha256 and program_sha256. Legacy identities remain unchanged.

The library module is `bagaev_record_revisions_form6`, with initialize, append,
inspect, checkout, loads and validation helpers. Every checkout validates the
whole history, including later revisions. Adjacent unchanged decoded programs
refuse, even if whitespace differs; a real A→B→A revision remains possible.
The input package is preserved and appended results are detached.

Raw source, raw serialized package and canonical package output are bounded to
1MiB. Histories contain 1–16 linear revisions. JSON nesting/structure is bounded;
duplicate keys, numeric package values and malformed Unicode refuse. Outputs
must be new paths; existing output is never replaced. This does not promise
crash-atomic publication, shared mutable heads or external-state recovery.

Retention checks syntax and identity only. For example, a syntactically legal
`json.bool_or(x, 0)` can be retained although a separate type checker refuses it.
semantic_check and execution_admission remain false. Nothing here checks types,
authenticates source or executes the submitted program.

Five bounded new test methods and eight unchanged form5 methods passed after
separate review. Literal ASTs and independent profile-bound identities constrain
fresh-session restore, stale-base refusal, profile separation, no-op imports,
tampered later history, sixteen/seventeen revision bounds, hostile JSON and CLI
output preservation. One default canonical package equals the unchanged legacy
API output. The canonical-size case establishes early oversized-package refusal;
it does not establish acceptance at the maximum size. No checker or submitted
program evaluation was performed by these tests.

## Separate-process continuation

`tests/probes/form6_continuation_checks.py` additionally exercises init, append,
fresh checkout, decode, source-only /12 check and form6 diagnostic mapping as
separate processes. It requires a separately reviewed checker binary with its
SHA-256 pin, a separately reviewed diagnostic source tree and a fresh output
directory. It does not build or download dependencies. The diagnostic tree is
not hashed by this harness; acceptance assumes the reviewed tree stays unchanged.

```sh
python -B -S tests/probes/form6_continuation_checks.py \
  --checker /path/to/reviewed-record-check --checker-sha256 CHECKER_SHA256 \
  --diagnostic-root /path/to/reviewed-form6-diagnostics --output /new/output
```

One bounded run passed eleven process calls: two revision writes, two
checkout/decode/check chains, actual-result location mapping, later-history
tamper refusal and existing-output refusal. It made two source-only checker
calls and zero submitted-source evaluations. The first revision checks; the
retained integer-fallback successor refuses RR_TYPE and maps to its zero.
Recorded inputs, packages, outputs and checker binary were preserved. This is
bounded CLI handoff evidence, not complete beta acceptance or crash durability.
