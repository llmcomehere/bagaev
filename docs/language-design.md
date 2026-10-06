# Whole-language design sketch

Working architectural proposal, October 6, 2026. This note connects the
[foundation's B01–B18](foundation.md#foundation-propositions) and
[operational candidates](operational-semantics.md) into one proposed language
model. It is **not a normative successor to L0/L2, Store/1 or frozen P0**, an
implemented surface syntax, a production runtime, a changed execution policy
or a report of new experiments. [README](../README.md) owns implementation
status; [the roadmap](roadmap.md) retains the current stage gates.

## One language for behavior and its change

The central proposal is a small typed computational core with explicit
contracts for components, state, operations and changes. A program describes
behavior. A change describes a candidate transition between program snapshots,
its affected obligations and the conditions for admitting it. Both share
stable identities and versioned relationships. They do not require one global
database, scheduler, model vendor or always-present LLM.

Start with ordinary computation. A pure function receives immutable values,
constructs a result and has no ambient access to clocks, randomness, storage,
network or models. It needs neither a durable journal nor an operation receipt
for every expression. Stateful components add those obligations only at the
boundaries whose effects must be controlled or recovered.

The hypothesis is that this common account of behavior and change reduces
semantic gaps and full accepted-change cost. Strong ordinary-language systems
with nominal types, contracts, structural editing and durable workflows can
provide many of the same properties. This sketch does not establish a benefit
or novelty for the combination.

## A program to read before the machinery

Consider a catalogue entry with manual and automatically indexed tags. Reindexing
replaces only indexed tags. A pure transformation can be read as follows:

```text
record Entry { id: EntryId; manual: Set<Tag>; indexed: Set<Tag> }

pure reindex_entry(entry: Entry, tags: List<Tag>) -> Entry {
  return Entry {
    id = entry.id,
    manual = entry.manual,
    indexed = canonical_set(tags)
  }
}
```

This is illustrative notation, not accepted source syntax. `canonical_set`
uses a pinned equality/order policy. With manual `{family}`, indexed `{old}`
and input `[new,new]`, the expected new entry has manual `{family}` and
indexed `{new}`; the old immutable value remains unchanged. No external write
has occurred merely because the function returned that value.

The stateful operation places that computation inside an explicit boundary:

```text
component Catalog {
  state entries: Map<EntryId, Entry> versioned by CatalogRevision

  operation reindex(id: EntryId, tags: List<Tag>, base: CatalogRevision)
    -> Outcome<CatalogRevision, CatalogError>
    effects { write(entries[id].indexed) }
    guarantees { after[id].manual == before[id].manual }
  {
    return atomic entries expecting base {
      entries[id] = reindex_entry(entries[id], tags)
    }
  }
}
```

The frame condition preserves every other field and entry, in addition to the
shown manual-tag guarantee. A component contract also defines valid IDs,
collection limits, missing-entry errors, timing and progress assumptions.
A nominal domain prevents implicit substitution of unrelated values; its name
does not authenticate their provenance.

For the proposed first state profile, `atomic` permits pure computation over
one state owner's data. At commit that owner checks the expected revision,
current rights, admitted write epoch and supported transition obligations.
The state change and operation receipt share one atomic boundary. An arbitrary
network call cannot be hidden inside this region: a local transaction cannot
make an unrelated service participate in it.

The operation returns a confirmed transition outcome or an explicit refusal or
unknown observation. The new revision is a result of commit, not of ordinary
record construction. Requested cancellation, confirmed cancellation and a lost
response have different meanings.

## Semantic objects

| Object | Meaning and key relationships |
| --- | --- |
| Type and value | Domain, valid representation and permitted operations. |
| Definition | Typed parameters, expression body, return type, effects and immutable revision. |
| Component and contract | Inputs, allowed observations, forbidden effects, required progress and assumptions. |
| State and resource | Identity/incarnation, owner or coordination protocol, revision, lifetime and access boundary. |
| Operation and run | Stable intent, pinned behavior, attempts, observations and unfinished effects. |
| Revision and snapshot | Immutable content and an exact selection of dependent revisions. |
| Change | Base snapshot, candidate, affected consumers/obligations and proposed admission. |
| Evidence | A claim, subject/revision, method, scope, assumptions, outcome and trusted production boundary. |
| Task and context | Current goal, exact sources, accepted results, missing material and next eligible action. |

Stable identity, immutable revision and display name are separate. Renaming an
object does not break its semantic reference. A snapshot resolves dependency
selection before execution; a hidden moving `latest` reference is not a pin.
A computation graph, a project dependency graph and one run's state machine
are different structures even when an implementation stores them together.

Large data need not appear in source or model context. Typed references state
where data can be accessed, their versions and disclosure rules. Model working
context is not the same object as application input.

## The computational language

Proposed core values include disjoint Bool, integer and text types, bytes,
Option, named records, closed variants and declared collection types. Function
boundaries have explicit types; local inference removes mechanical annotation.
Ordinary values are logically immutable and may share storage. Resource handles
have separate ownership and lifetime rules.

The expression vocabulary includes literals, lexical bindings, function
application, record construction/projection, variant construction and exhaustive
matching, lazy conditionals and collection traversal. Effect signatures compose
through calls: passing a function through another function cannot erase its
observable effects. Imports bind an exported contract revision and its supported
implementation rather than an unexamined name.

General recursion, higher-order functions and parameterized types belong to the
whole-language design space; their exact rules are not fixed here. A finite
initial profile can select first-order functions, bounded traversal and no
recursion. It must explicitly refuse unsupported programs rather than imply
that type correctness proves termination. That implementation subset is not a
claim that the final language is only a catalogue DSL.

A profile defines numerical types, overflow, collection bounds, evaluation
order and supported failures. One proposed first subset uses signed Int64 with
an explicit overflow error, exact validated text, left-to-right eager operands,
and only the selected conditional/match branch evaluated. Unsupported syntax
in an unselected branch is still structurally invalid. A logical work limit
remains a semantic quantity; it is not measured CPU time or process memory.

Absence, null, empty and explicit clearing are distinct. A patch type such as
`Keep | Set(T) | Clear` avoids conflating them. A dynamic codec preserves the
required lexical or semantic distinction; normalization cannot silently change
the bytes whose origin or signature is being checked.

An ordinary nominal wrapper may be explicitly unpacked and reconstructed.
Where such relabeling must be prohibited, an opaque constructor and actual
trusted boundary are required. A type name, hash or well-shaped JSON object
cannot manufacture a capability.

## Contracts, resources and effects

A contract specifies permitted observable traces and required progress under
named assumptions. A component that remains silent forever may violate it even
when it never emits an incorrect value. Equivalence or refinement of arbitrary
programs is not automatically decidable; unsupported proof obligations remain
unknown or require another accepted checking method.

Application refusal, language error, admission refusal and environment failure
are separate. Out-of-memory, unavailable storage or a crashed process cannot
be reported as an ordinary successful empty result. A pure return has detached
value ownership at the relevant boundary; later calls must not mutate an old
exported answer through a reused buffer.

An owned resource may be transferred or completed according to its protocol.
A borrowed transaction does not grant commit/rollback rights. Deferred use must
own its data or retain a valid lifetime-checked borrow. A callback that can
change relevant state introduces another final-boundary validation requirement.
Compiler lifetime checks and runtime/database/OS adapters have to compose.

State has an owner or a declared consistency protocol. The first proposed
profile has one serialized state owner. It does not promise distributed atomic
commit, automatic invariant-preserving merge or a total network event order.
An asynchronous port states ordering, bounded queue and overload behavior:
waiting within a deadline, refusal or explicitly permitted dropping. Silent
loss cannot replace a promised operation outcome.

## Operation identity and observed outcomes

An operation key includes receiver domain, resource incarnation, submitting
domain and operation ID. Immutable intent includes behavior revision, exact
validated input, expected state revision, write epoch and original deadline
policy. A retry preserves intent. Changing those material fields is a new
intention, not an automatic repair of a timed-out request.

Persist the information needed for reconciliation before crossing the effect
boundary. The receiver can bind current authorization, mutation and receipt
atomically only where its actual profile supports that guarantee. Other
receivers expose weaker behavior; no arbitrary external exactly-once promise
follows from adding an ID.

Receiver state and observer knowledge are distinct:

| Observer knows | Meaning | Permitted continuation |
| --- | --- | --- |
| Not dispatched | No dispatch in the stated boundary is confirmed. | Fix the local cause and recheck current eligibility. |
| In flight | An attempt began without a known terminal outcome. | Wait or request permitted cancellation. |
| Outcome unknown | The receiver may already have committed. | Reconcile the same key and intent; do not invent a fresh effect. |
| Terminal observed | A valid applicable receipt is available. | Use that historical result within its revision and disclosure scope. |

A later transport error does not erase an already observed terminal fact.
Conflicting applicable terminal receipts are a consistency failure, not a
choice of the more convenient result. Current state reached by operation B
never becomes a receipt proving that A succeeded.

### Replay and current authority

The proposed receiver first validates/authenticates the request within its
allowed lookup boundary. For an already bound key, it compares exact intent
and does not repeat mutation. Before revealing the old payload it checks current
permission to observe that result. A mismatch returns a conflict without a
second effect or inappropriate disclosure.

Only a new execution checks fresh-write conditions such as deadline, current
write epoch and expected data revision at commit. A successful operation may
have invalidated its original revision precondition itself. Requiring that
old precondition before terminal lookup would incorrectly block its replay.
But permission to replay a private result is still not permanent.

An access refusal during observation does not rewrite the original operation
as failed. Execution permission, cancellation permission and result-disclosure
permission remain distinct. These are proposed rules for a new profile; they
do not rewrite the frozen P0 command-verification order or Store/1 ownership
assumptions.

### Cancellation, retention and resumption

In the first proposed atomic profile, an authorized cancellation ordered before
commit establishes a terminal, intent-bound cancelled record. A delayed matching
request encounters it. Finding no row alone cannot confirm cancellation if the
original request may still arrive. A receiver unable to establish the required
binding reports unconfirmed cancellation.

Cancellation after commit reports already applied when disclosure is allowed;
it does not undo the write. Compensation is a new operation with its own
current target, authority and outcome. Partial multi-step compensation/cancellation
requires a different profile with already-performed effects represented.

A long-running task resumes at named logical points with serializable state,
pinned behavior and unresolved operation references. It does not serialize an
arbitrary live stack, socket, borrowed handle, transaction or raw pointer.
Reacquiring a resource checks incarnation and current rights. A pure segment
may be recomputed; a significant effect is first reconciled by its prior ID.

Deadlines name their origin and clock domain. Retry/restart does not silently
renew them. A nested lease can lawfully renew within its unchanged outer cap.
Clock conversion across restart requires an explicit supported rule.

Durable terminal facts and disposable diagnostic logs may have different
retention periods. Removing diagnostics must not resurrect completed work.
A profile promises a reconciliation horizon and accounts for live consumers
before retirement. After that guarantee ends, a missing receipt remains an
expired/unknown observation, not proof of non-execution. Infinite duplicate
suppression cannot coexist with finite deletion of all its witnesses.

Inventory completeness is similarly scoped: complete, partial and unavailable
are different values. An empty filtered result is not global absence.

## Changes, evidence and runs

An illustrative structural proposal is:

```text
change Catalog.reindex from snapshot S1 {
  replace behavior with candidate C2
  preserve contract ManualTagsSurvive
  require check ChangedConsumers
}
inspect change
check obligations
admit candidate for new runs
```

The notation expresses a proposal, not a currently executable command or an
instruction to an external tool. A change names stable owners, expected base
and candidate revision. It does not mutate an executing process in place.

The checking frontier starts with changed definitions, contracts and actual
consumers, then follows dependent obligations and evidence assumptions. A
consumer receives an explicit disposition: unchanged/reuse, regenerate,
migrate, retest or unsupported. Propagation may stop only with a justified
unchanged obligation. Unknown dynamic dependencies require broader checking,
isolation or an explicitly unsupported boundary. A graph is not proof of its
own completeness.

The admission receiver obtains its full obligation set from the accepted
contract. Candidate-supplied rows cannot shrink it. Evidence binds claim,
subject/revision, method, inputs, consumer, assumptions and outcome. Byte
matching, static checking, executed tests, runtime observation and human
acceptance are different grounds. No universal PASS converts one into another.

A descriptive imported receipt does not create trusted evidence. Authentication,
trustworthy observation and current admission authority remain separate.
Even a signature binds a key, not truth. Equal content can justify reusing a
content check while different callers or deployed instances still need their
own applicability checks. Conflicting applicable evidence is retained as a
conflict.

By default a new admitted program applies to new runs. Old runs remain pinned
to old behavior and may continue only while their state/authority assumptions
are compatible. A source-head change is not a resource-side write fence. If
old writers must be excluded, the actual state receiver orders the cutoff with
writes. Effects committed before that boundary remain historical facts.

Code replacement, state migration and permission change are separate
transitions. Migration names original/target schemas, preconditions, interruption
protocol and checking. It is not inferred from matching function signatures.
Reverting code cannot cancel an already dispatched action or undo the world.

## Models, context and representations

The canonical subject is a typed semantic model of behavior and changes.
Readable text, structural editing and exact serialization are representations.
Round trips must preserve the declared meaning; JSON, binary or familiar text
is not preselected as economically superior.

A model receives a task-bound working set, pinned sources, constraints and ways
to reveal missing context. It may generate, refine or select bounded candidates.
A partial stream remains a draft and cannot execute as an admitted program.
Models may be absent from ordinary application execution.

Exact recoverable state survives the loss of a session, model or accelerated
cache. A summary/embedding names its source and omissions. Context retains the
current goal, decisions, obligations, accepted results, open effects and next
eligible action. Missing mandatory ranges remain visibly missing; a source
hash is not proof that an executor understood them.

Program, data, contract, protocol, representation and model-profile versions
are separate. A successor negotiates supported versions and checks current
rights rather than inheriting authority from a handoff. A report or merged
component completes its scope, not the whole open objective. An unanswered
question blocks only the action that needs its answer.

Disclosure restrictions also cover summaries, embeddings, caches and diagnostic
data. A format change does not erase the source's transfer policy. A remote
model or another executor is selected only within available authority.

## Execution targets and extension boundaries

The compiler owns meaning, evaluation order, failures, source linkage and
valid transformations. A backend owns its selected machine-generation task.
Using LLVM or another backend does not require a Python application runtime
or give up the language's own semantics.

A target profile declares numerical behavior, precision, data representation,
placement, limits, effects and dependencies. CPU, GPU, remote and managed-library
profiles can differ. Transfer, synchronization and preparation count when
choosing placement. Unsupported requirements are refused explicitly.

External libraries have pinned interfaces/adapters, ownership, effects, errors
and cancellation rules. In-process native code shares an address space; an
effect annotation does not isolate untrusted code. Unsafe boundaries remain
part of the stated trust assumptions.

An extension requires a version, meaning, types, effects, checking method and
execution route. A receiver never guesses an unknown required operation from
its name. Learned codecs, model training, accelerator synthesis and distributed
profiles remain separately scoped research directions.

## Four complete paper scenarios

These are logical walkthroughs of the proposal, **not executed tests**.

1. **Reindex while preserving manual data.** An entry at R7 has manual `{family}`
   and indexed `{old}`. Pure computation returns indexed `{new}` and preserves
   ID/manual. The receiver checks R7 and current rights, commits R8 plus A's
   receipt atomically, and preserves every other entry. Wrong nominal ID,
   stale revision or attempted manual overwrite prevents that transition.
2. **Lose the reply after commit.** A commits R8; its reply disappears. The
   caller records unknown outcome. A successor uses the same key/intent and
   obtains the old receipt when authorized, with no second write. Expired write
   deadline need not invalidate an old result. Revoked observation permission
   can prevent disclosure without changing whether A actually committed.
3. **Change behavior with an old run active.** X is pinned to S1 while C2 proposes
   S2. Required consumer obligations are checked. New runs can select admitted
   S2; X's old result is not relabeled. A needed write cutoff is enforced at the
   state receiver. Prior committed effects remain historical; migration is
   explicit and code rollback is not compensation.
4. **Resume development after context loss.** A new executor receives the current
   goal/S2 plus an unresolved A under S1. It detects an old summary, resolves
   exact sources and retains A's actual observation route. Missing authority
   does not become granted by the packet. Independent authorized pure work can
   continue while one external observation is unavailable.

Useful intersections include cancel-before-registration followed by delayed
submit; late cancellation after commit; resource-name reuse with a new
incarnation; diagnostic expiry inside the reconciliation horizon; and an
already observed receipt followed by a transport failure. Each needs a valid
positive setup and a negative that reaches its intended predicate.

## Coverage of B01–B18

This is architectural placement, **not acceptance of eighteen implemented
principles**. The foundation retains their full meaning and limits.

| Principle | Proposed construction/enforcer | Distinguishing limit |
| --- | --- | --- |
| B01 Intent | Versioned goal, contract and independent expectations. | A precise record cannot prove understanding or repair its own success criterion. |
| B02 Meaning | Nominal domains, typed relations, stable identity and revision. | Equal bytes do not merge subjects; lawful explicit conversion remains possible. |
| B03 Boundaries | Components with trace and progress contracts. | Always silent is not necessarily conforming. |
| B04 Forms | Exact semantic model and checked representations. | Lossy views expose omissions; search score is not identity. |
| B05 Context | Source-bound decisions, obligations and open effects outside sessions. | Missing or stale text is not full current context. |
| B06 Models | Separate capability/profile and protocol versions. | A new model may not support a form; hidden internals are not guessed. |
| B07 Checking | Obligations, candidates and trusted admission methods. | Type correctness, testing and proof have different grounds; unknown is not pass. |
| B08 Effects | Explicit operations, state, ownership and outcomes. | Timeout does not cancel; a borrowed transaction cannot be completed as owned. |
| B09 Execution | One stated meaning across supported reference/backends. | Optimization preserves observations; ordinary applications need no LLM. |
| B10 Devices | Target/numerical profiles and placement constraints. | No automatic GPU or real-time support. |
| B11 Distribution | Explicit receiver/consistency profiles and unknown outcomes. | No global ordering or availability under every partition. |
| B12 Continuation | Pinned runs, logical checkpoints and terminal facts. | Arbitrary sockets, pointers and live transactions do not migrate. |
| B13 Cooperation | Task-bound changes and checkable handoff. | Agent agreement does not replace acceptance or receiver cutoff. |
| B14 Integrity | Consumer frontier, old-run pins and explicit migration. | Dynamic unknowns remain open; code rollback does not undo effects. |
| B15 Authority | Opaque capabilities and actual final-boundary enforcement. | Hashes, role names and declarations do not grant rights. |
| B16 Observation | Source/run/input-bound diagnostics with units and phases. | Logical work, requested bytes, RSS and elapsed time are not interchangeable. |
| B17 Extension | Versioned semantics, checker and declared adapter. | Unknown required forms refuse; learning has a cost. |
| B18 Cost | Comparable whole outcomes and retained negative findings. | Efficiency cannot be guaranteed by a language construct. |

## Reuse and the first vertical implementation

The existing code is useful material, not a discarded predecessor:

- [L2](l2.md) already supplies pure definitions, lazy control, structured changes
  and pinned snapshots. Its dynamic JSON semantics remain unchanged.
- [Store/1](store.md) already binds admission operations to exact continuation
  requests and replays their old receipts before fresh base/head checks. Its
  receipts concern program admission, not arbitrary catalogue mutations.
- The [typed profile family](probe-record-source.md) supplies bounded nominal
  records, variants and computational composition. Its reference evaluator
  can be a first computational route without requiring a new native experiment.
- The existing [integrated beta](beta.md) retains its historical bounded results;
  this proposal does not claim to have rerun them.

The proposed first vertical path is typed pure computation → component contract
→ simulated domain-state receiver → pinned candidate/admission → resumed
observer. Source identity, invocation, pure result and committed receipt have
explicit distinct bindings. The real entry point must exercise the whole path,
not only an isolated helper.

There are concrete compatibility gaps. Store/1 accepts L2 sources, so it cannot
silently admit a typed-profile source under the same kind/checker. A new bridge
needs its own versioned source/admission contract. The generic typed-record/10
reference invocation supports nominal arguments; its separate prepared Json
API deliberately requires Json-only entry parameters. Map/Set notation in this
sketch does not expand existing list capacities or create generic collection
types. A first demonstrator must state its narrower supported domain.

First finish the semantic composition and independent expectations. Then freeze
one selected profile, prepare the bridge and run a bounded reference demonstration
under its accepted execution conditions. A simulated receiver checks the proposed
state machine, not real durability, clock validity, access control or deployment.
Real state/security adapters require their own admitted profile and evidence.
Existing L2/Store/P0 contracts must not be weakened to make a new example pass.

## Open choices and reasons to reject the design

The working choice is a typed core, immutable ordinary values, explicit effects
and resources, operation identity, first-class changes and revision-bound
obligations/context. Physical graph/term layout, memory management, storage,
transport, surface syntax and backend selection remain open. Those choices must
satisfy the semantic obligations before their speed is compared.

A common semantic model may cost more than exact interfaces among existing
systems. Excessive metadata for a simple function, duplicated status registries,
manual bookkeeping and a language whose annotations have no enforcing boundary
are reasons to simplify or reject a candidate. Mechanical identity fields should
be derived when possible; durability is added only where required.

The next useful result is a coherent supported vertical program, with clear
remaining unknowns. Measurements belong at material design choices and complete
comparable scenarios; correctness checks remain mandatory when implementation
changes. Neither this document, its CI, a successful merge nor a set of paper
walkthroughs establishes runtime conformance, model benefit or lower full cost.
