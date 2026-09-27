# Model proposals and portable continuation

Contract: bagaev-model-task/1 and bagaev-model-response/1. This bounded,
provider-neutral library prepares proposals for [L2](l2.md) and a matched ordinary
Python comparison. It never calls a model, executes source, opens a file/store,
starts a process or performs admission. Candidate source and authored tests are
not model or runtime evidence. See [README](../README.md) and Issue #5 for status.

## Library and trust boundary

Import src.bagaev_model. All functions are pure with detached return values:

| Function | Result |
| --- | --- |
| canonical(value), decode(bytes), digest(value) | Bounded exact JSON bytes, detached value, or SHA-256 identity of canonical bytes. |
| inspect_source(variant, source) | {source, definitions:[{id,signature,pin}]}; Python pin is null. |
| make_packet(fields) | Canonical packet bytes; supply all fields below except packet_id. |
| read_packet(bytes) | Validated detached packet. |
| read_response(packet_bytes, response_bytes) | Detached response bound to this packet, without constructing/executing the change. |
| propose(packet_bytes, response_bytes) | {source,source_id,change,changed}; constructed candidate and actual named edit, never an acceptance result. |
| continuation_view(**fields) | Validated allowlist of explicitly supplied public continuation facts. |
| append_attempt(records, packet_bytes, response, outcome) | New attempt list, with exact replay or conflict refusal. |
| cost_totals(records) | Separate per-unit/category totals, C_dev and C_full; unknown remains null. |

The receiver owns current authority, transport, persistence, checking and
public/hidden separation. A packet is data, not an authorization token. Hashes
bind content without authenticating it. Returned source, model prose, references,
hypotheses and observations grant no action. No provider dependency, SDK,
credential, billing policy or scheduler is included. A caller must not mutate
borrowed input concurrently with a call.

For L2, the new L2.prepare_patch(original, add, replace) computes transitive pins
and target identity and returns an ordinary bagaev-l2-patch/1. It checks the base,
map shapes, disjointness and membership, then the whole resulting program; it
neither evaluates nor admits it. Existing L2.apply_patch and all old semantics
remain unchanged. Proposed results must fit the model transport as a whole.

For Python, source identity hashes exact UTF-8 source bytes. The entry is an
ordinary synchronous evaluate function with one positional parameter and no
variadic/keyword-only parameters. The adapter parses an AST but does not compile,
import or execute it. It inventories and adds/replaces complete named top-level
functions, including their decorators. A replacement must contain exactly one
function with the matching name. Duplicate names, absent replacement targets,
existing addition targets and overlapping maps refuse. Existing source spans
outside replacement lines are retained; additions append in sorted name order.
Comments on a replaced function's lines belong to its replaced span. Named
helpers, idiomatic Python expressions, imports and other existing module content
are not a sandbox. Syntax-level acceptance never permits executing decorators,
imports or any other code. Compilation, isolation and behavior checks require
the separate trusted receiver profile. No L2-style restriction is imposed on
ordinary Python's runtime semantics.

## Bounded exact schemas

All document fields listed here are required; unknown fields refuse. JSON is
UTF-8 without BOM/duplicate keys, at most 65,536 bytes, depth 128 and 32,768 value
occurrences. Integers are signed 64-bit; floats, nonfinite values, surrogates,
cycles and custom Python objects refuse. IDs match [A-Za-z0-9][A-Za-z0-9._-]{0,127}.
Digests are sha256: plus 64 lowercase hex digits. General text is 1..1,024 bytes;
explicit wider limits follow below. Canonical JSON has sorted keys, no whitespace,
literal UTF-8 and no trailing newline. Programmatic values receive the same
bounds before serialization. Returned aggregate documents also have these bounds.

A packet has exactly:

- schema: bagaev-model-task/1; packet_id: digest of all other packet fields.
- task, run, step: IDs; revision and attempt: positive integers.
- variant: python or l2. source: Python text or complete pinned L2 program value.
- profile: {model,reasoning,harness,history}. First three are observed/selected text
  labels; history is fresh, same_run or successor. This metadata does not attest
  provider internals or verify which model actually ran.
- base: {source,checkpoint,head}. source must equal the supplied source identity;
  checkpoint is nonnegative. head is null or {generation,source}; generation is
  nonnegative; source is null exactly when generation is zero, otherwise a digest.
  These are reported facts, not a live CAS.
- goal: {contract,text}. contract pins the receiver-selected public contract;
  text is at most 16,384 bytes. The library checks the digest spelling, not the
  adequacy of prose or its relationship to an external contract.
- references: up to 16 distinct {id,text}, each text at most 16,384 bytes; only
  explicit public context. No path or URL is followed.
- observations: up to 16 {source,checker,status,detail}; status is public_passed,
  public_failed or unknown; detail is at most 4,096 bytes. These are receiver-
  supplied public observations, not authenticated evidence or hidden diagnostics.
- continuation: the allowlist below.
- limits: {packet_bytes:65536,response_bytes:65536,proposals_left:1|2,wall_ms:N}.
  wall_ms is nonnegative. These communicate a run budget; the pure library does
  not enforce time, call count, tokens or source effects.

Inspection is included in the source/inventory and public context. Receiver
public checking follows a submitted proposal. This version has no interactive
tool-call protocol or unbounded context resolver.

A response has exactly schema (bagaev-model-response/1), packet_id, task,
revision, run, step, attempt, variant, base, status, add, replace, unresolved,
hypotheses. Every identity/base field exactly matches the packet, including scalar
types. Status proposed requires at least one named addition/replacement;
cannot_complete requires both maps empty. At most 16 changed definitions total;
add/replace names are disjoint. L2 values are full {params,body} definitions;
Python values are function-source strings. The two text lists each contain at
most 16 items of at most 1,024 bytes. No passed/accepted/permission field exists.
read_response checks the envelope/binding; propose additionally checks the edits.

Errors are ModelError with stable codes: MODEL_FORMAT (shape/value/text),
MODEL_BOUND (transport/structure), MODEL_BINDING (packet/source mismatch),
MODEL_SOURCE (Python syntax/inventory/entry), MODEL_EDIT (named edit),
MODEL_REPLAY (attempt conflict/duplicate ledger key), MODEL_COST (duplicate
expense attribution). L2 source/patch validation retains L2Error and its L2_*
codes. Unexpected host failures are not converted to success or language refusal.
Python AST parsing is not proof that CPython compilation/execution will succeed.

## Continuation without a hidden oracle

continuation_view takes only the following named arguments, with no Store input:

- next_question: text; unresolved: up to 16 text items.
- hypotheses: up to 16 {status:current|historical,text,sources:[digest,...]};
  at most 16 sources each. A current label is still a hypothesis.
- checkpoints: up to 16 {source,step,status}, where status is candidate,
  public_passed, public_failed or unknown.
- effects: up to 16 {id,status}, distinct IDs, status unknown/succeeded/failed.
- receipt: null or {operation,status,source}. Status committed requires a source
  digest; absent/unknown require null. This is an observed summary, not a new
  Store receipt or proof an external operation never happened.

The caller supplies only facts authorized for this participant. The function
rejects extra fields but cannot detect secrets inserted into allowed prose.
Never pass a Store export: its fixed policy includes case inputs and expected
outputs. Keep hidden acceptance and its diagnostics solely at the receiver;
public observations and exact variant-local source suffice for this handoff.
A successor gets no private predecessor transcript, hidden reasoning or another
branch's solution. Reference hashes alone do not resolve missing source.

[Store](store.md) keeps immutable source/change/continuation objects. Its policy
cannot change in place. For the workload below one final policy is fixed before
runs; intermediate versions remain candidates and head stays null. An unfinished
continuation can carry unresolved items and empty evidence. For final initial
admission use actual base {generation:0,source:null}, changes:[], target A2 and
fresh complete evidence. Retain the real patch-chain objects separately as
candidate lineage; do not invent intermediate admissions. Independent checks
also own obligations outside Store's value/error cases, such as nonmutation.
The receiver closes each transaction before any model call. Reopen/reconcile
an unknown admission by its same operation ID, using existing Store semantics.

## Compact transport example

[protocol-example.json](../examples/model/protocol-example.json) is unrelated to
the measurement workload: change a fixed response string. After independent
source review and execution authorization, this library-only example needs no
provider or private workspace:

~~~python
import json
from pathlib import Path
from src import bagaev_model as M

example = json.loads(Path("examples/model/protocol-example.json").read_text())
packet = M.make_packet(example["packet_fields"])
response = {**example["response_fields"],
            "packet_id": M.read_packet(packet)["packet_id"]}
candidate = M.propose(packet, M.canonical(response))
assert candidate["changed"] == ["evaluate"]
# candidate["source"] is still unexecuted text, not an admitted result.
~~~

For L2 use the same packet/response fields with variant l2 and definitions as
values instead of Python strings. The [seeds](../examples/model/seeds.json)
contain only unsolved calibration/control/queue starting programs for both
variants, never their solutions. The receiver fills exact profile, contract,
run/attempt/base and the current public context before dispatch.

## Queue-view/1 measurement workload

Input is exactly {revision,items}, revision integer 0..2, items 0..8 records in
arbitrary order. Records have required id, urgent, tags and optional due. IDs and
tags match [a-z][a-z0-9-]{0,7}; IDs are unique; urgent is Boolean; tags has 0..4
strings; present due is an integer 0..31 (Boolean/float are not integers).
Only this bounded valid input domain is claimed. Malformed ingress is outside
this workload, without narrowing any existing language/application contract.

Success is exactly {kind:"success",rows:[{id,tags},...],order:[id,...]}. Rows keep
input order, order contains every ID once, output containers are detached, and
input is unchanged. Each invocation returns a fresh tree: mutable containers are
not shared with input, a previous output, or another position in the same result.
Acceptance checks these identities as well as serialized values. Seed returns {kind:"unsupported"} for all selectors. Ak
supports selectors 0..k and returns exactly that unsupported record for higher
valid selectors. The successive model tasks are:

| Step | Added selector behavior; earlier selectors stay unchanged |
| --- | --- |
| Q0 CREATE | Selector 0 preserves tags including order/duplicates; missing due first, dated ascending due then ID, missing by ID; urgent ignored. |
| Q1 NORMALIZE | Selector 1 uses unique ascending tags; ordering as Q0. |
| Q2 PRIORITIZE | Selector 2 tags as Q1; urgent first, then within each group dated before missing, dates ascending then ID, missing by ID. |

Due=0 is dated. An urgent missing item precedes a non-urgent dated item because
urgency is the first key. An explicitly historical missing-first Q0 summary
cannot override Q2. This is new synthetic behavior, not the catalog answer patch.
The separate simple control sorts 0..4 valid identifier strings ascending and
retains duplicates, from an identity seed. Separate calibration returns the
integer length of such an array, counting duplicates, from a constant-zero seed;
one proposal per variant, outside main completion units.

U-long means all three checkpoints plus the designated fresh successor;
U-control means one accepted control change. Checkpoints are not extra accepted
units. The predecessor has up to two Q0 proposals then exactly one Q1 proposal.
After capture and public checking of that first Q1 proposal, a new participant
continues with the latest structurally valid candidate (or last valid source and
rejected attempt), public diagnostics, unresolved question and remaining budget:
at most one Q1 and two Q2 proposals. It receives only its variant's packet, with
fresh supplied history. Even an immediately successful Q1 still leaves Q2 to
the successor. Exhausted Q0/Q1 fails the unit; no human solution replaces it.

## Registration, attempts and costs

[registration.json](../examples/model/registration.json) fixes the selected design
and explicitly marks unfilled execution/profile/acceptance hashes. It is not an
activated run or a complete preregistration. Freeze those fields after bounded
calibration and before main responses. Independent literal acceptance cases,
mutation witnesses and public/hidden split are fixed before model proposals.
Hidden acceptance runs only after a unit/candidate choice is frozen, with no
feedback to later participants. Last structurally valid proposal is selected,
never hidden best-of-N. A refused wrong proposal is a counted failure; no failing
mandatory result may be labelled accepted.

Two paired repetitions of both units/variants mean eight main unit-runs. Order
B,C then C,B is predetermined. Two proposals per checkpoint/control give at most
32 main responses, plus two separate calibration responses. Same exact
model/reasoning, public information, named-edit facilities, public feedback,
source/version history and continuation apply to Python B and L2 C. B uses normal
Python constructs; C gets no ready domain operation. This is a bounded combined
core/representation comparison; no isolated syntax, training, channel, adoption
or broad language-necessity claim follows. A representation-specific claim needs
a separately controlled familiar-code-to-the-same-IR comparison.

No-tools/fresh-history rules on a native collaboration transport require observed
zero tool calls and supplied-context provenance; shared filesystem and hidden
provider state are not isolated by instructions. Deadlines request interruption,
not proof of stop; reconcile terminal handles and late output before continuing.
Hard provider token/memory limits are unavailable in this profile. Protocol
violations remain in denominators and costs; never silently substitute a model.

append_attempt stores at most 64 rows, each exactly schema, task, revision, run,
step, attempt, variant, packet, response, outcome. schema is bagaev-model-attempt/1;
packet is packet_id. response is null or {digest,bytes}, a capture-owner observation
of raw bytes (including oversized output). Outcome is received, rejected, timeout
or interrupted; only the latter two allow null response. The identity key is
task/revision/run/step/attempt/variant. Exact replay returns the same list;
conflicting content under the same key refuses. Late output after a recorded
terminal timeout is kept separately by the transport owner, never overwrites the
attempt. This in-memory API is not atomic durable accounting or authentication.
Uninvoked blocked steps are reported separately, not fabricated attempts.

A cost row has exactly {schema:"bagaev-model-cost/1",id,category,unit,amount,basis}.
category is preparation/attempts/maintenance/operation; unit and basis are IDs;
amount is nonnegative integer or null for unknown. Basis identifies the original
expense observation. Duplicate row IDs or the same basis/unit across categories
refuse. At most 256 rows; group only one variant/run scope per call. Use distinct
units such as usd_micros, input_tokens, output_tokens or cpu_ms; never sum tokens,
time and money together. Input/cached-input and output/reasoning-output are totals
and subsets, not additive categories. Peak memory is a separate observation, not
an additive cost. The caller owns truthful expense coverage and shared-cost
allocation; the library cannot detect invented IDs hiding a duplicate expense.

cost_totals produces category sums per observed unit. A missing category or any
unknown amount makes its sum null; missing units remain absent, never zero.
C_dev includes preparation plus attempts; C_full includes those same terms plus
maintenance and operation, without double-counting C_dev. Record an actual known
zero explicitly; absent measurements cannot be encoded as zero. For full
comparison include all setup, calibration, failed attempts, tool/check work,
review, recovery, maintenance and the fixed operational horizon. Subscription
allocation, historical preparation and unavailable provider metrics stay unknown.

The primary metric is full USD cost per accepted unit at the common finite
horizon: the four requested changes plus one invocation per frozen operational
case/checkpoint. Tokens/time/CPU/energy are descriptive separate dimensions.
Delta is 10% relative saving; completion epsilon is 0.10 absolute, with
conservative 95% rate intervals and paired differences reported descriptively.
Accepted correctness, source binding, privacy and authority are zero-tolerance
hard constraints. Proven hard failures take precedence; otherwise a positive
claim requires complete applicable cost and completion evidence. Missing costs
make cost/relative saving undefined; zero accepted units also makes per-accepted
cost undefined. No cost interval is calculated from incomplete inputs. A small
sample or missing full lifecycle expenses normally yields indeterminate, a valid
reported result that is not a positive claim. Observed task completion still
requires real authorized model changes, fresh continuation and independent checks.

## Measured M5 results

The finite M5 run completed 8/8 planned main units: two paired repetitions of
each Python and L2 queue/control unit. All eight accepted units used 16 native
main responses; two separate calibration responses are reported outside that
denominator. Four queue units included the preregistered fresh successor. The
selected product checks recorded 19 passes, zero failures, errors, or skips.
The comparator selected 522 observation rows: per queue/control unit, Python
contributes 81/6 rows and L2 162/12 because both its reference and backend are
checked. These rows are not tokens or useful-unit counts. Coordinator wall-clock
observations cover 3,133.439 seconds from registration freeze to main completion;
the eight unit intervals sum to 2,740.967 seconds. The remaining 392.472 seconds
fall outside those intervals. These are descriptive coordinator observations,
not independent runner measurements or a performance comparison.

The result record includes per-unit native usage, context-to-response wall time,
and joint checking-wrapper wall time. Usage takes the last cumulative counters
from each distinct participant session once; earlier turns are not added again.
Cached input and reasoning output are subsets of input and output respectively;
total tokens are input plus output, not an additional component. Response timing
runs from turn context to final assistant response, excluding earlier dispatch
and later terminal delivery. Runner timing includes guest work and checks before
outer supervision cleanup/delivery. These overlapping timing scopes must not be
added as independent costs. Coordinator/root counter overlap remains unknown.

Both variants accepted 2/2 queue units and 2/2 control units. Each of the four
variant-by-unit proportions has the preregistered exact Clopper-Pearson interval
[0.07905694, 1], using tail probability 0.05/8 for a 95% Bonferroni family. The
conservative L2-minus-Python completion bounds are [-0.92094306, 0.92094306] for
each task class and their equal-weight average. Both paired observed differences
are zero in each class. These bounds cannot establish the preregistered absolute
completion margin epsilon = 0.10. They are tiny-sample binomial references under
unverified provider/IID assumptions and support no broad completion-rate claim.

Preregistered shared M5 preparation, review, setup and coordination costs split
equally between variants, then equally across each variant's four planned units.
Calibration is preparation, outside the main useful-unit denominator. Specific
prompt, source-checking and continuation work is charged to its variant/unit;
failed attempts, checks, reviews and recovery remain in scope. Allocation rules
keep tokens, time and money separate and do not turn missing costs into zero.
No full USD lifecycle cost, provider billing, historical setup, energy, memory,
or separately attributable operation cost was observed. Therefore full cost per
accepted unit and relative saving are undefined, and the preregistered cost
decision is **indeterminate**. Post-batch reporting, review, and integration
expenses remain unknown. The observations support no broad efficiency, model,
or language claim. Zero observed tool calls were audited
under the no-tools instruction, but that instruction does not isolate a filesystem
or hidden provider state. Prompts were supplied as planned public context; opaque
native arguments do not attest plaintext byte equality.

The [sanitized result record](../examples/model/results.json) preserves the
preregistered limits, order, method, thresholds, execution-time source hashes,
and per-unit selected sources without private logs or identities. It is a bounded
observation, not final independent acceptance, a beta release, or evidence for
previously unrun full-suite/older-stage checks. The exact binomial-reference
method links were frozen in the registration: [NIST proportion confidence
intervals](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/propconf.htm)
and [NIST binomial intervals](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm).
