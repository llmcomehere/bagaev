# Independent finite probe oracle

The [kernel](../examples/probes/kernel-oracle.json),
[forms](../examples/probes/form-oracle.json) and
[context](../examples/probes/context-oracle.json) contain independent literal
expectations for the accepted [probe contracts](probes.md). They precede
candidate implementations. They do not grant execution authority, implement
the language, or claim runtime, native, comparative cost or model benefit.
The existing frozen L2/APP/P0 oracles remain separate and unchanged.

## Data preparation and observation

Comparison rows use family order `kernel`, `forms`, `context`, then fixture
case file order, then the caller's `required_profiles` list order within each
case. Plans and observations must preserve this exact sequence; a permuted
plan refuses even when observations follow that permutation. Every case has
a source anchor, input, observation key and complete expected value. Family
defaults are part of each case: environment failure, unsupported profile, missing evidence or
an unfinished call is unknown, never a language observation. No-case and
partial results cannot establish a complete comparison. Unknown diagnostics
cannot be replaced by a plausible expected answer.

An `after` sequence is part of one complete case: each step starts again from
the named immutable original fixture, never from a failed partial candidate.
Its entire ordered literal trace is compared, including every representation.
There are 128 named cases (48 kernel/57 forms/23 context) and 40 named mutations
(14/16/10). These counts do not count repeated profiles or trace events as
independent named cases. No trace event may be skipped during comparison.
`K-LAZY` retains its untaken-overflow input and adds an ordered `after` input
with a statically valid untaken nested-loop branch. The selected arm returns
Int64 zero with three ticks; the untaken branch alone would require 1,050,626
ticks. Its complete result, stdout, exit and native ABI are literal data.
`KM-EAGER` preserves the original overflow discriminator and adds a work-limit
discriminator for that trace stage, within the same named mutation.

Kernel shorthand is finite data: `body` denotes one main definition with
params/result explicitly supplied (defaults [], Int64); `functions` overrides
the entire map. Program schema is bagaev-probe-ir/1, entry defaults main.
Arguments default []. Invocation is the exact three-field envelope in probes.
`changes` are sequential literal path replacements/deletions on that envelope,
not repairs. `raw` is exact text instead. `recipe` names only the separately
declared finite construction. Expected `result` vectors are exactly
[status, reason, location, value_type, value, work]. The schema is
bagaev-probe-result/1. JSON driver observations prefix program paths;
invalid IR has no entry/ABI result. Native cases additionally freeze all six
ABI fields in offset order [status,type,value,work,reason,location]. Encode
them little-endian widths [4,4,8,8,4,4], zero all failure value fields; compare
all 32 bytes, not selected fields. Success reason/location become 0/0 in ABI.
All eight input slots are explicit in ABI-only cases. Pointer preconditions
are supplied by a separately admitted driver and are outside language results.
For driver cases compare exact C(result)+LF and exit0, not stderr messages.

Form `body` constructs one main definition params [x]; explicit extra
definitions are included unchanged. Literal pins are in `identity` records;
dependency payloads are explicit data, never discovered by this comparator.
Every semantic case runs json, sexpr and familiar with the exact same
reconstructed program and argument descriptor. Canonical encodings follow
probes; data preparation does not evaluate. `program_change` preserves each
missing/extra/wrong-tag field and does not repin the mutation. Generic negative
roots and definitions remain generic in familiar syntax. Descriptor notation
is the exact tag/payload grammar in probes; `argument` is an ordinary literal
JSON value only when all its tags are unambiguous. Recipes express finite
borrowed values separately. Expected values are literal; success output must
be detached and input/program/patch/retained snapshots unchanged. L2 failure
key is only code with null wrapper location; no backend diagnostic path is
added. `steps` is semantic work independently counted here, not a promise
that the existing API exposes a work counter. An admitted observer must capture
it independently or label that key unknown. Boundary failures have no partial
candidate. Edit observations contain exact code/location or detached-draft
identities plus admission=false and complete reconstructed program/patch.
Successful add/replace fixtures use the literal program/patch objects in data.

Context fixtures contain a complete literal baseline, context, external
expectation, evidence, request and response. A case's `changes` is a finite
ordered list of replacements on those exact records; omission means delete.
The `rehash` list names explicit canonical metadata payloads only, so a case
can challenge expected-map binding rather than fail an earlier content pin.
It never authorizes rewriting the external expectation except when explicitly
listed. No source discovery, provider/model execution or hidden transcript is
an input. Expected events are ordered complete protocol observations, including
evidence applicability, unknown IDs, unresolved effect IDs and admission=false.
A supported evidence label means only the supplied assertion at exact pins.
Absence remains absent. These fixtures do not claim the contract defines a
particular receiver's extra diagnostic wording.

## Comparison boundary

[Comparator source](../tests/probes/probe_oracle_contract.py) accepts raw fixture
bytes with externally supplied exact SHA-256 pins and an independently supplied
complete ordered observation plan. The plan binds case/family/profile, fixture
pin, input pin and applicability plus literal complete expected payload. An
external trusted preparer must freeze that plan before observing candidates.
Each expected payload contains `literal` equal with strict JSON types to the
case's complete frozen expected object, plus any externally prepared complete
wire/trace observations. Omitting or altering the source literal refuses.
Applicability is exactly {state:applicable,pins:{...}} with nonempty exact
digest bindings supplied by the caller; unknown applicability stops comparison.
The comparator cannot synthesize expectations, load ambient files, interpret
recipes, check language semantics, normalize a result, invoke a candidate,
test, model or compiler, or attest actual execution. Candidate-supplied hashes
never replace caller expectations. Its only successful claim is exact finite
literal comparison for the declared complete plan. Strict JSON types distinguish
bool/int/float, missing/null and ordering. Transport failures or unknown evidence
stop comparison; exact equality of all known selected results still proves
neither full conformance nor resource, storage, isolation or empirical benefit.

Mutations identify an obligation, concrete witness and distinguishing wrong
observation. They are source obligations, not seeded candidate implementations
or passing mutation tests. Recipes are finite declarative data only; no fixture
generator or semantic evaluator is provided. Preparation, comparator execution,
mutation execution, all language/native drivers and every optimization mode
remain NOT_RUN. Independent source acceptance and an externally authorized,
reviewed execution profile are needed before any functional evidence exists.

Coverage is intentionally finite. The kernel has no heap/storage/FFI library
bridge. Forms preserve the actual 28 L2 operations, borrowed shallow predicates,
lazy order, transitive pins and atomic edits; they add no typing or arithmetic.
Context covers independent version axes and finite frozen choices, not rank,
solve, model availability, semantic intent, completeness of arbitrary project
knowledge or automatic admission. Boundary recipes remain unmaterialized;
functional nonmutation/aliasing, raw accounting, ABI memory preconditions and
external performance are open evidence obligations.
Finite source coverage does not enumerate every combination of malformed
metadata, every boundary at every byte, or all possible type/error interactions.
Only named inputs and their complete ordered traces are selected. Broader
conformance and any future corpus extension need separate evidence.
