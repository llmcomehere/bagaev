# Fixed obligation-set compatibility example

This follows [single-requirement compatibility](probe-evidence-compatibility.md)
using existing /8 JSON operations. It changes neither the language nor native
backend. A trusted caller supplies the complete required obligation set; a
producer may not choose its own easier denominator and claim independent success.
Descriptive receipt compatibility is not truth, provenance or execution authority.

## Frozen contract

Two JSON inputs: requirements (one or two distinct requirement objects) and
receipts (zero through four receipt objects). Both use the exact object grammar
of the single-requirement example. Empty/malformed/oversized requirements or two
equal six-dimensional obligations return invalid/requirements. Integer -0 equals
0 for duplicate detection and matching; floating tokens and booleans are invalid.
Validate all requirements first, then all receipts before matching. Malformed or
oversized receipts return invalid/receipts. Unknown keys invalidate the input;
duplicate decoded keys are a transport refusal. The ordinary Python function
operates on already decoded ordinary JSON values, not raw duplicate-key streams.

For each required obligation, match all six dimensions exactly. Runtime pass
requires selected>0. Exact refuted/withdrawn records conflict with that pass even
when their selected field is zero. A conflict on any obligation returns
pending/conflicting-evidence, including when a different obligation is missing.
Otherwise any missing pass returns pending/missing-obligation. Only an exact
applicable pass for every obligation with no conflict returns
accepted/all-obligations. The result has Text fields decision and reason.
Unrelated negatives do not veto; duplicate receipts do not enlarge the fixed
requirement set; order does not change the decision. No coverage percentage or
implicit bytes-to-runtime promotion is introduced.

The small bounds stay inside the existing work budget. They are deliberate
limits, not a general arbitrary-size policy or evidence-management engine.

## Portable fixtures and harness

- [Source](../examples/probes/evidence-obligations/program.json) and
  [ordinary function](../examples/probes/evidence-obligations/ordinary_reference.py)
  implement the same finite contract.
- [48 vectors](../examples/probes/evidence-obligations/cases.json) include 20
  initial semantic cases and 28 grammar/raw-token boundaries. Preserve
  arguments_raw exactly: parsing and serializing -0 would erase the token witness.
  Expected semantic records were specified before implementation; full wires and
  logical work are captured observations, not independently predicted costs.
- [Data helper](../tests/probes/evidence_obligations_wire.py) supports list,
  request CASE, and check CASE --mode reference|native --output FILE. It emits
  the raw invocation or compares the complete recorded wire, without launching code.
- The [reference harness](../tests/probes/backend/evidence_reference_harness.rs.in)
  accepts the invocation file after replacing {{BACKEND}}.
- The [native harness](../tests/probes/backend/obligations_native_harness.rs.in)
  accepts invocation, fill 90/165 and work after replacing {{BACKEND}} and linking
  only the separately admitted exact-source /8 kernel. It checks canonical source
  identity before dispatch, input immutability, one call, guards/unused tails and
  detached owned output. The wire binding retains the distributed-source digest;
  the artifact canonical-source digest is different. Neither is an authority token.

Compilation and execution require a separately admitted bounded environment.
No workflow or automatic execution path is added.

## Finite evidence

Earlier 48 ordinary/reference cases and 192 native observations (O0/O2 with two
fills) matched the contract. Seven source mutants reached normal wrong outcomes
on explicit witnesses. A conservative valid-domain logical-charge model matched
48 actual reference counts and bounded its finite profile by 38,297 charges,
below 65,536. This model is not a compiler proof or a wall-time/memory bound.

Source acceptance, native conformance and measurement remain separate. Exact-head
CI validates documentation, not native execution. Same-maintainer review is not
independent reproduction. No timing, model-cost or production claim follows.

A further portable replay rebuilt the integration-base backend and reproduced
the prior LLVM/binding: all 48 ordinary results, 48 complete reference wires and
48 O2/fill-165 native wires matched. Five comparator/refusal controls and the
documentation checks passed. This replays the same cases; it does not add new
independent semantic coverage or a performance measurement.
