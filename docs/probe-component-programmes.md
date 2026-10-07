# Source admission, pinned runs and generic owner

Experimental contract; initial manager cases and connected expectations were frozen before their respective implementations.

Keep the already-reviewed generic Owner implementation unchanged. A small host
ProgrammeManager extends composition with a source registry/default and pinned
run IDs. Do not duplicate state or operation receipts. Initial live Owner contains
only S1. The manager's base is an immutable component identity, distinct from the
owner's mutable application revision. A run pins one admitted source; no moving
latest reference is serialized in an operation's intent.

## Admission boundary

1. Read/validate a checked component draft, expected old source head and complete
   receiving graph. Retain independent receiving policy and profile descriptor.
2. Verify exact retained synthetic qualification bytes and their actual producer
   identities for this owner/manager profile. The old catalogue receiver bundle
   is incompatible. Use the existing five-obligation matcher and validate every
   wrapper/group before any acceptance. Missing, conflicting and malformed
   evidence retain existing priority. Evidence supplies no authorization.
3. Actually check candidate source against the same receiving policy. This host
   checker can fail or allow a controlled interleaving; no live source/default
   update has happened yet. Candidate hash must equal the qualified draft target.
4. At the final boundary, read current trusted admission permission and compare
   current source head to expected base again. Also recheck source registry bound.
   A changed base or revoked permission rejects without adding candidate/default.
5. Register the immutable candidate and publish new default without an intervening
   callback. Never mutate live application state, operation ledger or existing
   run pins. Physical crash atomicity is not established by these Python writes.

Registration is trusted host composition, not an API by which source/context data
selects executable code or grants authority. Source read/check is independently
configured. Initial qualification instances may explicitly admit both sources for
isolated tests under the approved execution profile; live application admission
must still follow the five-obligation transition above.

## Invocation and continuation

start_run(run_id) pins current default if ID is fresh; a duplicate ID cannot repin.
submit(run_id,packet) requires packet source equals the run's immutable pin before
calling the generic owner's submit. Old runs may continue using their admitted
source after a new default. observe preserves exact packet intent and uses the
owner's current observation permission; it cannot infer outcome from live state.

A pending continuation carries a pinned programme source and exact generic packet.
Context uses component-context/1 with separate current/old sources and exact open
facts. A versioned new pending payload declares its packet shape explicitly; never
reinterpret the old catalogue-shaped pending payload under the same version.
Reconstruction compares both current default and retained run identity, then exact
pending intent/key. It restores explicit caller data only, not live state/ledger,
permissions, callbacks or sockets. A forged packet/key/source refuses before
observation and cannot become a fresh submit.

## Independently expected connected path

Live state begins atR7, manual[family], indexed[old]. Run original pins S1.
A/S1 computes and commitsR8,indexed[new],reply is lost. Capture pendingA/S1.
A readable S2 edit produces a detached checked draft. Compatible freshly qualified
five-obligation observations permit source admission and defaultS2; state remains
R8 and A ledger row/run pin unchanged. Run new pinsS2. B commitsR9,indexed[next].
Reconstructed old continuation observes exactA/R8/indexed[new] while live state
remainsR9/indexed[next]. Only two application evaluations occur in the live path,
with source orderS1,S2. Source checking and isolated qualification are separate.

## Required negative cases before implementation

Unknown S2 use before admission; run/source mismatch; duplicate run ID repin;
missing actual consumer; an applicable conflict plus a missing obligation;
malformed late receipt; old-receiver profile substitution; changed owner producer;
stale source head before/after checking; current admission permission revoked
at final boundary; candidate hash substitution; forged pending key/source/request;
current observe denial after reconstruction. Every rejection preserves the live
state/ledger/old-run identities appropriate to that point. Capacity refusal cannot
silently discard old source/operation history.

Next freeze exact result records and projected snapshots for these cases, then
implement the minimal manager and qualify fresh owner-bound observations. Keep
qualification timestamp and live execution timestamp distinct in every report.


# Avoid a self-certifying admission loop

Before implementing the connected manager, distinguish what each witness proves.
A qualification run may provision S1/S2 explicitly as trusted isolated test inputs.
This is permitted execution of own reviewed code, not evidence that live admission
already happened. It can test source checking, preserved fields, actual dispatch,
old receipt replay and immutable source/run association. Its provisioning premise
must be retained, not hidden inside a pass receipt.

A live instance starts with only S1. A manager's source-registration transition
checks the newly qualified observations with the existing actual matcher before
adding S2. Final current authority/head checks remain independent of all evidence.
Qualification does not prove authenticity of its producer or grant permission.

If an isolated manager trace needs an admission decision in order to test run
continuity, label that decision as a controlled trusted qualification premise.
The output can qualify the observed old/new run behavior, not its own admission
precondition. Separately test the actual admission matcher and live transition
against missing/conflicting/wrong-profile/stale/denied controls. Do not describe
one passing trace as an end-to-end proof of all premises or all possible histories.

The fresh graph must bind exact owner and manager/adapter producer identities and
new frozen scenario bytes. The older catalogue qualification's source/policy hashes
may match, but its receiver/profile does not. A wrapper must not erase that difference.

Prefer the smallest explicit division: finite independently frozen runtime cases
qualify observed behavior under stated setup assumptions; fixed matcher tests qualify
applicability/decision logic; the final live trace checks their composition. All
three remain serial in-memory experiments under the approved bounded profile.

## Reproduction

The [manager](../src/bagaev_component_programmes.py) composes the unchanged generic
owner with [pure admission logic](../src/bagaev_component_admission.py). The latter
is extracted without changing the prior decision body; the old component-change
runner imports the same implementation and retains its original fixtures.

Run `tests/probes/component_programme_checks.py` for eleven fixed decisions and
`tests/probes/component_programme_cycle.py` for the complete composition. Both take
absolute `--reader`, `--reference`, `--matcher` paths, the corresponding separately
retained `--reader-sha256`, `--reference-sha256`, `--matcher-sha256`, and a new
absolute `--output` directory with an existing parent. Use the already reviewed
component reader, typed-record/10 reference and /8 obligation matcher described in
[component source](probe-component-source.md) and [change](probe-component-change.md).
Execution still requires separately approved bounded/no-network conditions. Neither
a path nor its hash authorizes executing untrusted binaries.

The [frozen inputs](../examples/probes/component-programmes/inputs.json) include
[decision cases](../examples/probes/component-programmes/manager-cases.json), the
[complete path](../examples/probes/component-programmes/connected.json) and
[restore refusals](../examples/probes/component-programmes/restore-cases.json).
The `owned-record-pending/1` payload is new; the old pending-payload contract stays
unchanged. Reconstruction returns caller data only. Wrong independent pending pin,
changed current head and rebound old run refuse without state/ledger mutation.
Duplicate-run and wrong run/source guards prevent repinning or dispatch substitution.

Observed finite qualification: eleven decisions,25 actual data/reference calls and
27 matcher calls. Complete two-phase path:61 data/reference calls and6 matcher
calls;7 qualification application evaluations (two trace,four literal values,one
S2 frame guard) and2 later live application evaluations. These counts describe
actual bounded work, not a performance or cost comparison. Input/output and producer
hashes preserve applicability, not authenticity. Controlled qualification admission
premises are recorded explicitly. Old catalogue observations are not relabeled as
evidence for this receiver. Full language, durable runtime and real authority remain
unestablished.
