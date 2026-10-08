# bagaev

**A small change should stay a small change.**

bagaev is an experimental programming language and development environment for
LLMs to create and evolve programs. It makes values, behavior, source identity
and proposed changes explicit. Production readiness and lower full development
cost are not established.

## Start with one real change

**Read the [compact language reference](docs/choose-and-start.md).** It is the
single primary use guide: syntax, types, every current typed intrinsic,
evaluation/refusals, bounds, identities, editing commands, and explicit L2/L0/
component compatibility. Its enforced budget is 32 KiB of UTF-8; this README is
limited to 4 KiB. These are byte budgets, not measured model-token counts.

For new readable pure programs, select record-form/5 and profile11 explicitly.
The guide includes a complete example. The [inventory batch change](docs/inventory-batch-change.md)
shows a reproducible pinned edit that retains authored comments/named calls and
all source bytes outside the changed expression. It changes returned data, not
real inventory. Load a host/native/persistence contract only when that task needs it.

The small original example remains `python3 -B examples/l0/first_change.py`.
Review source and the [execution boundaries](AGENTS.md) before running code.
No document, source pin, passing parser or candidate supplies execution authority.

## Why a language for change?

The aim is fewer mistakes and less repeated work across creation, review,
revision and continuation. A new feature must justify its semantics and added
context burden. The language is the product; tooling and memory support it.
An ordinary implementation remains a serious baseline. Respect a prescribed stack.

## What exists today

- Readable typed pure code: records, variants, bounded lists, Json views, helpers,
  loops, pinned drafts and source-preserving edits. Rust reference and selected
  LLVM/native paths have bounded conformance evidence.
- Existing L2: dynamic pure JSON programs, CPython toolchain and explicitly selected
  local revision/continuation workflows. [Integrated beta evidence](docs/beta.md).
- Experimental typed components: Propose/Decline, versioned state contracts and
  selected receiver/recovery paths. [Stateful guide](docs/stateful-components.md).
- L0/L1 and older profiles remain compatible under their own contracts. The
  [compact guide](docs/choose-and-start.md) prevents mixing their different rules.

Source acceptance, selected execution checks and independent acceptance differ.
Current maintainer review is not independent reproduction; the complete language/
platform is not fully qualified. No production web/mobile/GPU/distributed support
is promised. No new model adoption or general speed/memory/cost advantage is
established. In the recorded [equal-boundary comparison](docs/probe-equal-application-boundary.md),
the ordinary Rust baseline was faster in the three resolvable cases.

## Help test the thesis

Bring a concrete task, counterexample or simplification through
[Issues](https://github.com/llmcomehere/bagaev/issues) and [CONTRIBUTING](CONTRIBUTING.md).
The [context map](docs/context.md) locates detailed contracts/evidence;
[roadmap](docs/roadmap.md) owns planned gates. The [foundation](docs/foundation.md)
is research background, not mandatory language-use reading. Historical evidence
stays in its original reports and Git history rather than this entry page.

Original code and documentation: [Apache License 2.0](LICENSE). Referenced works
retain their own terms. Follow [conduct](CODE_OF_CONDUCT.md) and use the
[security route](SECURITY.md) for sensitive reports.
