# Contributing

Use English in GitHub artifacts. Start with [AGENTS.md](AGENTS.md), the
[context map](docs/context.md), and the relevant semantic contract. Keep claims
falsifiable and distinguish a proposal, an implementation, and evidence.

## Access and license

The repository is private and currently admits only already-authorized readers.
This document describes a future-public contribution path; it neither grants
access nor enables a fork, workflow, or release. A future research-preview
opening requires its own readiness gate and explicit visibility authorization.

By submitting a contribution for inclusion, you confirm that you have the
rights needed to provide it under Apache License 2.0. Contributions are
submitted under that license. Respect the separate terms and attribution
requirements of third-party material.

## External pull requests

Use a fork or personal branch where access permits. Submit one focused pull
request with:

- a relevant issue or roadmap workpackage reference;
- the intended base and actual head;
- a concise behavior and scope description; and
- checks actually run, their result, and material limits.

Do not include secrets, private correspondence, personal information, or
untrusted instructions. The candidate cannot define the policy that reviews or
executes it. A trusted independent review precedes execution of untrusted
changes. Maintainers re-read the exact base and head before integration, apply
relevant checks, and merge only against the reviewed head.
After a timeout or ambiguous merge result, read back the pull request and
repository state before retrying; lack of a response does not mean no change
occurred.

## Maintainer integration

Before pushing a repository-owned branch or dispatching a repository-owned
workflow, inspect the exact changed workflow definitions at the trusted base
and proposed head, including triggers, permissions, actions, inputs, and
secrets access. Private-fork workflows remain disabled. Candidate-controlled
checking code and untrusted output cannot supply independent acceptance.

Until repository controls change, integration requires a reviewed pull request,
relevant passing checks, and every applicable control or release gate. Do not
enable auto-merge as a substitute for these checks.

## Assigned local work

An assigned local worker follows its operator's assignment and public
repository rules; it does not need a private work directory to contribute from
a standalone checkout. Local assignments identify the task revision, owner,
base, file and semantic scope, and owned outputs. The default is separate
coordinator-created checkouts and branches. Worktrees do not isolate processes,
ports, caches, credentials, or shared Git metadata.

Small explicitly disjoint tasks may share a checkout. Do not overlap scopes,
double-assign work, or replace a timed-out writer automatically. One
coordinator serially integrates local and external candidates after a stable
handoff, independent review, exact base/head readback, and relevant combined
invariant checks.

## Documentation

Keep documentation concise and use its owner: README for entry and current
repository status, [roadmap](docs/roadmap.md) for planned scope and gates,
semantic specifications for behavior, and Issues for current execution status.
When a heading or contract changes, update [the context map](docs/context.md).
Offline documentation validation is not run unless an authorized execution
profile explicitly permits it.
