# Operational semantics candidates

Research refinement, October 6, 2026. This document makes selected
[foundation B01–B18](foundation.md#foundation-propositions) obligations concrete
as candidate language, compiler and runtime mechanisms. It is not a new
instruction policy, a changed execution profile, a normative successor to L0/L2,
or a replacement for the frozen application/P0 contracts. Names below are API
and type sketches, not newly implemented syntax. Issues own implementation status.

The language remains the product. A new registry, graph or scheduler is not the
default answer to a counterexample. First determine whether existing nominal
records, ordinary types, a parser, a transaction or an existing receiver can
express and enforce the property. The stronger ordinary-language implementation
gets the same contracts, information and domain operations in a comparison.

## 1. Semantic domains survive representation changes

**Failure mechanism:** values with the same physical representation are treated
as interchangeable despite different subjects, phases, units or meanings.

**Candidate property:** implicit substitution across declared domains is rejected
before evaluation. For example, `Digest<IssuerRequest>` and `Digest<UserRequest>`
are not made equal merely because both use SHA-256; `Unchanged`, `Set(value)` and
`Clear` are distinct patch commands. Source, built artifact, installed bytes and
running process identity are separate stages with explicit relations.

**Mechanism and enforcement:** nominal wrapper types and closed variants;
explicit checked codecs at dynamic JSON, storage and FFI boundaries; field-specific
normalization. Existing [nominal record profiles](probe-record-source.md) already
distinguish declared names with identical field shapes. Reuse that capability
before proposing another type feature. A compiler can reject an implicit wrong
wrapper; a codec must reject an invalid external representation at runtime.

**Counterexamples and limits:** an intentional field projection and reconstruction
can erase or relabel meaning unless a separately enforced opaque constructor
boundary exists. A type name does not authenticate origin or grant rights.
Test both mistaken substitution and a lawful explicit conversion. Ordinary
newtypes/variants are a strong baseline. Extra adapters, annotations and migration
cost must be counted. Related principles: B02–B04, B07, B17.

## 2. Evidence applicability is separate from evidence truth and permission

**Failure mechanism:** a receipt for bytes, a different revision or a neighboring
consumer is widened into acceptance of the required behavior.

**Candidate property:** an admission decision discharges each required obligation
with an admissible method and exact scope, or exposes the missing/conflicting
ground. There is no implicit ordering in which byte access becomes semantic
review, compilation becomes execution, or a successful test becomes authority.

**Mechanism and algorithm:** model evidence with claim, subject/revision,
method, consumer binding, scope, producer, assumptions and outcome. For a fixed
obligation set, validate the whole candidate evidence set, resolve exact pins,
check permitted reuse prerequisites, and return accepted, refuted or unresolved
per obligation under the selected profile. The denominator comes from the pinned
contract, not only the rows supplied by a candidate. One unrelated green result
does not fill another mandatory gap. Contradictory applicable evidence needs
resolution rather than selecting whichever result is favorable.

**Trust boundary:** matching these fields is only compatibility checking. An
untrusted JSON producer must not mint trusted evidence by filling them correctly.
Producer authentication, trustworthy observation, current authority and the
checking tool's integrity are separate receiver obligations. A review receipt
can record its claimed reading method and delivered ranges; it cannot prove a
model understood them. Equal content can justify sharing a content check while
different callers, principals or deployment configurations retain separate
applicability checks.

**Costs and baseline:** typed records, immutable manifests and existing CI or
verification tools may suffice. Avoid another manually maintained copy of status.
Test wrong subject, stale revision, wrong method, partial scope, missing obligation,
zero selected tests, late malformed evidence and valid reuse. Related principles:
B01, B05, B07, B14–B16, B18.

## 3. Operation outcome is not a snapshot of current state

**Failure mechanism:** a state reached by operation B is credited to operation A
after A's response was lost; a timeout becomes a cancellation or permission to retry.

**Candidate property:** observation, attempt, committed outcome, requested stop,
confirmed stop and compensation have distinguishable semantics. A correct state
or matching timestamp is not a receipt for a particular operation.

**Mechanism:** a stable operation ID bound to immutable intent and a pinned
behavior revision; explicit not-started, in-flight, outcome-unknown, applied,
reconciliation-required and terminal transitions. Preserve the information needed
for recovery before crossing the relevant persistent effect. Reconcile the same
ID and request before repeating an effect. A known terminal replay is not
automatically subject to every fresh-execution prerequisite already changed by
its own successful action; the exact receiver contract determines ordering.

**Enforcement:** a cooperating receiver may atomically bind request identity,
current authorization, state mutation and outcome receipt. Without such a
receiver, keep the specified uncertainty or weaker guarantee. Compensation checks
its current target and cannot undo unrelated later changes. Cancellation requires
its own transition and ordering relative to commit; an observer timeout supplies
neither. This does not change the [historical P0](p0.md) order or add cancellation
to its frozen state machine.

**Costs and baseline:** journals, durable workflows, outboxes and provider-specific
idempotency protocols already address parts of this problem. Count retention,
lookup, migration and recovery cost. Test lost reply after real commit, A rollback
followed by B success, late old response, conflicting request reuse and failure
during compensation. No arbitrary external exactly-once or live-process migration
claim follows. Related principles: B03, B08, B11–B14, B16.

## 4. Ownership covers the whole operation and its final boundary

**Failure mechanism:** an apparent read rolls back the caller's transaction;
cleanup treats a path as proof of ownership; a deferred binding outlives its value;
or state/authority changes after preflight but before the effect.

**Candidate property:** a borrowed resource cannot be finished or destroyed as
an owned one. Acquisition, use, effect and cleanup retain a declared owner and
lifetime. Applicable mutable conditions are checked at the boundary that accepts
the protected read or write, not only at an earlier entrance.

**Mechanism:** owned and borrowed connection/transaction handles, affine cleanup
obligations, role-specific path/handle arguments and owned or lifetime-checked
deferred parameters. A busy borrowed connection refuses a new transaction owner
before BEGIN, without rolling back its caller. A scratch-root parameter cannot
silently accept an executable input. Establish original resource custody before
relying on it for later recovery. A callback that can mutate relevant state
creates a new validation boundary; retain identity/lease and revalidate where
the claimed guarantee requires it.

**Enforcement and limits:** compiler lifetime/role checks and actual runtime,
database or OS adapters must compose. An observation is not exclusion of another
writer; retained bytes are not automatically original object identity. A platform
profile must identify which primitive enforces each claim. Narrow best-effort
cleanup is not exact deletion of arbitrary user data. Ordinary ownership types,
RAII and transaction scopes are baseline competitors. Test foreign additions,
pre-existing transactions, post-acquisition failure, post-callback substitution
and lawful cleanup of one's own disposable object. Related principles: B03,
B08, B11, B13–B15.

## 5. Scope, time and retention compose explicitly

**Failure mechanism:** an empty filtered listing becomes global absence; equal
TTL numbers are mistaken for aligned intervals; cleanup deletes the only witness
needed by later replay; first creation requires an already completed replacement.

**Candidate property:** completeness and absence name a subject, revision and
inventory domain. Time contracts name the start event, clock, precision, deadline
and renewal rule. Recovery does not refresh the original deadline accidentally.

**Mechanism and algorithm:** scoped complete/partial/unavailable inventory values;
leases with origin and explicit renewal; a retention/dependency graph over live
consumers and required evidence; a finite phase model separating creation, use,
replacement, terminal replay and retirement. Check interval containment and
reachable prerequisite cycles before adopting a recovery plan. An expiring
diagnostic audit need not be the durable completion state. A compiler or checker
can expose incompatible promises, but cannot decide which product obligation to
weaken without an authorized revision.

**Costs and limits:** inventory discovery can be incomplete; observations and
clocks have freshness assumptions. Ordinary bounded scans, deadline wrappers and
state machines may supply the same property. Test unknown versus absent, lawful
nested renewal inside an unchanged outer cap, audit expiry after completion,
first-generation creation and interrupted retirement. Related principles: B03,
B08, B10–B12, B14, B18.

## 6. Change obligations reach actual consumers

**Failure mechanism:** a helper passes while the real entry point, middleware,
build target, packaged resource, migration or replay path still uses another contract.

**Candidate property:** for a declared dependency boundary, each affected consumer
has an explicit disposition before the change is admitted. A source definition,
registered test and selected executed test are different relations.

**Mechanism and algorithm:** producer/consumer ports pinned to contract revisions,
an impact frontier, and reuse/regenerate/migrate/retest/unsupported outcomes. Begin
with changed semantic owners; traverse known consumers and evidence dependencies;
stop propagation only with a justified unchanged obligation. Exercise a real small
vertical path as well as isolated functions. Unknown dynamic dependencies remain
visible and require broader checking, isolation or an unsupported boundary.

**Oracle boundary:** establish a valid positive fixture, change the intended
property, and verify that the negative reaches its target predicate. Setup refusal,
skip, empty selection and a different earlier guard are not proof of that negative.
Include intersections of relevant conditions rather than testing each dimension
only in isolation. A generated table is not its own independent oracle.

**Costs and baseline:** ordinary build graphs, LSP, generated schemas, test registries
and integration tests receive the same consumer inventory. Merely adding a graph
does not prove it complete or cheaper. Related principles: B02–B07, B14, B16.

## 7. Context and continuation preserve obligations without growing rituals

**Failure mechanism:** a stale overview overrides a newer decision; a truncated
read is reported complete; the next ready item belongs to another goal; a milestone
is treated as completion of the whole authorized objective.

**Candidate property:** current intent, eligibility, authority, partial completion
and goal completion remain distinct. Missing mandatory context and open effects
survive a handoff. A report or merged component does not erase remaining obligations.

**Mechanism:** source/revision-bound context slices with delivered ranges, omissions
and authorized disclosure paths; a current decision projection with supersession;
and a continuation record containing goal, accepted results, open effects, next
action and the exact dependency preventing that action. Select from the current
goal's authorized ready frontier. An unanswered question blocks only its dependent
action. This is not permission to bypass a denial or a promise of service uptime.

**Costs and baseline:** one compact current view plus existing durable records may
be enough. Repeated historical incidents should refine, merge or retract a small
mechanism catalogue rather than create an ever-growing startup checklist. Preserve
counterevidence and legitimate exceptions outside the short operational view.
Context hashes establish binding, not understanding; retrieval score is not
validity or permission. Related principles: B01, B05–B07, B12–B16, B18.

## Synthetic discriminating cases

These are proposed public qualification cases, not reported executions or changes
to a frozen oracle. A selected experiment must freeze concrete inputs, outputs,
fault points and allowed effects before implementation.

| ID | Controlled counterexample | Required distinction or observation |
| --- | --- | --- |
| OE01 | Identical-shaped values from two declared domains | Implicit substitution refuses; a permitted explicit conversion is separately tested. |
| OE02 | A byte receipt offered as semantic/runtime evidence | Method mismatch leaves that obligation unresolved. |
| OE03 | Equal source bytes in a fixture and a privileged consumer | Reuse content checking while retaining separate binding/applicability. |
| OE04 | An omitted required row or a late malformed receipt | Candidate rows do not redefine coverage; a convenient early match does not hide invalid data. |
| OE05 | A negative fixture rejected before its intended fault point | Report setup/reachability failure, not the intended negative pass. |
| OE06 | A rolls back or remains unknown; B reaches the same state/time | State observation does not manufacture A's success. |
| OE07 | Commit succeeds and its reply is lost | Same-ID/intent reconciliation, with no invented cancellation or blind new effect. |
| OE08 | A helper enters while its caller owns an open transaction | Refuse or use an explicitly permitted borrowing protocol; preserve caller completion rights. |
| OE09 | A foreign object replaces a path or appears during cleanup | Original ownership and exact cleanup scope remain required. |
| OE10 | Authority changes after preflight or a mutating callback | Actual receiver/retained-boundary checking prevents an inadmissible new effect. |
| OE11 | Equal-duration leases have different starts; a lawful nested renewal occurs | Check containment and original cap without banning the lawful renewal. |
| OE12 | Audit expiry or partial retirement removes an earlier prerequisite | Completion does not resurrect; finite recovery does not require a destroyed ordinary input. |
| OE13 | First creation is gated on its not-yet-created replacement | Expose the phase cycle; do not silently weaken deletion/retention guarantees. |
| OE14 | Shared helper changes but one actual caller or selected test does not | Keep the affected obligation open despite neighboring green checks. |
| OE15 | A handoff loses a mandatory range or carries a superseded decision | Mark missing/stale context and retain the current goal and open effects. |
| OE16 | The main goal has one blocked action and an independent authorized step | Continue the latter without switching to an unrelated goal or inventing permission. |
| OE17 | A coarse resource estimate combines mutually exclusive expensive branches | Preserve correlations when refining the bound; distinguish logical charges, bytes, time and measured memory. |

## Placement and acceptance

[Issue #26](https://github.com/llmcomehere/bagaev/issues/26) is the current home for
bounded typed-core and representation work; these candidates refine that research
scope rather than spawn a parallel project. The [roadmap](roadmap.md) places
compiler/type work with language semantics, consumer checks with tool integration,
and durable effects with the store/runtime boundary. The optional documentation
site and frozen P0 support track do not become prerequisites for all candidates.

For each adopted slice, state whether the mechanism prevents an error by
construction, refuses it before admission, detects it during checking/execution,
or supports bounded recovery. Name the enforcing component and its assumptions.
Keep source acceptance, actual runtime conformance and comparative measurements
separate. A pure descriptive-receipt matcher does not implement trusted evidence
or operation authority; a simulation does not demonstrate real crash durability.

Use the foundation's A/B/B-separated/C comparisons and stopping rules. Include
positive controls where existing behavior is correct, costs of setup and upkeep,
failed attempts and false refusals. If ordinary types or existing components
provide the same behavior at comparable cost, no extra language mechanism is
justified by that observation alone. Fewer registry rows, printed tokens or
reported tests are not accepted-change productivity measures.
