# Experimental typed application outcomes

Foundation B01/B03/B08 requires values, business refusals, environment failures and
state effects to remain distinguishable. Component-source/1 only returns a next
state. This separate /2 construction reuses existing typed-record/10 variants to
return **Propose:State** or **Decline:ErrorRecord**. A pure proposal is never an
Applied receipt, and an ordinary business decline is not a crashed evaluator.

## One readable source

[StockOutcome.bagaev](../examples/probes/component-outcomes/form/StockOutcome.bagaev)
expresses a nonnegative-quantity rule. Negative input returns a typed StockError;
otherwise the programme proposes a new Stock preserving its key/note. The generic
receiver does not know the quantity field or that application rule. Another
application can admit negative values under a different explicit contract.

The separate `component-form/2` adds named variant declarations, an outcome/error
clause, signed Int64/scalar Text/Bool literals, grouping, comparison and lazy
if/then/else. Constructors, field access, named calls and list.unique retain their
existing meaning. There is no eval, host-language escape, import, interpolation or
arbitrary dotted callback. The old /1 codec remains unchanged and rejects /2.

## Source and receiving policy

`bagaev-component-source/2` retains program/component fields and adds outcome_type
and error_type metadata. The entry is exactly `(State, Request) -> Outcome` with
exact Propose:State and Decline:ErrorRecord alternatives. Complete actual core
checking precedes component checks. The owned state/request/revision/error graph
is bounded, nominal, required-field and acyclic. Json views, optional omission,
record lists and nested variants are outside this first owned graph profile.

Independent `bagaev-component-policy/2` fixes the names, full reachable record
closure, outcome/error types, identity/revision bindings and allowed replacement
fields. A matching name does not establish compatibility. The /2 data reader has
its own module and executable; it does not autodetect or widen /1. Every checker
wire still says execution_admission:false. Source/core/policy identities identify
bytes and do not authenticate authors, observations or permission.

## Receiver behavior

OutcomeOwner is explicitly selected with /2 source/policy/checker. It reuses the
unchanged /1 owner's bounded packet, immutable intent, current conditions, ledger
and cancellation machinery. The entire returned nominal variant, including the
Decline payload, is checked by the actual typed reference.

- Propose: check every preserved field and all current final conditions, then
  replace detached state, increment revision and bind Applied. Equal-state proposal
  still advances revision under this profile.
- Decline: recheck the same current conditions, then bind Declined with typed error
  at the current revision. Application state/revision/mutation count do not change.
- Replay: exact old intent returns its historical result under current observation
  permission. A later B state is not A's result. Changed source/request/deadline
  conflicts; a late cancellation cannot rewrite a completed Declined result.
- Missing reply: the observer may know no outcome even though the receiver recorded
  one. No fresh effect follows merely from that uncertainty.
- Type/work/evaluator/service failures: distinct failures, with no successful empty
  value or business receipt. A stale computation cannot bind its old business
  decline against a new application revision.

This is a serial in-memory model with trusted host callbacks/conditions. It does
not establish authenticated rights, process-crash atomicity, real concurrency,
durable recovery, arbitrary application invariants or complete-language acceptance.

## Frozen observations and an explicit oracle correction

The source reader matches18 pre-implementation full wires. The outcome owner
matches17 pre-implementation finite scenarios, including old decline after B,
current-right/epoch changes, nested B commit, bad error payload and missing evaluator
response. A decoded readable source repeats those same17 scenarios, not17 new
independent cases. Twelve pre-code codec cases and10 additional boundary observations
cover exact lowering, refusal, escaping and limits. Two own-code mutations produced
normal wrong Declined outcomes and were detected; old-version gates invoked no host
checker. These are finite same-maintainer observations, not independent verification.

An earlier five-case pure prototype matched3/5 complete wires because its authored
logical-work expectation forgot the17 UTF-8 bytes in a Text literal. All five
semantic value/refusal observations matched. The original oracle is retained under
[pure/original-cases.json](../examples/probes/component-outcomes/pure/original-cases.json).
The [documented correction](../examples/probes/component-outcomes/pure/oracle-correction.md)
derives25 rather than8 from the pre-existing Text work rule. The unchanged source
and reference match the corrected five wires. This was an expectation error, not
an implementation fix or a change made to hide a failed run. Logical work is not a
speed, memory or model-cost measurement.

## Reproduction

Build `examples/probes/backend/rust/component_outcome_main.rs` only after reviewing
it and authorizing the existing bounded build profile. Use that retained /2 reader
and the unchanged typed-record/10 reference. The source and form runners take
`--reader`, `--reader-sha256`, `--output`; the owner runner additionally takes
`--reference`, `--reference-sha256`. Executable/output paths must be absolute and
output directories new with existing parents. Hashes identify reviewed files;
they are not execution permission or an isolation mechanism.

- `tests/probes/component_outcome_source_checks.py`:18 full data-check wires.
- `tests/probes/component_outcome_form_checks.py`:12 codec cases and actual exact
  /2 source/policy check, plus old /1 version refusal.
- `tests/probes/component_outcome_owner_checks.py`:the actual readable source
  through17 reused outcome-owner cases, including nominal validation and effects.

Use an approved bounded no-network execution environment. No workflow, toolchain,
credential or permission change is provided by this packet. Source/1, form/1,
Owner/1 and L2/Store/P0 remain unchanged. A /2 source-change admission/continuation
profile requires its own explicit contracts and qualification; it is not silently
covered by the existing /1 programme-manager demonstration.

See [typed outcome changes and pinned continuations](probe-outcome-composition.md) for the finite edit, qualification, admission and context path.
