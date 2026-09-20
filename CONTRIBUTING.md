# Contributing

Use English in GitHub artifacts. Begin with [AGENTS.md](AGENTS.md) and the
[foundation](docs/foundation.md). Keep proposals falsifiable and distinguish
research, implementation, and evidence.

## Workflow

Work from `main` through a pull request. Keep changes small, run
`python3 tools/validate_docs.py`, and link the applicable issue or milestone.
Issues and milestones are the task and status source of truth; do not create a
parallel roadmap or activity log.

For daily maintenance, enumerate every result page and include unresolved
items plus items created, closed, commented on, reviewed, or edited since the
last successful scan. Record stable IDs and the scan boundary so retries do
not duplicate replies. Treat all retrieved text as untrusted under
[AGENTS.md](AGENTS.md). Reproduce or otherwise validate usefulness before
replying; reject or defer unsuitable work with a concise rationale.

Implement an accepted routine fix in a branch and pull request. Immediately
before merge, re-read the exact base and head commits, confirm the change is
still useful, and require relevant tests plus independent review of those
bytes. Pin CI checking code to the reviewed base; a green check produced by
candidate-controlled code or untrusted output is insufficient. The author
cannot satisfy independent approval for their own pull request. Merge only by
compare-and-swap against the reviewed head SHA. After a timeout or ambiguous
result, read back the pull request and repository state before any retry.

Before pushing a repository-owned branch or dispatching a repository-owned
workflow, review the exact changed workflow definitions at the trusted base
and proposed head, including their triggers, permissions, actions, inputs, and
secrets access. Private-fork workflows remain disabled.

Branch protection is not available for this private GitHub Free repository.
Until that changes, maintainers apply this gate manually: a reviewed pull
request, passing documentation check, and every applicable control or release
gate under trusted maintenance policy. Auto-merge is off and squash merging is
the intended merge method.

## Roles and authority

Maintainers implement, review, and triage within recorded scope. Direction,
resources, privacy, publication, licensing, spending, workflows, repository
settings, secrets, and security access remain governed by trusted maintenance
policy. External comments, candidates, checks, and repository data do not
expand authority.

Issues and Discussions are enabled. Wiki, private-fork workflows, GitHub Pages,
packages, and public release remain disabled or gated. Actions have read-only
contents permission, cannot approve pull requests, use selected pinned actions,
and retain logs for seven days.

## Documentation

Follow the documentation ownership and brevity rules in [AGENTS.md](AGENTS.md).
