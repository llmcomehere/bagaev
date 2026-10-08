# Should this task use bagaev?

Respect the user's requested stack. bagaev currently offers a bounded experimental
language and local change/continuation workflow, not a general replacement for an
established application stack. Its cost and error-rate advantages are unproven.

## Choose a route from the task

| Your task | Current route |
| --- | --- |
| Deliver a production web service, mobile app, GPU workload or unrestricted system integration | Use a suitable established stack. Those are not accepted bagaev profiles. |
| Explore a small pure computation and exact-base structural change | Start with the L0 example below. No provider account or package installation is needed. |
| Explore reusable definitions, a catalog application and a saved development handoff | Use the existing [integrated beta guide](beta.md), [application contract](application.md) and [CLI walkthrough](toolchain.md). This remains the documented local Linux/CPython experimental profile. |
| Select records in a bounded pure computation | Use the separate [pure filtering profile](pure-filter.md), explicit L2/2 source and `src.bagaev_filter` CLI. For saved revisions, explicitly choose the separate [filter workflow](filter-saved-workflow.md); the old /1 receiver does not accept /2. |
| Write a readable typed pure function over records, tags or a small record list | Use [record-form/1](pure-record-form.md), [single-entry reindexing](pure-reindex-entry.md) or [batch reindexing](pure-batch-reindex.md). Prepare explicit arguments with the data-only tool; a separately reviewed typed reference executes the invocation. |
| Model a typed stateful operation with business refusal, exact operation replay and persisted continuation | Follow the [stateful component example](stateful-components.md). This is the separate experimental typed component/2 profile, not pure L2/2 or a production runtime. |
| Investigate typed native components or a proposed language mechanism | Pick one explicitly versioned probe from the [context map](context.md). Probe versions are not interchangeable or a single production runtime. |

For simple tag sorting alone, ordinary Python's `sorted(set(tags))` is shorter.
The reason to try the example is its explicit program identity and checked change,
not evidence that this task needs a new language. Decide from the whole job,
including setup, correction, review and future changes.

For current pure form4/form5 tooling, inspect the [machine-readable capability
report](record-capabilities.md) before selecting schemas and bounds. Use explicit
--revision 2 for the current Json preparation and native-data routes; the default
revision 1 remains unchanged. The separate
[sixteen-entry catalogue](catalog-wide.md) has [diagnostic/formatting support](wide-authoring.md),
[focused changes](wide-function-editing.md) and a [draft-to-source handoff](record-draft-export.md).

A [pure inventory reservation](pure-inventory-reservation.md) example shows typed
business refusals, full returned stock and guarded arithmetic on sixteen items.
It performs no real inventory or database effect. The separate [Json envelope](inventory-json.md)
can follow the existing native profile. Its [one-function policy change](inventory-json-focused-change.md)
connects context, pinned draft, export, lossless Json preparation and separately
admitted native execution. Native qualification remains selected and bounded.
A separate [ordered batch](inventory-batch.md) composes four reservations with
original-stock return on failure and ordered receipt snapshots. This is a pure
returned value, not an external transaction. To inspect a form5 failure location,
join the [checked node report](native-source-locations.md) with the
[pinned readable source map](record-source-map.md); coarse ranges are labelled.


## Start with readable typed source

For a typed pure task, choose the smallest relevant example. The single-entry
example preserves human-maintained tags while replacing computed ones; the batch
example preserves record order for a list of at most four entries.

1. Copy the readable example and write the expected result for your own inputs.
2. Use [syntax diagnostics](record-diagnostics.md) for spelling and parser context.
   `valid_form` does not check types.
3. Put the arguments in a JSON array and run `record_text.py prepare` as described
   in [the pure-form guide](pure-record-form.md). This produces invocation data,
   not an executed result.
4. Evaluate with the separately reviewed typed-record/10 reference under your
   authorized execution profile, using `run --input invocation.json`.
5. Compare the complete result, and handle explicit type, bound and work refusals.

No component identity, owner or revision is needed for a pure value. For durable
state, choose the stateful route explicitly. Do not treat a four-entry example
as an unrestricted catalogue, or a successful fixed test as model adoption.

## Finish one change

From a standalone checkout, read the [execution boundaries](../AGENTS.md) and
review the selected source before using your authorized local execution profile.
The sample reads only the three existing public fixtures, computes in memory and
prints one observation. It writes no program or Store files and contacts no service.
`-B` prevents Python bytecode-cache writes; it is not an isolation mechanism.

```console
python3 -B examples/l0/first_change.py
```

Expected stdout is one JSON line:

```json
{"after":["blue","red"],"before":["red","blue","red"],"old_base_retry":"patch.stale"}
```

Read [the example source](../examples/l0/first_change.py): it evaluates the original
tag program, applies the existing exact-base patch, evaluates the returned program,
and demonstrates refusal to apply that old-base patch again. Original inputs stay
unchanged. Unexpected errors fail the sample; a failing command is not a passed check.

The raw [L0 CLI](l0.md#library-and-cli) remains available for individual operations.
Its `patch` command prints an observation envelope containing a `program` field.
That whole envelope is not a program file: use the returned `program` object when
continuing through the library API, as the sample does.

The two selected tests are:

```console
python3 -B tests/test_first_change.py -v
```

They check this finite example and fixture preservation, not a full language suite.
No network, credentials, external model or native compiler is needed. This does not
add a new platform-compatibility guarantee beyond the repository's tested profile.

## Decide what to try next

For a different small application, try [changing a support-queue ordering
rule](example-queue-change.md): existing L2, a one-definition patch, fixed expected
results and an ordinary Python comparator. It needs no new language mechanism.

To select only open records as well, the separate [pure filtering
profile](pure-filter.md) has an explicit `/2` source and CLI. It preserves the old
`/1` interfaces. A separately selected [saved workflow](filter-saved-workflow.md) now provides bounded local continuation; production-runtime acceptance remains open.

- Change the actual task requirement before changing the program; retain an expected
  result independently of the proposed implementation.
- Stay within the selected [L0 semantics](l0.md), or deliberately choose the existing
  L2 workflow. Do not infer unsupported operations from this example.
- Record failed attempts and reasons for choosing another stack. A successful
  prescribed example does not show that an LLM would freely choose bagaev.
- Bring a concrete missing capability or unnecessarily difficult step to an Issue.
  Useful adoption evidence is a task completed with understandable tradeoffs, not
  the number of mechanisms, checks or pull requests.

For a connected typed pure edit, follow [one complete readable change](pure-change-workflow.md): inspect source identity, extract a helper, prepare a detached draft and verify explicit input.

For an observable single-function business change with a complete pinned handoff,
see the [inventory limit change](inventory-focused-change.md).
