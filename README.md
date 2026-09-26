# bagaev

bagaev is a private research repository for a programming language and development
environment in which people and LLMs can create and evolve programs through
checkable behavior and structural change. Lower cost and fewer errors are
research hypotheses, not demonstrated benefits.

## Current profile

L0 is the accepted bounded core: a pure deterministic dataflow language with
four types, ten operations, a reference interpreter, digest-bound atomic
patches, and synthetic examples. [L0](docs/l0.md) owns its normative semantics.

L1 is the bounded CPython backend profile for all L0. Local selected-case
evidence recorded 41 of 41 cases matching, with zero failures or skips, on
CPython 3.14.4. That evidence is not universal equivalence, native compilation,
or a model/cost result. [Issue #11](https://github.com/llmcomehere/bagaev/issues/11)
owns integration status. The [L1 proposal](docs/l1-proposal.md) owns the
backend and 41-case contract.

[P0](docs/p0.md) and its [oracle](docs/p0-cases.json) are frozen historical
research inputs. They are not the current language implementation plan.

The synthetic catalog [application contract](docs/application.md) selects four
behaviors with a frozen [99-case oracle](examples/beta/catalog-cases.json).
Its ordinary Python [comparison reference](src/catalog_reference.py) and
[tests](tests/test_catalog_reference.py) support M1. This reference is not an
implementation of the application in bagaev.

Read the [roadmap](docs/roadmap.md) for the bounded beta and its gates, then the
[context map](docs/context.md) for source routes. The complete
[foundation](docs/foundation.md) is required for a whole-concept review.

## Repository status

The repository is private. Its current visibility does not grant access,
publication, a static site, packages, or beta distribution. A future
research-preview opening has its own readiness gate and requires separate
visibility authorization.

## Contributing

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md). Standalone
contributors use the public fork-and-pull-request path when access is granted;
assigned local workers follow their operator's assignment. Issues own current
execution status. The roadmap owns planned scope and gates.

## License

Original code and original documentation are under the [Apache License 2.0](LICENSE).
Referenced works retain their own terms.
