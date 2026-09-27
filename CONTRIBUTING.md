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

## Select checks and report results

Select affected product modules or named test methods explicitly within the
authorized execution profile. For example, [L2 tests](tests/test_l2.py),
[toolchain tests](tests/test_toolchain.py) and [Store tests](tests/test_store.py)
cover different contracts. The [integrated beta guide](docs/beta.md) gives one
selected [CLI/continuation test](tests/test_beta.py) and its expected observations;
it does not replace the other product checks.

Blind discovery of every test module is not an ordinary product-suite selection.
[L1-checker tests](tests/test_check_l1.py) require a separately reviewed guest
with the trusted checker and fixtures at the module's declared paths.
[Candidate-checker tests](tests/test_check_candidate.py) create temporary Git
repositories and may invoke host isolation. Review their actual effects and
prerequisites separately; their names do not make them static checks.

For a reproducible handoff, record the exact command and working directory
relative to the checkout, base/head or source snapshot, interpreter/tool versions,
selected test IDs and count, actual run count, exit code, failures, errors and
skips. Identify expected failures, unexpected successes and any unavailable
checks as well. Preserve primary output locally and provide a sanitized result
summary; do not publish private paths or logs. State resource/isolation limits
and remaining owned processes or unfinished effects.

Zero selected tests, omitted checks or hidden skips cannot establish the requested
coverage. Report unrun work as `NOT_RUN`; distinguish a selected product run from
the full suite. The documentation CI checks static structure and links, not
runtime behavior, integration acceptance or benchmark claims.

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
