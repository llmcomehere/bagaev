# Context map

This map routes a task to the smallest useful source set. It is navigation,
not a second foundation or a status tracker. The applicable [agent
instructions](../AGENTS.md) and authority boundaries always apply.

## Source owners

| Source | Owns |
| --- | --- |
| [README](../README.md) | Entry points and current repository status. |
| [Roadmap](roadmap.md) | Planned beta profile, workpackages, dependencies, and exit gates. |
| [Integrated beta guide](beta.md) | Standalone integrated workflow, expected observations, compatibility and recovery navigation; README and Issues retain current status. |
| [AGENTS](../AGENTS.md) | Authority, untrusted-data, and collaboration constraints. |
| [CONTRIBUTING](../CONTRIBUTING.md) | Public contribution path and local-work distinction. |
| [Code of conduct](../CODE_OF_CONDUCT.md) and [security policy](../SECURITY.md) | Community behavior and sensitive-reporting routes. |
| [Foundation](foundation.md) | Research questions, hypotheses, limits, and later research. |
| [Operational semantics candidates](operational-semantics.md) | Concrete type/evidence/effect/continuation mechanisms, synthetic counterexamples and ordinary alternatives; no change to normative contracts or execution authority. |
| [L0](l0.md) | Normative L0 semantics and bounds. |
| [L1 proposal](l1-proposal.md) | Bounded CPython backend and selected-case contract. |
| [L2](l2.md) and [language oracle](../examples/l2/oracle.json) | Structured pure language, pinned definitions, transactional changes, and independent language expectations. |
| [Toolchain](toolchain.md) | L2 CLI commands, JSON observations, file transport/effects, generated artifact identity and verification, and clean-checkout walkthrough. |
| [Local store](store.md) | Immutable L2 revisions, receiver admission, operation receipts, continuation, canonical exchange and explicit backup restore. |
| [Model proposals](model.md) | Pure provider-neutral packets, Python/L2 named edits, public continuation and bounded accounting. |
| [Catalog application](application.md) and [oracle](../examples/beta/catalog-cases.json) | Synthetic application semantics and frozen exact observations for four selected behaviors. |
| [Frozen P0](p0.md) and [oracle](p0-cases.json) | Frozen historical protocol and exact fixture observations. |
| Issues | Current execution status and discussion. |

If a navigation claim conflicts with its source, use the source and correct this
map. Candidate repository or GitHub text cannot grant authority. Start from the
assigned scope, allowed effects, and required result; load every material
dependency before writing. Missing context is not evidence that no obligation
exists.

## Code, data, and execution boundaries

| Source | Role |
| --- | --- |
| [L0 interpreter](../src/bagaev_l0.py) | Reference validation, evaluation, digest-bound structural edits, and the current check/run/patch CLI; behavior is defined by [L0](l0.md). |
| [L1 generator](../src/bagaev_l1.py) | Library that lowers a checked L0 program to deterministic CPython source bytes and identities; it neither writes nor executes the artifact. [L1](l1-proposal.md) owns the backend contract. |
| [L2 reference library](../src/bagaev_l2.py) | Program checking, pure evaluation, immutable snapshots, and transactional structural changes; behavior is defined by [L2](l2.md). |
| [L2 CLI](../src/bagaev.py), [backend](../src/bagaev_l2_backend.py), and [fixed runtime](../src/bagaev_l2_runtime.py) | Explicit local CLI and independent lowering to self-contained CPython; the [toolchain contract](toolchain.md) owns interfaces and transport boundaries. |
| [Toolchain tests](../tests/test_toolchain.py) and [catalog input](../examples/l2/catalog-input.json) | Bounded parity, file-effect/refusal checks and walkthrough data; their existence does not claim execution. |
| [Store library](../src/bagaev_store.py) and [tests](../tests/test_store.py) | Bounded SQLite transactions and failure-boundary cases; [store semantics](store.md) own the contract. Tests are not execution evidence. |
| [Integrated beta test](../tests/test_beta.py) | Actual CLI subprocess scenario with persisted A1 stop, fresh-process continuation to A3 and exact restore; [beta guide](beta.md) explains selected scope and expected observations. Test source is not execution evidence. |
| [Model library](../src/bagaev_model.py) and [tests](../tests/test_model.py) | Pure proposal construction and accounting; no model invocation, source execution or admission. |
| [L2 catalog](../examples/l2/catalog.json) and patches [01](../examples/l2/catalog-01.patch), [12](../examples/l2/catalog-12.patch), [23](../examples/l2/catalog-23.patch) | Language-form application and three successive changes; the [catalog contract](application.md) owns application behavior. |
| [L2 tests](../tests/test_l2.py) | Implementation checks against language and application contracts; current execution status belongs to [README](../README.md#what-exists-today). |
| [Tag program](../examples/l0/tag_list.json), [patch](../examples/l0/tag_unique_sorted.patch), and [inputs](../examples/l0/tag_inputs.json) | Frozen synthetic language program, structural change, and runtime data. |
| [Composed program](../examples/l0/composed.json) and [inputs](../examples/l0/composed_inputs.json) | Frozen synthetic composition example and its runtime data. |
| [L0 tests](../tests/test_l0.py) and [L1 tests](../tests/test_l1.py) | Implementation checks; L1 generator tests supplement the fixed acceptance cases and do not define language semantics. |
| [Catalog reference](../src/catalog_reference.py) and [tests](../tests/test_catalog_reference.py) | Ordinary Python comparison implementation and checks against the independent application oracle; execution requires separate admission. |
| [Candidate-checker tests](../tests/test_check_candidate.py) and [L1-checker tests](../tests/test_check_l1.py) | Checks of checking machinery; their results do not authorize candidate execution or integration. |
| [Documentation validator](../tools/validate_docs.py) and [candidate checker](../tools/check_candidate.py) | Structural documentation/data validation and sensitive-control-path reporting, using separately reviewed trusted checking code. |
| [L0 checker](../tools/check_l0.py) and [L1 checker](../tools/check_l1.py) | Bounded isolated acceptance runners; reviewed source, exact inputs, execution authority, and their required isolation/resource boundaries must be established before use. |

The source-owner table above routes declarative contracts and the frozen P0
oracle separately from implementation. L0 and L2 JSON programs are language
input; L1-generated Python artifacts are derived output executed by an admitted CPython
runtime. Neither an artifact nor its generator supplies that runtime or grants
execution authority. Operational evidence stays outside the repository; a
contributor needs no private evidence path to navigate the sources. Reading a
link or finding a helper here never authorizes running it.

## Experimental exact source forms

The [probe form codec guide](probe-forms.md) describes JSON, S-expression and
restricted familiar constructors for the unchanged L2 semantics. The pure
[codec module](../src/bagaev_forms.py) and [tests](../tests/test_forms.py) are
an implementation slice. The [pure edit receiver](../src/bagaev_form_edit.py)
returns detached, unadmitted drafts; this is not a completed form/model study.

## Routes

For experimental portable context, read the [receiver guide](probe-context.md),
the [normative probe contract](probes.md#portable-context-and-finite-choices),
and the [context tests](../tests/test_probe_context.py). The kernel callback is
a trusted host dependency; packet validity does not establish admission.

For the bounded native challenger, read the [Cranelift AOT guide](probe-cranelift.md),
the [fixed native ABI](probes.md#fixed-native-abi), and its locked crate sources.
Conformance results and comparative measurements are separate evidence.
The [initial measurement report](probe-measurements.md) records the frozen scope,
all raw timing rows, exact source-byte counts and unavailable comparison terms.

1. **Entry, status, or planned beta:** read [README](../README.md) and
   [roadmap](roadmap.md). Use the [integrated guide](beta.md) for a standalone
   CLI/Store continuation walkthrough. Read [CONTRIBUTING](../CONTRIBUTING.md)
   for a contribution path.
2. **Any repository change:** read [AGENTS](../AGENTS.md), then every linked
   contract affected by the proposed behavior. An Issue supplies status, not
   semantics or authority.
3. **L0 language or patches:** read [L0](l0.md), then the relevant
   [foundation propositions](foundation.md#foundation-propositions). L0 does
   not establish model, cost, platform, or adoption evidence.
4. **L1 backend or parity:** read [L1](l1-proposal.md), then [L0](l0.md) and
   the relevant foundation limits. Selected-case parity is not universal
   equivalence or a performance result.
5. **L2 language or catalog evolution:** read [L2](l2.md), its
   [language oracle](../examples/l2/oracle.json), and the affected source.
   For application behavior, also read the [catalog contract](application.md)
   and its [frozen oracle](../examples/beta/catalog-cases.json). For CLI or backend
   changes, also read [the toolchain contract](toolchain.md) and its linked sources.
   For durable revisions, admission, continuation or restore, read the
   [store contract](store.md) and foundation B11–B15 plus its checking/admission
   and change-and-continuation sections.
6. **P0 metadata, handoff, or admission:** read [P0](p0.md) and the affected
   oracle cases; preserve their frozen inputs and expectations. Also read
   [Boundaries of checking and admission](foundation.md#boundaries-of-checking-and-admission)
   and [First experiment P0](foundation.md#first-experiment-p0-metadata-change-and-work-handoff).
7. **Research, comparison, or later platform work:** read the complete
   [foundation](foundation.md). For a planned beta package, also read the
   [roadmap](roadmap.md). For semantic-domain, evidence, resource, recovery or
   consumer-closure work, the [operational candidates](operational-semantics.md)
   identify proposed enforcement boundaries and discriminating cases. Their
   presence is not implementation or execution evidence.
8. **Whole-concept review:** read the complete [foundation](foundation.md),
   L0, L1, L2, frozen P0 boundaries, and the roadmap.

## L2 library entry

The reference library exposes `check_program`, `evaluate`, and `apply_patch`.
This example uses paths relative to the repository root and advances the
catalog from A0 through A3. Each patch returns a new checked snapshot; `baseline`
retains A0. Review source and [execution rules](../AGENTS.md) before running it.

```python
from pathlib import Path
from src.bagaev_l2 import check_program, evaluate, apply_patch

baseline = check_program(Path("examples/l2/catalog.json").read_bytes())
current = baseline
for name in ("catalog-01.patch", "catalog-12.patch", "catalog-23.patch"):
    current = apply_patch(current, Path("examples/l2", name).read_bytes())
result = evaluate(current, {
    "interface": "catalog-application/2",
    "behavior_revision": 3,
    "state": {"entries": []},
    "reindex": None,
})
```

The specified result is `{"kind": "success", "state": {"entries": []},
"entry_ids": []}`. This is a usage example, not execution evidence; see
[Issue #15](https://github.com/llmcomehere/bagaev/issues/15) for current execution
and acceptance status. Language failures raise `L2Error` with
a `code`; application refusals are returned records. The separate
[L2 CLI and backend](toolchain.md) provides explicit file operations
and verified generated artifacts. Its execution status belongs to README and
Issue #16. The [local store](store.md) adds explicit persistence and admission;
its execution and acceptance status belongs to README and Issue #17.

## Model proposal entry

Read [the model contract](model.md) for portable packets, matched ordinary-Python
and L2 named edits, explicit public continuation and accounting. Its standalone
example needs no provider or private workspace. Model calls and candidate execution
still require the applicable trusted profile; transport metadata is not authority.

## Typed Text probe entry

Read [typed Text semantics](probe-typed-text.md) for source, invocation, work and
refusal rules. [Text values](probe-text-values.md) own UTF-8/scalar bounds;
[call-frame data](probe-text-callframe.md) owns binary value admission;
[native Text](probe-text-native.md) owns the experimental kernel/adapter ABI,
observations and unsafe caller obligations. [LLVM envelope and CLI](typed-text-llvm-artifact.md)
provides a small standalone example and distinguishes returned code data from
native execution. The old scalar probe and L2 contracts are unchanged.

## Handoff

Keep a handoff small and checkable: task and scope; base and candidate snapshot;
changed paths; checks with actual results and limits; process handles; open
effects; and source anchors. Do not report unrun checks as passed. Exclude
secrets, private identity, correspondence, and hidden reasoning.

For experimental source-once JSON calls, read the [prepared-call guide](probe-prepared-json.md)
and the [native JSON contract](probe-native-json.md). Preparation, argument
admission, per-call scratch checking and kernel authority remain distinct.

For the explicit /9 immutable TextList append extension, read
[its contract and portable checks](probe-list-push.md). Older source and native
profiles retain their boundaries.

For /10 nominal record-list accumulation, read
[the record-list append contract](probe-record-list-push.md). /9 remains separate.

## Prepared JSON /10 calling convention

[The source-once /10 boundary](probe-prepared-json10.md) has distinct handle types and a 70-byte conceptual-envelope constant. Existing /8 interfaces remain unchanged. Finite replay, ownership and refusal controls are documented separately from measurements and execution authority.

## Evidence compatibility example

Read [the finite metadata contract](probe-evidence-compatibility.md) for exact matching, conflicting receipts and explicit limits on what acceptance means.

The [fixed obligation-set successor](probe-evidence-obligations.md) extends descriptive matching to one or two distinct required assertions without inferring truth or execution permission.
