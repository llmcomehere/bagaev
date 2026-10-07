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

## Prepare a program explicitly

When authoring a new pure program, provide a draft with exactly `schema`, `entry`
and `definitions`, using `schema: "bagaev-l2-draft/2"`. Omit `pins` entirely.
The explicit preparation operation validates every definition and dependency,
including unreachable definitions, then derives the `/2` pins. It does not run
expressions, repair invalid source or grant execution authority.

After source review under the same authorized local bounds:

```console
python3 -B -S -m src.bagaev_filter prepare examples/l2-filter/queue-draft.json --output prepared-queue.json
python3 -B -S -m src.bagaev_filter check prepared-queue.json
python3 -B -S -m src.bagaev_filter run prepared-queue.json --input examples/l2-filter/queue-input.json
```

The last result is `{"kind":"ok","order":["b"]}`. The prepared program is byte-equal
to the canonical checked `queue.json`. The library equivalent is
`bagaev_l2_filter.prepare_program(draft)`, returning an immutable checked snapshot.
It accepts a draft value or bounded JSON text and leaves the input unchanged.
Both the draft text and prepared program file must fit the ordinary 1 MiB limit.
The output filename must be new. A malformed draft creates no output.

Existing `check` and `run` still require a pinned program and reject incorrect or
missing pins. They never invoke preparation as a fallback. A supplied `pins`
field, unknown draft field or foreign schema is refused. This operation does not
convert `/1` sources or add a Store path. It handles deterministic authoring work;
it does not establish authenticity or model advantage.

## Locate a reference refusal

For an unbound variable, missing called definition or wrong call arity, the `/2`
checker now supplies a supplemental source location with `L2_REFERENCE`:

```json
{"definition":"main","expression":"/body/3"}
```

The expression path is rooted at the definition's body and uses JSON Pointer
escaping (`~0` for `~`, `~1` for `/`). `prepare` and `check` CLI observations expose
it in `error.location`; the library exposes `L2Error.location`. It identifies a
source expression, never a local filename or runtime permission.

Complete syntax checking still precedes reference errors, including unselected
and unreachable code. Error codes and first-error selection are unchanged.
This slice does not promise locations for every error: entry, syntax, cycle,
transport and other failures can still have null location. If an escaped pointer
would exceed 4096 UTF-8 bytes, location contains `expression:null` and
`truncated:true` rather than a misleading partial path. The checker retains
shared path components and constructs text only for the selected failure.

The portable `l2_filter_reference_location_checks.py` driver covers eleven
frozen refusal/location expectations through the API and 22 actual `prepare`/`check` CLI refusals, plus four
supplementary pointer-bound cases. It also checks literal data is not treated as
a variable reference and metadata does not alias the supplied draft. Existing
filter/draft checks retain their source, pin and artifact expectations. These
checks do not establish fewer model mistakes or complete diagnostic coverage.

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
it. The CLI exposes only `prepare`, `check`, `run`, `compile`, `patch`, help and version. There
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

The optional `l2_filter_draft_checks.py` driver checks four independently frozen
complete prepared programs through value/text/bytes input, nine invalid drafts,
three text refusals, unchanged checking strictness, 18 CLI calls (13 expected
refusals), the queue draft and unchanged existing queue artifact bytes. Two
additional bounded checks established refusal when derived pins push prepared
text beyond 1 MiB and successful preparation of syntax whose explicit later
execution refuses: preparation does not evaluate the program. These supplements
are distinct from the original four exact prepared-output fixtures.
