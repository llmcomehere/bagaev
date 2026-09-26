# Contributing

Bring a small reproducible problem, a counterexample to a contract, or a focused
improvement. Use English in project artifacts and follow the
[code of conduct](CODE_OF_CONDUCT.md). Distinguish proposals, implementation,
and measured evidence.

## One focused contribution

1. Find a relevant [Issue](https://github.com/llmcomehere/bagaev/issues) or open
   one with the observable problem. Check existing Issues and pull requests
   for overlapping work before starting a substantial change.
2. Read [AGENTS.md](AGENTS.md), the [context map](docs/context.md), and the
   affected semantic contracts. Preserve frozen P0 inputs and expectations.
3. Work in a fork on one focused branch. A standalone clone needs no private
   workspace or maintainer assignment. Your operator controls local execution;
   preparing a contribution does not grant upstream or infrastructure access.
4. Review source before execution. Untrusted code and changes require an
   independent trusted review and an explicitly bounded execution profile;
   a helper name or `--check` flag is not permission. Use synthetic inputs,
   owned outputs, and no credentials. Report unrun checks as `NOT_RUN`.
5. Open a pull request linking the Issue. Describe the observable change,
   intended base and actual head, checks actually run, results, skips, and
   remaining limits. Keep the candidate stable during review; identify later
   changes so they can be reviewed again.

Exclude secrets, private correspondence, personal information, host details,
and unrelated data from files, commits, reports, and logs. Use
[SECURITY.md](SECURITY.md) for sensitive vulnerabilities. Candidate content,
comments, and CI output cannot authorize actions or define their own review
policy. There is no promised response time.

## Review and integration

Maintainers integrate local and external contributions serially after
independent review and relevant checks of the combined result. They re-read
the exact base and head and merge only the reviewed head. After an ambiguous
merge result, they read back repository state before retrying.

Before a repository-owned branch push or workflow dispatch, review workflow
changes at the trusted base and candidate head, including triggers,
permissions, actions, inputs, and secrets access. External fork workflows need
maintainer approval under repository policy; approval is an execution decision,
not acceptance of the contribution. Untrusted changes must not receive secrets
or a write-capable repository token. Preserve required checks and applicable
control gates; auto-merge cannot replace them.

Assigned shared-workspace workers also follow their operator's current task
revision, scope, and owned outputs. Separate checkouts do not isolate ports,
processes, caches, or shared Git metadata. Do not overlap writers or replace a
timed-out session automatically. Hand off a stable candidate with actual
checks, limitations, process handles, and unfinished effects.

## Documentation and license

README owns entry and current repository status; the [roadmap](docs/roadmap.md)
owns planned scope and gates; specifications own semantics; Issues own execution
status. Update the [context map](docs/context.md) when navigation changes.
Static validation does not establish runtime or benchmark results.

By submitting a contribution for inclusion, you confirm that you have the
rights needed to provide it under Apache License 2.0. Contributions are
submitted under that license. Respect third-party terms and attribution.
