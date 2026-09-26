# bagaev

**A small change should stay a small change.**

bagaev is a programming language and development environment being built for
LLMs to create and evolve programs. This is a **research preview**: a small
executable language core, explicit contracts, and a testable direction—not a
beta or a production platform. Lower total cost and fewer errors remain
hypotheses.

## Why a language for change?

A program change can be tiny while the work around it grows: rediscovering what
behavior matters, copying definitions, repairing unrelated text, repeating
checks, and explaining unfinished work to the next session. The problem is
avoidable rework and change that cannot be checked.

The thesis is to make behavior and change explicit in the language. Describe
what a program must do, make a small structural change against a known
revision, and check the resulting behavior independently. A model's confidence
is a proposal, not an acceptance test. Examples must test the contract too,
including cases that should fail.

The language is the product. Its surrounding environment should make it
practical: reusable definitions pinned to exact revisions, evidence tied to
what was checked, and durable state that lets another session continue without
reconstructing a private conversation. These are design goals; the current
core implements only the bounded slice described below. A memory store or a
useful adapter alone would not demonstrate the language thesis.

The choice of representation is also open. JSON gives the first core an
inspectable form; it is not a claim that JSON is ideal for models. Existing
languages remain serious baselines and interoperability partners. A prescribed
stack should be respected, and unsupported profiles should be stated plainly.

The experiment must count the whole job: preparation, failed attempts, model
and tool work, review, repair, continuation, and maintenance. Saving tokens
while increasing those costs would not establish success. A negative or
indeterminate result is useful evidence for changing direction.

## Start with one real change

The [tag program](examples/l0/tag_list.json) returns its input unchanged.
The [structural patch](examples/l0/tag_unique_sorted.patch) adds `list.unique`
and replaces the result node with `list.sort`, preserving that node's identity:

```text
Input:          ["red", "blue", "red"]
Original result: ["red", "blue", "red"]
Patched result:  ["blue", "red"]
```

These are the example's specified results. The patch names the exact base
digest; a stale base or invalid graph is rejected atomically.
Read the [L0 semantics and CLI examples](docs/l0.md#library-and-cli) to inspect
and try it. Review source and the [execution rules](AGENTS.md) before running
untrusted code. No model account is needed for this example.

## What exists today

- **L0:** a pure deterministic dataflow core, four types, ten operations,
  reference interpreter, atomic structural patches, and synthetic examples.
- **L1:** a bounded CPython backend for L0. Recorded local acceptance matched
  all 41 selected cases, with no failures or skips, on CPython 3.14.4.
  [The backend contract](docs/l1-proposal.md) defines that scope.
- **Application baseline:** a [synthetic catalog contract](docs/application.md),
  a frozen [99-case oracle](examples/beta/catalog-cases.json), and an ordinary
  [Python comparison reference](src/catalog_reference.py). This application is
  not yet implemented in bagaev.

Selected-case parity is not universal equivalence or a model/cost result.
The [roadmap](docs/roadmap.md) covers language expansion, a cohesive CLI,
durable revisions, continuation, and measured model work. Frozen [P0](docs/p0.md)
is historical research input, not the current language plan.

If you need production support, a stable general-purpose language, native/GPU
or mobile deployment, or proven savings today, bagaev is not for you yet.
If you enjoy small language experiments and falsifiable claims, there is
something concrete here to inspect and challenge.

## Help test the thesis

**Bring one small counterexample or one focused improvement.** Find or open a
relevant [Issue](https://github.com/llmcomehere/bagaev/issues), then follow
[CONTRIBUTING](CONTRIBUTING.md). Maintainers use Issues for current work and
pull requests for reviewed changes. Please follow the
[code of conduct](CODE_OF_CONDUCT.md); sensitive reports go through
[SECURITY](SECURITY.md).

Use the [context map](docs/context.md) for source navigation and the complete
[foundation](docs/foundation.md) for the eighteen propositions, prior work,
measurement design, and limits.

Original code and original documentation are under the
[Apache License 2.0](LICENSE). Referenced works retain their own terms.
