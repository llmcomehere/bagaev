# Finite retention and creation dependencies

This data-only experimental slice of [operational semantics](operational-semantics.md)
uses the existing typed-record/10 profile. It plans no actual deletion, changes
no receiver ledger and returns execution_admission=false for every decision.
Existing store and retention promises remain unchanged.

## Same finite inventory

Input is an explicitly complete inventory of at most four nodes and four directed
consumer-to-witness edges. Nominal NodeId records contain unique integers1..4.
Node kind is terminal, diagnostic, consumer or artifact; phase is live, planned or
retired, with a requested retire Boolean. All endpoints exist and edges are unique.
Completeness is a supplied premise, not discovered by a graph algorithm.

This first profile never retires terminal facts and refuses already retired
terminals as invalid inventory. Planned nodes cannot also request retirement.
Terminal retirement, tombstones, expiry horizons and external consumers remain
outside its scope. Dispensable diagnostics can be planned for retirement while
completion facts remain available; an absent fact never becomes proof of execution.

After full graph validation, a live non-retiring consumer needs every witness to
remain live and non-retiring. A planned witness is not enough for a live consumer.
A planned consumer may depend on live or planned non-retiring witnesses. Planned
dependencies must be acyclic: with four nodes, cycles have witnesses of length1..4.
Lawful acyclic prerequisite creation is allowed; first creation needs no replacement.

Decision priority is unavailable/incomplete-inventory, invalid/graph,
refused/terminal-retirement, refused/live-dependency,
refused/creation-dependency, refused/phase-cycle, then supported/finite-plan.
Validation of a late malformed edge is not hidden by an earlier convenient result.

## Ordinary baseline and typed probe

The [ordinary baseline](../tests/probes/retention_plan_baseline.py) uses conventional
DFS. The [typed source](../examples/probes/retention-plan/program.json) uses existing
nominal records, bounded record lists and explicit bounded path expansion. No new
interpreter operation is introduced. Both receive the same finite inventory and
the same [25 literal expectations](../examples/probes/retention-plan/cases.json).
Ordinary code supplies the same outcomes on these cases; this observation alone
does not justify an additional language mechanism or establish a cost advantage.

The [portable driver](../tests/probes/retention_plan_checks.py) accepts --reference,
--reference-sha256 and a fresh absolute --output directory. The reference must be
the separately reviewed typed-record/10 executable. A matching hash identifies
bytes, not execution permission; use an independently approved bounded profile.
Inputs and raw outputs remain in the selected output directory, not the repository.

Six [explicit source controls](../examples/probes/retention-plan/controls.json)
skip terminal/live/creation obligations or complete edge checking, miss a four-node
cycle, or incorrectly ban lawful acyclic creation. Each is paired with its valid
baseline witness and must return a normal wrong Decision value. Setup refusal,
skip or an unrelated earlier error does not count as a successful negative.

Initial preparation found a lexical loop-accumulator collision. Distinct names
corrected the source without changing the expectations or interpreter. The literal
cases and six controls were then exercised with the actual reference; these remain
finite same-maintainer observations, not independent reproduction, arbitrary graph
conformance, production deletion safety, scheduling or timing/model-cost evidence.
