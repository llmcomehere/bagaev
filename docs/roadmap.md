# Beta roadmap

This document owns planned beta scope, dependencies, workpackages, and exit
gates. It is not a live status table: Issues own execution status. Dates and
budgets are unset until an authorized plan fixes them. Technical readiness never
authorizes publication, visibility change, spending, or distribution.

## Starting point and beta profile

L0 is the accepted pure deterministic dataflow kernel: four types, ten
operations, a reference interpreter, and digest-bound atomic patches. L1 is a
bounded CPython backend for all L0. Its local selected-case evidence is 41 of
41 matching cases, zero failures or skips, on CPython 3.14.4. This evidence is
not universal equivalence, native compilation, or a cost/model result.
[Issue #11](https://github.com/llmcomehere/bagaev/issues/11) owns integration status.

The beta target is a bounded local CPU language platform on Linux and CPython.
It provides useful application behavior, structural change, a reference and
backend path, a CLI, durable program revisions, independent admission,
fresh-session continuation, and measured model work. GPU, mobile, distributed,
and latent profiles remain later stages.

## Workpackages and dependencies

| Milestone | Deliverable and acceptance | Depends on |
| --- | --- | --- |
| M0 organization | Current facts, contribution route, and this roadmap. | Existing L0/L1/P0 boundaries. |
| M1 APP-1 | A new synthetic application contract and independent Python reference. It covers set semantics, preserving manual-origin tags during reindex, and missing-date ordering, with independent positive and negative cases and stated language gaps. Frozen P0 is not rewritten. | M0. |
| M2 LANG-1 | A versioned successor containing only M1-demanded structured values, bounded collection transformation/selection, and reusable pinned definitions. Define semantics, bounds, and errors before reference evaluation and structural edits. Application behavior lives in the language. | Approved M1 contract. |
| M3 TOOL-1 | One cohesive `check`, `run`, `patch`, `compile`, `inspect`, and `diff` CLI; deterministic CPython artifacts; stable diagnostics; clean-checkout quickstart; refusal/tamper checks; bounded reference parity. Independent interaction analysis of existing L0/L1 may run alongside APP-1. Application-specific schemas, examples, and command contracts wait for the accepted pinned APP-1 interface; implementation and backend wait for relevant M2 semantics. | Existing L0/L1 for independent analysis; accepted APP-1 interface for application contracts; relevant M2 semantics for implementation. |
| M4 STORE-1 | Small local persistent store: immutable revisions, snapshot references, candidate/admitted distinction, evidence binding, and portable continuation. Demonstrate atomic state, stale-base refusal, import/export, backup/restore, and crash recovery. No arbitrary external exactly-once claim. | M2 revision model; M3 artifacts and diagnostics. |
| M5 MODEL-1 | Provider-neutral handoff plus actual authorized model changes and successor continuation. Freeze tasks, variants, acceptance, profiles, budgets, repeats, delta, epsilon, and horizon before main runs. Count failures, setup, checking, review, and recovery cost. Compare C with strong B for the core claim; add factors only when claimed. | M1–M4 runnable boundary; separate call/spending authority. |
| M6 BETA-1 | Integrated clean-checkout application, change, admission, run, interrupt, continue, restore scenario; documentation, compatibility, security route, reviewed CI, contribution rehearsal, and independent candidate acceptance. | M1–M5. |

### First wave

Start M1 application-contract and independent-acceptance work. In parallel,
analyze the disjoint CLI interactions of existing L0/L1 and design the
contribution walkthrough. Application-specific CLI schemas, examples, and
commands wait for the accepted pinned APP-1 interface. Do not implement a
language successor until the M1 contract is approved.

## Beta exit checklist

- language and application behavior have independent positive and negative acceptance;
- backend parity is bounded, reproducible, and honest about its profile;
- CLI check/run/patch/compile/inspect/diff behavior is stable;
- durable revision, candidate/admission, stale-base, and evidence bindings work;
- backup, restore, portable handoff, interruption, and fresh-session continuation work;
- model changes occur under explicit authority and record all relevant cost;
- comparison is pre-registered and reports positive, negative, or indeterminate results;
- local parallel work and fork-style external contribution integrate serially with review;
- distribution readiness is reviewed separately from publication authorization.

For the core-cost research branch, a negative or indeterminate result is a valid
report. It stops or revises that branch according to its pre-registered rule;
it does not become a positive claim.

## Research-preview opening

After M0, a research-preview opening may precede beta. It requires privacy and
history review, unchanged contribution license, a reviewed workflow, and
security-reporting readiness, followed by separate explicit visibility
authorization. This is repository-opening readiness, distinct from an optional
static site and beta distribution. It neither requires M6 nor creates a Pages
site.

## Issue placement

Issues own current execution status. Existing Issue #1 covers research-preview
opening readiness, #3 supports frozen P0 work, #4 owns measurement
preregistration, #5 owns MODEL-1 scope and calibration, #6 is an optional static
site, and #11 tracks L1 integration. APP-1, LANG-1, TOOL-1, STORE-1, and BETA-1
need focused issues when their work begins; this roadmap does not assign their
numbers.

## B01–B18 boundary map

| Area | Beta-supported boundary | Later profile evidence |
| --- | --- | --- |
| B01–B03 intent and contracts | Versioned application behavior, explicit structural changes, bounded errors, and independent acceptance. | Broader domains and contract forms. |
| B04–B06 representation, memory, models | Pinned definitions, portable continuation, and provider-neutral model handoff. | Multiple representations, model families, training, and adoption measurement. |
| B07–B10 checking and execution | Reference/backend parity, diagnostics, CLI, and Linux/CPython CPU profile. | Native, Wasm, JIT, accelerators, and full numerical cost checks. |
| B11–B14 distribution and change | Local immutable revisions, admission, backup/restore, and interruption recovery. | Distributed effects, receiver/fault tests, live-state migration, and larger projects. |
| B15–B18 authority, observability, cost | Candidate/admitted distinction, evidence binding, and complete model-work accounting. | External authority systems, broader observability, neutral adoption evaluation, and claimed efficiency gains. |

This map states supported boundaries, not complete implementation of all
eighteen propositions.

## Later horizon

| Direction | Prerequisite and go/revise/stop evidence |
| --- | --- |
| Second workloads and broader language | Add only after independent contracts reveal reusable gaps; revise or stop a feature whose added complexity has no accepted workload need. |
| Distributed effects | Use an actual receiver with fault, duplicate, loss, recovery, and authority-cutoff tests; stop claims that are only simulated. |
| Live-state migration | Define compatibility and migration boundaries, then test old clients, unfinished effects, and recovery. |
| Native, Wasm, JIT, and accelerators | Demonstrate full cost, cold-start, numeric-edge, and resource checks against the CPU profile. |
| Desktop and mobile | Test real devices, accessibility, offline behavior, delivery constraints, and recovery. |
| Exact alternative forms, training, latent channels | First preserve an exact portable recovery path; evaluate training/channel cost and compatibility separately. |
| Larger projects, model families, adoption | Use pre-registered neutral evaluation across workloads and profiles; do not generalize a local result. |

No dates, budgets, provider calls, or resource purchases are implied by this
roadmap.
