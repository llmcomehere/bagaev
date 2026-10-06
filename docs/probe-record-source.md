# Experimental structured source profiles

This separate reference-language family extends the bounded primitive/Text/list
probe without changing those earlier source schemas. The implementation constructs
checked IR and evaluates explicit invocation data; it does not authorize native
execution. Each CLI selects its profile explicitly. Earlier schemas keep their
old limits and refuse later operations.

| Profile | Addition | CLI |
|---|---|---|
| typed-record/1 | Nominal flat internal records, constructor and field projection | record_main.rs |
| /2 | Exact flat record arguments and owned record result JSON | record_io_main.rs |
| /3 | Acyclic nested records and forward type references | record_nested_main.rs |
| /4 | Named bounded lists of records | record_list_main.rs |
| /5 | Nominal variants and exhaustive match | variant_main.rs |
| /6 | Bounded raw JSON views for staged source-level validation | json_main.rs |
| /7 | Optional OptionInt64 field metadata and omission of None | optional_fields_main.rs |
| /8 | Explicit composition limits:32 functions and2048 expression nodes | composition_main.rs |
| /9 | Immutable TextList append with the same /8 limits | list_push_main.rs |
| /10 | Immutable nominal record-list append, same capacity bounds | record_list_push_main.rs |

Invocation/result schemas use bagaev-typed-record-invocation/N and
bagaev-typed-record-result/N. The checked program schema is bagaev-typed-record/N.
Literal valid and refusal examples are under examples/probes/records. A portable
Rust test template under tests/probes/backend repeats104 existing complete wires;
compilation and execution require their own bounded profile.

## Structures and observation boundaries

Records have canonical named field order, nominal identity and exact argument
objects. Constructors evaluate every field left-to-right. Fields flow through
helpers, locals, branches and bounded loops. /1 refuses records at the entry
boundary; /2 and later export detached JSON record values. /3 checks all named
references/cycles/expansion before function checking, including unused definitions.
The shared record/list/variant graph has at most8 named definitions and4096
logical descriptor units. Record fields and variant alternatives are bounded by8;
named record lists have capacity0..4. Earlier primitive TextList limits remain.

Record and record-list results have value_type Record:NAME / RecordList:NAME.
Variant results have value_type Variant:NAME and value {case:ALT,value:PAYLOAD}.
This generic wrapper is distinct from an application's payload response. Match
must cover every alternative exactly once; all arms typecheck and share a result
type, while only the selected arm evaluates.

Json views distinguish missing, null, Boolean, integer tokens, other number tokens,
text, arrays and objects. Generic field/index/int/Text projections contain no
catalog logic. Invalid Text is not silently normalized. Views cannot escape as
entry results or become record/variant payload types. JSON field lookup, integer
conversion and successful Text projection carry explicit bounded work charges.
Raw argument storage/admission is distinct from logical execution work.

In /7, a field descriptor may be exactly {"type":"OptionInt64","omit_none":true}.
Its source constructor still supplies an Option value. Absent input key means
None; explicit null is refused. Export omits None and preserves Some(0).
Ordinary string-declared OptionInt64 fields remain required and accept null=None.
No field name, date range or application refusal phase is hard-coded.

All profiles retain expression depth32, program JSON8192 values, invocation
JSON16384 values, work65536, up to8 parameters and existing bounded Text/list
rules. /1–7 retain8 functions/512 expression nodes; /8 through /10 use the higher two
structure caps. Structural/work bounds are not latency or whole-process resource
measurements.

## Catalog source composition

examples/probes/catalog-source/program.json expresses the existing
[catalog-application/2](application.md) workload in ordinary source definitions.
It has24 functions and1087 expression nodes. Validation priority, exact request
shapes, optional dates, reindex replacement, origin preservation, tag normalization
and date/ID ordering are implemented in source. No opaque catalog callback or
oracle-derived response is embedded in the interpreter.

The source matched all99 existing literal catalog-cases/2.0.0 responses and the
four-step EVOLUTION chain using actual predecessor states. A strict data bridge
checked the result envelope and extracted the generic variant payload. Seventeen
concrete source mutations produced normal-exit wrong complete responses and were
detected, including refusal-priority changes. Replaying stages/profiles reuses
existing cases and is not additional independent semantic evidence.

The serialized bounded invocation domain is narrower than the abstract Python
value-level application contract. Arbitrarily large finite values can encounter
admission/work limits, so these finite matches are not all-domain application
conformance. Input wire/value preservation and detached JSON container checks are
not native pointer/alias proofs. Review was a separate same-maintainer pass,
without independent reproduction. This source slice establishes no native
record/JSON execution, full production acceptance, speed, token-cost or uptime
advantage.

The [/9 append contract](probe-list-push.md) defines its additional operator,
work charge, refusal priority and distinct native output version.

The [/10 record-list append contract](probe-record-list-push.md) keeps exact
nominal element identity and the declared list capacity.
