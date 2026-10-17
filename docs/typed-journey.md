# One typed change, diagnosis and continuation

For the same change through the current authored CLI and one explicitly
authorized CPython run, see [the CPython continuation companion](typed-journey-cpython.md).
It preserves this twelve-case oracle and adds a focused retained-reader recipe;
it does not turn the historical reference evidence below into new executions.

This focused exercise composes existing public form5/profile11 tools. Starting
from [BatchLimited](../examples/probes/inventory-batch-change/BatchLimited.bagaev),
add a cumulative per-SKU limit of six. Keep the existing per-order maximum five
and batch-wide maximum ten. Equal limits succeed. Existing reservation failures
win first; after a successful reservation proposal, the per-SKU limit wins over
the global limit. Rejection returns the original complete stock and failing
zero-based step. All behavior is pure returned data, with no external inventory
transaction.

Only `batch_apply` changes. The [fragment](../examples/probes/typed-journey/PerSku.fragment.bagaev)
sums earlier receipt amounts for the current SKU, adds the current amount, and
then applies the existing global check. The [twelve-case literal oracle](../examples/probes/typed-journey/cases.json)
was fixed before authoring the fragment. Eight cases belong to the first process;
four different cases belong to a fresh continuation process. Cases cover limits,
failure precedence, rollback and complete receipt values.

## Data preparation

Use a fresh output directory. The commands below inspect and transform source;
checking additionally requires a separately authorized checker. Digest matches
establish identity, not execution permission.

```sh
mkdir typed-journey-output
SOURCE=examples/probes/inventory-batch-change/BatchLimited.bagaev
FRAGMENT=examples/probes/typed-journey/PerSku.fragment.bagaev
BASE=b4755a73e1090e2b4ed563f42c29250dc759c5b1224d3c5765a239cb6584351e
FUNCTION=7c2d12d8944682ca1ee7717de1a9e5fcc77477a3885472e8f75e032b5bba9c31
TARGET=77e72b2cab462713df4e4d56febe3709f49423ca16a62963969c3d049a022042
SOURCE_SHA=8caccd806134b0a96cf10492e3aac5ac14a18212f0e2cb4303feea7187dc8e88
python tools/record_function.py context "$SOURCE" --form 5 --name batch_apply --source-body --output typed-journey-output/context.json
python tools/record_function.py replace "$SOURCE" --form 5 --replacement "$FRAGMENT" --base "$BASE" --function-pin "$FUNCTION" --output typed-journey-output/draft.json
python tools/record_export.py "$SOURCE" --form 5 --draft typed-journey-output/draft.json --base "$BASE" --target "$TARGET" --preserve-layout --source-sha256 "$SOURCE_SHA" --replacement-source "$FRAGMENT" --output typed-journey-output/PerSku.bagaev
```

The exported source SHA256 is
`dbab1ba6b3fabcfc6031ad0b7f9e58a6950b8264b1d0e5e179251b5d14cdb65e`.
Every byte outside the original `batch_apply` expression stays unchanged.
The expression's authored spelling is preserved. This was checked against an
independent literal source splice, not merely a decoded graph comparison.

## Diagnosing a valid but incorrect change

For an intentional negative control, replace the fragment's one
`text.eq(record.field(earlier, "sku"), sku)` expression with `true`. This sums all
SKUs for the new six-unit limit. The source remains well-typed, so a semantic
checker alone cannot establish that it implements the requested business rule.
The `cross10` case, five units of each of two SKUs, distinguishes the changes:
the correct result commits; the control rejects on its second request.

Use `record_source_run.py` with separately authorized, pinned reference and
argument bytes. Compare retained results with `record_run_expectation.py` and
inspect its `status`: both `matched` and `mismatched` are successfully produced
reports. A zero exit code alone does not mean the application expectation passed.
This control is deliberate, not an observed natural model mistake.

## Continuation boundary

Use `record_revisions.py init` for the original source and `append` for the
changed source with exact package, head, source and program pins. In a fresh
process, validate and `checkout` the retained head. Require checkout bytes to
match the changed source pin before running the four successor cases. Reverify
retained predecessor bundles as well. A source-history package carries source
identity and lineage; it grants no execution authority and stores no real stock.

This exercise requires no new application-state receiver or store. Existing
public tools suffice without the optional facade. No model usability, adoption,
speed or cost advantage follows from a finite same-maintainer replay.

## Execution evidence

On 17 October 2026 the reviewed bounded replay passed 45 public CLI calls:
seven preparation calls, twenty predecessor calls and eighteen fresh-process
successor calls. Two source-check paths accepted both well-typed changes.
Eight predecessor and four successor application cases matched their complete
literal outcomes. One additional reference run produced the intended wrong
control's successful `BatchRejected` value, which expectation comparison marked
`mismatched`. The successor also reverified all nine predecessor bundles without
rerunning them. There were thirteen fresh reference executions in total.

The portable history contained two revisions. Its checked-out head matched the
changed source bytes and program digest. No complete repository copy was made
for either phase, and no new state receiver, native backend, generated Python,
database mutation or model/provider call was involved.

The context packet was 30,893 bytes, the authored fragment 3,869 bytes, exported
source 9,235 bytes and detached draft 11,266 bytes. These are exact artifact byte
counts, not token counts, total model context, latency, cost or usability scores.
The run used an existing bounded profile; its successful reference work counts
are observations rather than an independent resource oracle.

The portable tests check the frozen partition, exact one-function replacement,
outside-body source preservation and in-memory history roundtrip. Running those
tests does not repeat the recorded reference executions or demonstrate a new
fresh-process continuation.

## Complete local replay recipe

The following Linux/Bash recipe continues after the three preparation commands.
Run it only where compiling these sources and executing the reference are
separately authorized. It uses Python 3 and an installed Rust compiler, with no
package download. The recorded build used Rust 1.93.0, edition2021 and no added
optimization flag. A different build may have different binary bytes: pin your
own authorized output rather than treating the recorded binary hash as portable.

```sh
set -eu
OUT=typed-journey-output
rustc --edition=2021 examples/probes/backend/rust/record_wide_main.rs -o "$OUT/record-reference"
rustc --edition=2021 examples/probes/backend/rust/record_check_main.rs -o "$OUT/record-check"
CHECK_SHA=$(sha256sum "$OUT/record-check" | cut -d' ' -f1)
python tools/record_source_check.py "$OUT/PerSku.bagaev" --form 5 --checker "$OUT/record-check" --checker-sha256 "$CHECK_SHA" --output "$OUT/check"
```

Convert the literal task oracle into the existing expectation-tool schema and
one-element argument arrays. This step performs no application execution.
Exclusive file creation refuses an accidental replay over existing outputs.

```sh
python - <<'PY'
import json
from pathlib import Path
out = Path('typed-journey-output')
rows = json.loads(Path('examples/probes/typed-journey/cases.json').read_bytes())['cases']
def put(path, value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    with path.open('xb') as stream:
        stream.write(raw)
expected = {'schema': 'bagaev-record-run-expectations/1', 'form': 'record-form/5', 'cases': []}
for row in rows:
    put(out / (row['id'] + '.arguments.json'), [row['request']])
    expected['cases'].append({'id': row['id'], 'arguments': [row['request']], 'expected': {
        'status': 'success', 'value_type': 'Variant:BatchOutcome', 'value': row['value'],
        'reason': None, 'location': None}})
put(out / 'expectations.json', expected)
PY
printf '%s  %s\n' e3d64d1456cfeeb5e6588d5e5c03229c289ed0ae9a72672c0f118340b43e2508 "$OUT/expectations.json" | sha256sum -c -
```

For the following commands, put this short shell helper in the new output
directory. It invokes only the existing public run and expectation tools.
Its arguments are source path, case ID, unique output label and expected status.

```sh
cat > "$OUT/run-case.sh" <<'SH'
#!/bin/sh
set -eu
OUT=typed-journey-output
SOURCE=$1
CASE=$2
LABEL=$3
EXPECTED=$4
pin() { sha256sum "$1" | cut -d' ' -f1; }
python tools/record_source_run.py "$SOURCE" --form 5 --source-sha256 "$(pin "$SOURCE")" --arguments "$OUT/$CASE.arguments.json" --arguments-sha256 "$(pin "$OUT/$CASE.arguments.json")" --reference "$OUT/record-reference" --reference-sha256 "$(pin "$OUT/record-reference")" --output "$OUT/run-$LABEL"
python tools/record_run_expectation.py "$OUT/run-$LABEL" --receipt-sha256 "$(pin "$OUT/run-$LABEL/receipt.json")" --expectations "$OUT/expectations.json" --expectation-sha256 "$(pin "$OUT/expectations.json")" --case "$CASE" --output "$OUT/$LABEL.expectation.json"
python -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"] == sys.argv[2], r' "$OUT/$LABEL.expectation.json" "$EXPECTED"
SH
for CASE in empty one5 sku6 sku7 cross10 global11 both12 stock-before-cap; do
  sh "$OUT/run-case.sh" "$OUT/PerSku.bagaev" "$CASE" "$CASE" matched
done
```

The digest checks above bind each call's inputs. Before using this helper on
other files, independently establish their intended identity and execution
scope. Computing a hash immediately before use is not approval of unknown code.

Construct and diagnose the intentionally wrong control:

```sh
python - <<'PY'
from pathlib import Path
source = Path('examples/probes/typed-journey/PerSku.fragment.bagaev').read_bytes()
needle = b'text.eq(record.field(earlier, "sku"), sku)'
assert source.count(needle) == 1
with Path('typed-journey-output/Wrong.fragment.bagaev').open('xb') as stream:
    stream.write(source.replace(needle, b'true'))
PY
python tools/record_function.py replace "$SOURCE" --form 5 --replacement "$OUT/Wrong.fragment.bagaev" --base "$BASE" --function-pin "$FUNCTION" --output "$OUT/wrong.draft.json"
WRONG_TARGET=81ffd32234f3606d29e52a597e61f0eac6638753bb249913c7e9ddfce89a2178
python tools/record_export.py "$SOURCE" --form 5 --draft "$OUT/wrong.draft.json" --base "$BASE" --target "$WRONG_TARGET" --preserve-layout --source-sha256 "$SOURCE_SHA" --replacement-source "$OUT/Wrong.fragment.bagaev" --output "$OUT/Wrong.bagaev"
python tools/record_source_check.py "$OUT/Wrong.bagaev" --form 5 --checker "$OUT/record-check" --checker-sha256 "$CHECK_SHA" --output "$OUT/wrong-check"
sh "$OUT/run-case.sh" "$OUT/Wrong.bagaev" cross10 wrong-control mismatched
```

Inspect `wrong-control.expectation.json`: its actual result must be successful
`Variant:BatchOutcome`, `BatchRejected`, reason `sku-batch-limit`, step1 and the
original stocks a20/b20. A runtime failure would also mismatch the oracle but
would not demonstrate the intended business-logic error.

Retain the original and corrected source revisions:

```sh
CHANGED_SHA=dbab1ba6b3fabcfc6031ad0b7f9e58a6950b8264b1d0e5e179251b5d14cdb65e
INITIAL_HEAD=df21665e403f175d55fedbc6520dbcba69ed9a8b0357859e37d20e42acee21c0
INITIAL_PACKAGE=741195949aed4d3c414a16041ae07c793a8947a4d2810c381fefe864fcadd3d7
python tools/record_revisions.py init "$SOURCE" --form 5 --source-sha256 "$SOURCE_SHA" --program-sha256 "$BASE" --output "$OUT/initial-history.json"
python tools/record_revisions.py append "$OUT/initial-history.json" --form 5 --package-sha256 "$INITIAL_PACKAGE" --head "$INITIAL_HEAD" --source "$OUT/PerSku.bagaev" --source-sha256 "$CHANGED_SHA" --program-sha256 "$TARGET" --output "$OUT/history.json"
```

Start a **new terminal process**, return to the same repository root, and use
only the retained files and these explicit pins. The final comparison is exact
source bytes; the history package alone is not a semantic check.

```sh
set -eu
OUT=typed-journey-output
HISTORY_SHA=eb97f852a771210ac97929c9d38fd66011e4761dbfc70f4417d2323f5181b160
HEAD=819f5de83a27cf7346ffdca714232c79f4e3635ac638021b5c8a7211c9ea4f39
CHANGED_SHA=dbab1ba6b3fabcfc6031ad0b7f9e58a6950b8264b1d0e5e179251b5d14cdb65e
printf '%s  %s\n' "$HISTORY_SHA" "$OUT/history.json" | sha256sum -c -
python tools/record_revisions.py checkout "$OUT/history.json" --form 5 --revision "$HEAD" --output "$OUT/continued.bagaev"
printf '%s  %s\n' "$CHANGED_SHA" "$OUT/continued.bagaev" | sha256sum -c -
cmp "$OUT/continued.bagaev" "$OUT/PerSku.bagaev"
for CASE in order-before-cap fourth-cap four-balanced missing-late; do
  sh "$OUT/run-case.sh" "$OUT/continued.bagaev" "$CASE" "$CASE" matched
done
```

To reverify a predecessor bundle without executing again, call
`record_run_expectation.py` with its retained receipt hash, the fixed expectation
hash above, its case ID, and a fresh report path. Repeat for each retained case,
including the intentional mismatch. Preserve the original receipt hashes across
the handoff; do not substitute arbitrary new bundles under an old success claim.
The recorded bounded acceptance did this for all nine predecessor bundles.
The copy-paste recipe explains that same public route but does not itself
reproduce the recorded acceptance's resource and preservation controls.
