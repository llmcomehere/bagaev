# bagaev

Private research workspace for a programming language and development
environment designed for LLMs to create and evolve programs. The language is
the central product; program memory, coordination, and tools support its
development and use. The goal is lower total cost and fewer errors across a
program's life cycle. This is an aim to test, not a demonstrated benefit.

The repository contains L0: a bounded typed pure dataflow language core, a
reference interpreter, atomic structural edits, and linked runnable examples
and usage. See [L0](docs/l0.md) for the contract and commands, and
[foundation](docs/foundation.md) for research limits. L0 makes no compiler,
model, or cost-advantage claim.

Start with the [context map](docs/context.md) to load the relevant source
sections. Read the complete [foundation](docs/foundation.md) for whole-concept
review of the 18 propositions and P0 research work. The project may support an
existing stack through a bounded adapter; it does not replace a user-selected
stack or promise model adoption.

The historical P0 workload remains frozen as a [protocol and behavior
contract](docs/p0.md) with an independent [case oracle](docs/p0-cases.json).
It is a preserved research baseline, not the current implementation priority.
There is no model or cost-comparison result yet.

## License

Original code and original documentation in this repository are licensed
under the [Apache License 2.0](LICENSE). Referenced or linked external works
remain subject to their own terms.

## Working here

Read [AGENTS.md](AGENTS.md), then [CONTRIBUTING.md](CONTRIBUTING.md). Run the
offline check with `python3 tools/validate_docs.py`.

Work is tracked in the private [project board](https://github.com/users/llmcomehere/projects/2)
and its linked issues and milestones.

The repository is private. Public release, Pages deployment, packages, and
spending remain gated by project readiness and trusted maintenance policy.
