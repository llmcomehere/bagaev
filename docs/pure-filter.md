# Explicit pure filtering profile

The current [queue example](example-queue-change.md) orders records. A common
next request is to select only open records. This separate experimental pure
profile adds a stable record filter and a complete open-queue example. It is not
a new Store, a native backend, a production queue or evidence of model benefit.

## Choose the profile explicitly

| Interface | Existing profile, unchanged | Separate filtering profile |
| --- | --- | --- |
| Source | `bagaev-l2/1` | `bagaev-l2/2` |
| Definition identity | `bagaev-l2-definition/1` | `bagaev-l2-definition/2` |
| Patch | `bagaev-l2-patch/1` | `bagaev-l2-patch/2` |
| CPython artifact | `bagaev-l2-cpython/1` | `bagaev-l2-cpython/2` |
| CLI module | `src.bagaev` | `src.bagaev_filter` |
| CLI observation | `bagaev-toolchain/1` | `bagaev-filter-toolchain/1` |

The old reference, generator, runtime and CLI source bytes are preserved. The
separate reference and generator intentionally retain the frozen algorithms with
distinct identities; this adds maintenance cost rather than silently changing old
artifacts. Existing `/1` remains the default entry and rejects `filter`. Neither CLI
silently converts the other source schema. Old Store admission is not a `/2` path.
Source/check/artifact identity does not grant execution permission or authenticity.

## Stable selection

The new expression is `["filter", array_expression, binder, predicate]`.

- Evaluate the array once; require an array of at most 256 items.
- Bind each item in input order, using a fresh lexical binder. Evaluate the
  predicate exactly once for that item. It must return Boolean, without coercion.
- Keep the original item exactly when the predicate is true. Preserve order and
  duplicates. Return a detached value under the existing export bounds.
- Empty input evaluates no predicate at runtime. Invalid syntax or an unbound
  predicate still fails static checking, even for an empty input.
- The first reached error aborts the run without a partial result. No mutation or
  external effects occur. Unselected borrowed values are not deep-visited merely
  to filter them; selected output still undergoes ordinary export validation.

Other expression semantics and the 100,000 semantic-step budget follow
[L2](l2.md), under the distinct `/2` identities above. Filter charges its entered
expression and each entered predicate expression using those existing rules;
these charges are not CPU measurements. The existing source depth and value
bounds remain. CLI input transport retains its additional byte/nesting limits;
it is narrower than the borrowed-value library API.

## Run an open queue

The application retains the existing queue ordering with missing priorities last
within each urgency group. It adds optional exact-Boolean `closed`, default false.
It validates **all** jobs before removing closed jobs: an invalid priority or
duplicate ID is not hidden by marking that job closed. No jobs are executed.

After reviewing source and selecting an authorized bounded local execution
profile, run from the checkout root:

```console
python3 -B -S -m src.bagaev_filter check examples/l2-filter/queue.json
python3 -B -S -m src.bagaev_filter run examples/l2-filter/queue.json --input examples/l2-filter/queue-input.json
python3 -B -S -m src.bagaev_filter compile examples/l2-filter/queue.json --output open-queue-artifact.json
python3 -B -S -m src.bagaev_filter run examples/l2-filter/queue.json --input examples/l2-filter/queue-input.json --artifact open-queue-artifact.json
```

Both runs return `result.value` equal to `{"kind":"ok","order":["b"]}`.
The urgent job `a` is closed; only the open job `b` remains. Use a new owned
artifact filename. Captured artifact bytes must exactly equal fresh trusted
lowering before the CLI executes generated Python; changing a hash field is
insufficient. This is not permission to execute arbitrary candidate code.

The same source can be obtained by applying the explicit `/2` consumer change:

```console
python3 -B -S -m src.bagaev_filter patch examples/l2-filter/queue-base.json examples/l2-filter/queue-change.patch --output open-queue.json
```

That output must be new. Stale or foreign-profile patches refuse without creating
it. The CLI exposes only `check`, `run`, `compile`, `patch`, help and version. There
is no Store command, implicit cache, network call or migration. `-B` suppresses
bytecode writes but is not isolation. Expected errors emit one JSON observation
and exit 2; successful commands exit 0. Unexpected host failures exit 1 with
path-free stderr. Error-code parity is required; optional locations are supplemental.

## Bounded evidence and reproduction

Portable drivers in `tests/probes/` require an explicit new absolute `--output`
directory whose parent exists. They execute code and write captures; they require
the same separately reviewed execution profile as other project tests. Keep their
raw captures private because CLI arguments can contain local paths.

- `l2_filter_checks.py`: 12 pre-implementation runtime expectations, five static
  refusals, three profile refusals, two artifact refusals and unchanged `/1` hashes.
- `l2_filter_controls.py`: nine own-code normal-wrong-output controls across the
  reference and compiler: wrong retained value/order, deduplication, truthiness
  or skipped final predicate. Mutant code is deliberate test input, not a runtime.
- `l2_filter_boundary_checks.py`: eight later borrowed-value/work-bound checks,
  including unselected deep data, selected invalid output and nested-work bounds.
  These are supplemental checks, not part of the initial pre-code oracle.
- `l2_filter_cli_checks.py`: 18 actual CLI calls, including 11 intentional refusals,
  no-overwrite, symlink, duplicate-key, foreign-profile and unsupported-Store checks.
- `l2_filter_consumer_checks.py`: 31 queue cases, including 23 inherited and eight
  new cases, against ordinary Python, reference and verified CPython, plus two CLI runs.

The unchanged `/1` L2 test suite's 17 selected methods also passed. A separate
compatibility run applied the same 99 catalog expectations to four explicitly
repinned `/2` snapshots through reference and CPython: 396 case/revision comparisons,
792 evaluations. Repeated cases are not additional semantic cases.

These are finite same-maintainer observations, not independent reproduction or
proof against arbitrary bugs. Ordinary Python can filter this queue directly.
No model-selection uplift, performance, token or whole-job cost advantage is
established. The benefit to investigate is keeping a needed transformation inside
a checked language application; the extra version and maintenance burden remain.
