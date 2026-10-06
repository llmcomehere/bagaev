# Experimental component source and connected execution

This non-normative construction makes a component's state/request types,
identity/revision binding and replacement footprint explicit source data.
It connects those declarations to the existing [whole-cycle simulation](probe-whole-cycle.md).
It does not implement the whole proposed language or a production effect receiver.

## Source construction

`bagaev-component-source/1` contains exactly `schema`, `program` and `component`.
The embedded programme uses existing typed-record/10 rules. The component names
one nominal state record, request record, revision record and a pure entry with
exactly `(state, request) -> state`. Its entry must equal the embedded entry.
Identity fields in state/request must share one nominal record type. The revision
field in the request has the named revision record type, exactly `{value:Int64}`.
The direct `replace_fields` list is nonempty, sorted, unique, at most eight fields,
and cannot include identity. Every other state field is preserved.

Reachable owned records currently support required string field descriptors,
Bool, Int64, Text, OptionInt64, TextList and acyclic nominal records. Optional
field omission, Json, RecordList and Variant are outside this construction.
Existing core bounds and typechecking still apply. The envelope adds at most
10,000 JSON values and depth128 within the existing1MiB transport limit.
Metadata names are bounded ASCII identifiers; duplicate keys and malformed JSON
are refused. These limits are a finite experimental scope, not a language-wide
claim that richer owned types are impossible.

An independently supplied `bagaev-component-policy/1` names the component and
operation, bindings, allowed fields and complete reachable nominal record graph.
Matching names alone is insufficient: changed field types or same-shaped renamed
identity records are incompatible. Candidate replacement fields must fit inside
the policy allowance. The policy cannot contain unused record definitions.
Policy data never grants rights. Every checker wire reports
`execution_admission:false`, including successful compatibility checks.

The reader distinguishes source refusal, checked-source/policy refusal and
environment failure. Refusal codes cover format/version/bounds, existing-core
checking, references/signatures, identity/revision, footprint and owned types;
policy mismatch is `CS_POLICY`, malformed policy is `CS_POLICY_FORMAT`.
Successful wires include canonical source/core hashes, bindings, replacement and
preserved fields. Hashes identify content; they do not authenticate an author or
authorize execution.

## Connected path

Two synthetic source components implement the same catalogue transition. S1
normalizes tags inline; S2 extracts a helper. This differs from the old standalone
simulation sources and does not inherit their logical-work expectations.

The explicit catalogue wire adapter constructs nominal EntryId and CatalogRevision
values in ReindexRequest. Actual typed reference execution computes the result.
A typed identity programme validates its result type before checking every
preserved field returned by the component reader. The original catalogue-specific
postcondition remains a redundant independent workload check. Only after both
checks may the simulated receiver mutate state and create its receipt.

Each actual transition records its source/core/input/result hashes and exact
operation key. In WC17, A uses S1 and commits R8; B uses S2 and commits R9; replay
of A retrieves R8 without another pure call or write. These are local observations,
not externally authenticated execution proofs. Receiver rights, admission evidence,
logical clocks, receipt storage and continuation restoration remain simulation
assumptions. No persistence, process-crash recovery or real authorization claim.

## Qualification and reproduction

`examples/probes/component-source/check-cases.json` preserves twelve complete
literal checker outputs frozen before their first execution. Two positive wires
and ten refusals cover nominal confusion, footprint expansion, malformed source
and changed receiver types. The first private implementation matched10/12 because
it emitted a prefixed hash where the frozen wire required plain hex. Correcting
the emitter, without changing expectations, yielded12/12.

The connected runner reuses all17 frozen whole-cycle projections. Three additional
guards corrupt a preserved field, corrupt an allowed field's type, and supply a
same-shaped wrong nominal receiver contract. The first two must refuse before
state or receipt mutation; the third must prevent pure invocation.
This is composition/regression coverage, not17 newly independent scenarios.

Build the reader from `examples/probes/backend/rust/component_main.rs` with the
same reviewed Rust toolchain and existing approved bounded build profile. Build
the existing generic record reference separately. No package downloads or new
execution privileges are needed. Retain each reviewed executable's SHA256 before
running either command in the approved bounded no-network profile:

```
python tests/probes/component_source_checks.py --reader /absolute/component-reader --reader-sha256 RETAINED_READER_SHA --reference /absolute/record-reference --reference-sha256 RETAINED_REFERENCE_SHA --output /absolute/new-check-output
python tests/probes/component_cycle.py --reader /absolute/component-reader --reader-sha256 RETAINED_READER_SHA --reference /absolute/record-reference --reference-sha256 RETAINED_REFERENCE_SHA --output /absolute/new-cycle-output
```

Output directories must be new; their parents must exist. Input manifests are
verified before execution. Keep binaries and inputs owner-controlled throughout.
The check-only harness requires the reference argument for a shared invocation
contract but does not invoke it. No timing, model or allocation measurement is
performed. L2/Store/P0 and normative foundation are unchanged.
