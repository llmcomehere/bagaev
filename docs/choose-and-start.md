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
| Investigate typed native components or a proposed language mechanism | Pick one explicitly versioned probe from the [context map](context.md). Probe versions are not interchangeable or a single production runtime. |

For simple tag sorting alone, ordinary Python's `sorted(set(tags))` is shorter.
The reason to try the example is its explicit program identity and checked change,
not evidence that this task needs a new language. Decide from the whole job,
including setup, correction, review and future changes.

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
`/1` interfaces and has no Store or production-runtime acceptance.

- Change the actual task requirement before changing the program; retain an expected
  result independently of the proposed implementation.
- Stay within the selected [L0 semantics](l0.md), or deliberately choose the existing
  L2 workflow. Do not infer unsupported operations from this example.
- Record failed attempts and reasons for choosing another stack. A successful
  prescribed example does not show that an LLM would freely choose bagaev.
- Bring a concrete missing capability or unnecessarily difficult step to an Issue.
  Useful adoption evidence is a task completed with understandable tradeoffs, not
  the number of mechanisms, checks or pull requests.
