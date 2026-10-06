# Experimental whole-cycle reference simulation

A finite demonstration derived from the [whole-language sketch](language-design.md).
It connects an actual typed pure programme to an **in-memory simulated** state
receiver, source admission and a resumed observer. It is not a new normative
language, durable database, security boundary or replacement for L2/Store/P0.
No native application kernel or model is invoked.

## What the complete path demonstrates

Two immutable [typed-record/10](probe-record-source.md) sources implement the
same reindex contract. `S1` calls a named `canonical_tags` helper; `S2` inlines
that computation. Both construct a nominal `Entry`, preserve its nominal
`EntryId` and manual tags, and replace indexed tags with ascending unique text.
They use the existing `list.unique`, record construction and field operations.
No catalogue callback or oracle-derived answer is installed in the evaluator.

The generic reference invocation accepts the nominal Entry and TextList
arguments. It is deliberately not the Json-only prepared calling convention.
Its detached `/10` result is checked before the simulated receiver commits.
TextList's existing64-item/4096-aggregate-byte limits remain. This is not a new
generic Set, Map or unbounded collection implementation.

The full `WC17` trace follows one connected path:

1. S1 computes a new entry; operation A commits simulated revision R8 and loses
   its response. A's exact intent and behaviour revision remain bound.
2. A continuation retains S1 and unresolved A. A proposed S2 candidate receives
   simulated admission; its actual pure source is checked against all four
   frozen complete pure outputs before becoming the new-run default.
3. A new run pins S2. Operation B invokes that actual source and commits R9.
4. The continuation resumes its explicit S1 data and observes A's old R8
   receipt, while the current entry remains B's R9 result. No second A write
   occurs and the old result is not relabeled as S2.

Only pure computation executes in the bagaev reference language. The Python
receiver implements a proposed finite protocol around it. Calling this a complete
production bagaev component/runtime or an implemented surface syntax would be
incorrect. Its value is checking the connection between computations, changes,
operations and continuation rather than another isolated helper.

## Proposed simulation rules

An operation key binds receiver/resource incarnation, domain and ID. Its intent
includes behavior revision, selected entry, canonical tags, expected state
revision, write epoch and original deadline. All event transitions are serialized
in one process; the fixtures supply logical clock ticks and controlled permission
inputs. Those inputs do not grant real rights.

For a known operation, exact intent is compared before fresh-write revision or
deadline checks. Current permission to reveal a result still applies. A new
execution checks write permission, deadline, epoch, revision and entry existence
at the simulated mutation boundary. A pure result must preserve ID/manual and
match the indexed-tag contract before state mutation. Other entries remain
unchanged. A receipt describes that particular operation, not arbitrary current
state.

Cancellation before commit creates an intent-bound cancelled record, including
when the original request has not arrived. A delayed request encounters it.
Late cancellation reports already applied rather than reverting data. A request
that only finds no row cannot claim a confirmed stop without establishing the
binding. These are new proposed simulation rules, not additions to frozen P0.

A receiver-side write epoch orders a cutoff with new writes. Old committed
receipts remain historical; admission of a new source alone is not a write fence.
A replacement resource incarnation does not inherit the old display name's
capabilities or operation history.

Observer knowledge is separate from receiver state. A dropped reply creates
uncertainty, not rollback. Revoked observation rights can prevent seeing a
receipt without making the old operation fail. Diagnostic audit expiry does
not remove terminal state within the promised horizon. After lawful retirement,
expired/unknown observation never becomes automatic permission for a fresh
operation. The simulator does not implement a real clock or retention service.

Continuation is a JSON round trip of logical program/operation references.
It is not a process-kill, crash recovery, filesystem synchronization or database
transaction test. No live handle, transaction or restored authority is serialized.

## Evidence and admission assumptions

The five named obligations in the fixture contract are fixed independently of
candidate rows. An intentionally omitted actual-consumer obligation leaves
simulated admission unresolved. The `complete-admissible-fixture` is an explicit
**controlled trusted premise** about these obligations, not production evidence
or a working general verifier. Actual pure source evaluation against the four
literal examples is additionally performed. It does not prove the other
obligations or universal refinement.

The existing [Store/1](store.md) accepts L2, not typed-record sources. This
simulation does not bypass its checker, change its schema or present its local
admission receipts as external application receipts. A real typed admission
bridge remains an implementation and trust-boundary decision.

## Inputs and reproduction boundaries

- [S1](../examples/probes/whole-cycle/pure/S1.json) and
  [S2](../examples/probes/whole-cycle/pure/S2.json): exact pure sources.
- [Pure expectations](../examples/probes/whole-cycle/pure/cases.json): four
  hand-authored complete result records per source, including existing logical
  work charges. These are not timing estimates.
- [Seventeen traces](../examples/probes/whole-cycle/cases.json): initial state,
  explicit events and selected expected projections, including WC17.
- [Input manifest](../examples/probes/whole-cycle/inputs.json): exact input hashes.
- [Serial simulator](../tests/probes/whole_cycle.py) and
  [negative controls](../tests/probes/whole_cycle_controls.py): source only.

The runners require three explicit arguments: `--reference` is an absolute
path to the separately reviewed/admitted `record_list_push_main.rs` reference
executable, `--reference-sha256` is its independently retained build identity,
and `--output` is a new absolute directory with an existing parent. They refuse
an identity mismatch or an already-existing output directory. A hash pins the
selected file; it does not authorize arbitrary code.

Review source and use an authorized bounded, no-network execution profile
before compiling or running. The runner does not establish that isolation. The selected executable and its
parent directories must remain owner-controlled during the run; the hash check
is not protection against concurrent hostile replacement.
It calls the selected reference serially with a20-second per-call timeout and
records inputs and complete stdout/stderr in the owned output directory. No
shell command is constructed from fixture contents, and no remote service,
model, credentials or native generated kernel is used. The source's existence
and CI do not grant execution permission.

## Finite observations

The initial pure qualification matched eight complete records: four inputs on
each source. The whole-cycle simulation then matched all17 pre-frozen trace
projections and made22 actual typed reference calls. The portable packet repeated
those17 projections through its explicit-argument runner. Repetition is not
additional independent semantic evidence.

Three controlled incorrect receiver variants produced normal, complete but
wrong projections: checking a fresh revision before terminal replay, confirming
cancellation without binding it, and disclosing a protected receipt after read
permission was removed. Each had a matching original positive setup and reached
its intended branch. A fourth control corrupted manual tags after a correct pure
return; the component-frame check refused before any state or ledger mutation.
That is guard detection, not a normal wrong-output comparison.

The16 original paper examples were not called passed until this finite simulation
was implemented; WC17 added the connected path before implementation. Expected
values/hashes remained unchanged. A pre-execution source review corrected new
terminal-result disclosure to use the same current observation check as replay.
No failed run is converted into a passing observation by editing expectations.

The compared observations are selected state/receipt projections, not a full
new wire protocol or all state-machine interleavings. Several permission,
scheduling, failure and migration combinations are outside this finite set.
No claim follows about real authentication, confidentiality, durability,
clock conversion, arbitrary effects, distributed progress, model benefit,
performance or total cost. Review is a separate same-maintainer pass, not
independent reproduction. Exact-head CI checks documentation, not this runtime.
