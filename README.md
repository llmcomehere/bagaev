# bagaev

**A small change should stay a small change.**

bagaev is a programming language and development environment being built for
LLMs to create and evolve programs. This is a **bounded functional beta
candidate** for local Linux/CPython CPU use: an executable language core,
explicit contracts, durable revisions and a checked continuation workflow.
This is an experimental platform, not a production platform.
Lower total cost and fewer errors remain hypotheses.

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

The [operational-semantics candidates](docs/operational-semantics.md) make this
thesis concrete: preserve semantic domains, evidence scope, operation identity,
ownership and obligations through real consumers and continuation. They include
synthetic counterexamples and ordinary alternatives. These are scoped research
candidates, not a claim that the full runtime or a new permission system exists.

The [whole-language design sketch](docs/language-design.md) connects these
mechanisms into a proposed computational, component and change model, with
paper scenarios and a map of all eighteen principles. It is a non-normative
architecture proposal, not new syntax or runtime acceptance.

The experiment must count the whole job: preparation, failed attempts, model
and tool work, review, repair, continuation, and maintenance. Saving tokens
while increasing those costs would not establish success. A negative or
indeterminate result is useful evidence for changing direction.

## Start with one real change

Unsure whether this task fits bagaev? Start with
[choose a route and finish one change](docs/choose-and-start.md): a short scope
guide and one complete runnable example, including the patched result.

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

For a readable stateful formula, follow [write, diagnose and change a component](docs/readable-authoring.md): an explicit form2–6 choice map, syntax context, JSON conversion and a detached checked helper extraction.

For a composed business rule with retained results, follow the [stock adjustment example](docs/stock-adjustment.md): readable match, actual typed execution, declines, applied revisions and receipt reconstruction.

The [typed tag collection](docs/tag-box.md) demonstrates readable TextList rules, retained outcomes and the boundary between a business decline and an uncommitted computation failure.

## What exists today

- **Typed stateful operations and continuation:** the [worked component guide](docs/stateful-components.md) connects readable Propose/Decline outcomes, source-pinned runs and bounded persisted receipts. Business refusal, unobserved result and applied state remain distinct; this is an experimental single-writer profile.

- **Source admission and old runs:** [programme composition](docs/probe-component-programmes.md) starts with only S1, admits a checked S2 after receiver-bound obligations and current checks, and reconstructs an old S1 observation without repinning its run. Qualification and live simulation remain separate.
- **Source-driven owned record:** a [generic serial receiver model](docs/probe-component-owner.md) uses the checked component bindings for both catalogue tags and a stock record. Pure computation is actual reference execution; state and authority remain in-memory simulation.
- **Explicit component context:** [inspection and continuation](docs/probe-component-context.md) bind current and pending programme sources, required unknowns and open effects. The first connected demonstration reconstructs explicit data at WC17; it does not restore authority or establish durable recovery.
- **Checked readable changes:** the [component edit receiver](docs/probe-component-edit.md)
  turns a proposed source change into a detached exact-base/target draft and
  add/replace function delta. Actual source/policy checking precedes the separate
  evidence/authority admission boundary; draft creation changes no live state.
- **Readable component programme:** a [bounded notation](docs/probe-component-form.md)
  expresses the actual working component's records, pure functions and state/frame
  declarations. It reconstructs the same checked source and enters the connected
  change/recovery example, without introducing a host evaluator or new rights.
- **Experimental evidence-bound changes:** the [connected change example](docs/probe-component-change.md)
  checks all five receiving obligations against exact retained observations,
  then rechecks base/authority before switching the simulated new-run default.
  Evidence reuse is distinguished from new execution and never grants real rights.
- **Experimental source-level components:** [typed declarations](docs/probe-component-source.md)
  name state/request types, identity/revision bindings and replacement fields.
  A data-only checker feeds the connected simulation's actual typed computation
  and preservation checks. Compatibility does not grant execution permission.
- **Experimental whole-cycle reference simulation:** a [connected example](docs/probe-whole-cycle.md)
  runs typed pure computation through simulated state mutation, source change
  and lost-response continuation. Seventeen finite trace projections matched;
  this is not a durable receiver, real access enforcement or a full runtime.
- **Experimental portable context:** the [bounded context receiver](docs/probe-context.md)
  checks pinned sources, obligations, choices and separate exchange frames.
  It preserves unknowns and never grants admission; kernel checking remains an
  explicit trusted host dependency. The 23 frozen cases passed within the
  documented single-baseline integration, not full context/model acceptance.
- **Experimental exact forms:** [JSON, S-expression and familiar-code codecs](docs/probe-forms.md)
  reconstruct unchanged L2 programs. The initial slice passed 126 frozen
  non-edit form observations. A pure edit receiver also passed 51 frozen
  trace/form observations; full form acceptance and model/cost studies remain open.
- **Experimental typed native kernel:** a separate bounded Int64/Bool core,
  Rust frontend, LLVM lowering and handwritten C11 comparison. The
  [October 4 observations](docs/native-probe-results.md) record 300 matching
  native ABI observations at O0/O2/Os. This is not full native L2/L3 support
  or a measured performance/cost advantage.
- **Experimental inferred scalar source:** [local and loop-accumulator types](docs/typed-scalar-source.md)
  are inferred while function boundaries remain explicit. The Rust adapter passed
  43 frozen source checks and composed with both backends on 25 frozen stages.
  [Pinned source-location lookup](docs/typed-source-locations.md) also passed its
  bounded mapping suite. This is a scalar experiment, not full L3 or admission.
- **Experimental typed Text:** a [separate source profile](docs/probe-typed-text.md)
  supports bounded UTF-8 literals/arguments, locals, branches, helpers and loops.
  Its [LLVM kernel and admission adapter](docs/probe-text-native.md) passed bounded
  complete-output checks; the canonical-binding correction was followed by 136
  native matches across 34 cases, O0/O2 and two output prefills. This is not full
  native L2/L3, arbitrary-pointer safety, independent reproduction or a performance
  advantage. The [Text CLI example](docs/typed-text-llvm-artifact.md#small-cli-example)
  evaluates an invocation or emits pinned LLVM data without compiling it.
- **Experimental Cranelift comparison:** a [locked AOT object backend](docs/probe-cranelift.md)
  passed 150 fixed native ABI observations using the same kernel oracle.
  [Initial bounded runtime and source-byte observations](docs/probe-measurements.md)
  do not select a general backend winner; compiler-latency, memory and model/cost
  conclusions remain unestablished.
- **L0:** a pure deterministic dataflow core, four types, ten operations,
  reference interpreter, atomic structural patches, and synthetic examples.
- **L1:** a bounded CPython backend for L0. Recorded local acceptance matched
  all 41 selected cases, with no failures or skips, on CPython 3.14.4.
  [The backend contract](docs/l1-proposal.md) defines that scope.
- **Application baseline:** a [synthetic catalog contract](docs/application.md),
  a frozen [99-case oracle](examples/beta/catalog-cases.json), and an ordinary
  [Python comparison reference](src/catalog_reference.py).
- **L2:** a [structured pure language contract](docs/l2.md),
  [reference library](src/bagaev_l2.py), and a catalog program with three
  structural changes. The [L2 source and API guide](docs/context.md#l2-library-entry)
  links the programs, oracle, and tests. See [Issue #15](https://github.com/llmcomehere/bagaev/issues/15)
  for reference execution and acceptance status.
- **L2 toolchain:** a cohesive [CLI and CPython backend](docs/toolchain.md)
  for checking, running, patching, compiling, inspecting and comparing L2 programs.
  The guide includes a clean-checkout walkthrough and explicit artifact verification.
  Earlier M3 acceptance matched 575 primary records and three selected backend
  methods; its CLI observations were in-process. The integrated run below also
  exercised all authored toolchain methods and actual CLI subprocesses.
  [Issue #16](https://github.com/llmcomehere/bagaev/issues/16) retains M3 history.
- **Local revisions:** an explicit [store and continuation contract](docs/store.md)
  and `store` CLI commands for immutable candidates, checked admission, portable
  export and verified restore. Earlier M4 acceptance matched 96 primary records, with 19 CLI
  observations nested in one record. It used 17 fresh child processes and rejected
  seven wrong-observation controls. Selected cases cover process-interruption
  recovery, stale-base/CAS refusal, receipt replay, and receiver import/restore.
  The integrated run below exercised all 16 authored Store methods. This is
  process-interruption evidence, not power-loss or physical-disk durability
  evidence. See [Issue #17](https://github.com/llmcomehere/bagaev/issues/17).

- **Model proposal interface:** a pure [packet/response and named-change library](docs/model.md)
  with matched Python/L2 edits, explicit continuation views and bounded accounting.
  A bounded M5 run passed 19 selected product methods and all 8/8 main units, including
  four fresh successors; it recorded 16 main and 2 separate calibration native responses.
  Full USD lifecycle cost was not observed, so the cost result is indeterminate. See the
  measured [model results](docs/model.md#measured-m5-results) and its
  [sanitized data summary](examples/model/results.json). This is not a beta release,
  universal equivalence, or proof of savings; it does not imply full-suite coverage.

Selected-case parity is not universal equivalence or a model/cost result.
The integrated M6 run passed all 88 selected product methods with zero failures,
errors or skips on Linux x86_64, CPython 3.14.4 and SQLite 3.46.1. It includes
actual CLI subprocesses, persisted A1 continuation into a fresh process, A3
completion and exact backup restore. The [beta guide](docs/beta.md) records the
tested source, bounded oracle checks, local contribution rehearsal and limits;
25 specialized checker methods remain **NOT_RUN**, so this is not the full suite.
Current independent candidate acceptance and integration status is tracked in
[Issue #18](https://github.com/llmcomehere/bagaev/issues/18).
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

The experimental [source-once JSON interface](docs/probe-prepared-json.md)
separates program preparation from per-call argument admission. Its owned data
handles do not confer native execution authority; portable reproduction surfaces
and narrower input-budget equivalence are documented separately.

The explicit [/9 immutable TextList append probe](docs/probe-list-push.md) adds
source-level accumulation without changing /1–8. Its native output has a separate
version; finite conformance and source-size observations are not performance claims.

The explicit [/10 named record-list append probe](docs/probe-record-list-push.md)
extends immutable accumulation to nominal record lists without increasing their
capacity. It preserves earlier source/native profiles.

The [experimental prepared /10 JSON API](docs/probe-prepared-json10.md) reuses checked /10 source with distinct ownership types, preserving the older /8 interface. Finite conformance is separate from production acceptance.

The [finite evidence compatibility example](docs/probe-evidence-compatibility.md) compares descriptive receipt metadata with frozen requirements using existing /8 JSON operations. It grants no execution authority.

The [fixed obligation-set example](docs/probe-evidence-obligations.md) checks every member of a trusted finite requirement set and gives conflicts priority over missing evidence.

The [lease metadata example](docs/probe-lease-compatibility.md) checks clock labels, half-open containment and bounded renewal descriptions without reading a clock or granting authority.

The [nominal-domain parity control](docs/probe-nominal-domains.md) demonstrates existing record distinctions alongside ordinary Rust newtypes, including the deliberate explicit-conversion escape.

The [direct ordinary Rust catalogue](docs/probe-ordinary-catalog.md) implements the same frozen workload without the language interpreter, providing a qualified comparison path before any new measurements.

The [equal application-boundary observations](docs/probe-equal-application-boundary.md) compare complete owned output across ordinary Rust and prepared reference/native paths. The ordinary baseline is faster in the three resolvable cases; no universal advantage is claimed.
