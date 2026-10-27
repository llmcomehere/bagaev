# R23 FFI metadata: closed shape and declared local links

This directory defines a finite metadata encoding for six proposed FFI
contracts. Validation checks object shape and consistency of declared links
inside one synthetic capsule. It does not implement a native ABI, wire codec,
broker, runtime authority gate, callback scheduler, recursive WireData
admission, or platform isolation.

Every generated capsule explicitly declares synthetic_shape_and_local_links_only
and synthetic_refs=true. Its ExactRef values are fabricated identifiers:
referenced artifact preimages are absent, and their byte_length and SHA-shaped
fields do not describe the enclosed JSON declarations. Actual source-file
hashes in the report are computed separately from real file bytes.

Metadata JSON is distinct from the number-free canonical transport body in
WIRE-FFI-0.1. Metadata uses exact JSON integers for bounded counts and UInt64
identities. No JSON-to-wire encoder is supplied here.

## The six local kinds

| Kind | Required declaration | Local relationships checked |
|---|---|---|
| AdapterManifest | Stable adapter ID, raw interface, worker image/closure/shim refs, static admission, type/codec/limits refs, exported contracts, broker allowlist, limits, origins | Exported adapter/interface identities; codec/registry/limit agreement; operation allowlists and declared capacities |
| FunctionContract | Ordered slots, mandatory HostCall, broker/cleanup/callback effect bounds, resource selectors, current-check policy, lifecycle, ordinary Err policy, fault declarations, origins | Resource/signature association, compatible modes/selectors, declared callback effects within the enclosing bound |
| ResourceTypeContract | Raw resource declaration, allowed modes, exact operation refs and roles, close policy, generation/release/GC policy | One exported contract per raw declaration; unique operation IDs/refs; compatible modes; own close-operation selection |
| CallbackContract | Raw signature, ordered non-callback parameters/outputs, effect bound, scoped lifetime, scheduling/stop policy, limits | Signature and resource association, codec agreement, enclosing effect bound and declared capacities |
| PlatformAdmission | Exact factory/broker/policy/evidence refs, target declaration, required properties, physical capacity declaration | Manifest target and declared ingress-capacity consistency; no actual platform test inferred |
| CallBinding | Source/node/execution/occurrence, session/call IDs, existing manifest/function/admission, prepared-input ref, exact slot vectors, preallocated resource/callback IDs | Exported function, ordered slot match, origin membership, session/mode/parent bindings, alias multiplicity and unique lease IDs |

All defined data objects have additionalProperties=false and all listed
properties are required. Ordered slot arrays preserve order. Effect/reference
sets use explicit uniqueness constraints. Names are bounded ASCII identifiers,
not host paths or authority grants.

There is no local WireTypeRegistry kind. WireType, WireTypeRegistry, and
CodecContract are typed external references. The mandatory declaration
external_ground_WireData_check_required identifies work still required.
Validation does not inspect type preimages, expand generic fields, prove
recursive type properties, or decide WireData/Key admission.

## Exact reference domain and construction DAG

Every ExactRef has exactly four fields: kind, schema_revision, byte_length,
sha256. Each reference position fixes its kind. Only schema revision "1" is
supported. Byte length is 1 through 4,294,967,295; sha256 is exactly 64 lowercase
hex digits. Local resolution compares all four fields. A matching name,
digest prefix, or digest with a different declared length does not resolve.
These checks apply solely to the synthetic catalogue.

The external catalogue has eighteen closed reference kinds:
InterfaceDeclaration, ResourceDeclaration, CallbackSignature, WireType,
WireTypeRegistry, CodecContract, LimitsContract, OperationContract,
WorkerImage, DependencyClosure, NativeShim, SandboxFactory,
BrokerImplementation, PlatformPolicy, PlatformEvidence, SourceOrigin,
PreparedInputVector, and OperationIntent.

Raw interface/resource/signature/type/operation declarations precede completed
function/resource/callback contracts. Function slots point to raw
ResourceDeclaration and CallbackSignature, never to a future manifest or to a
completed contract that might refer back to the function. The manifest lists
completed contracts and already formed image closure.

Static PlatformAdmission has no manifest, worker-image, or future LaunchReceipt
hash. A current supervisor launch receipt remains a separate runtime
obligation. CallBinding refers to existing manifest/function artifacts and a
raw PreparedInputVector; it cannot refer to future INVOKE, REPLY, release, or
settlement bytes. A real mutable broker ledger would bind preallocated IDs
afterward; this metadata constructor implements no ledger.

Local validation rejects duplicate identities, reference/document
kind-revision mismatch, unresolved references, unreachable local objects,
unused external entries, and cycles. This DAG check concerns metadata links,
not recursive language types.

## Modes, lifetimes, publication, and current checks

DATA input slots declare copied snapshots. DATA outputs declare atomic
publication of new immutable values. There is no mutable VM memory, host
pointer, or implicit inout slot.

RESOURCE inputs use OWN, BORROW_SHARED, or BORROW_EXCLUSIVE. OWN requires
call_until_return_or_consume; borrows require until_verified_quiescence.
RESOURCE outputs in this metadata profile require OWN,
caller_owned_until_explicit_close, and new_token_after_prior_owner_quiescence.
Accepting these declarations does not establish actual ownership or quiescence.

Resource contracts include OWN among allowed modes. Mutate operations cannot
allow shared borrow. Close permits OWN and requires no active/reserved leases.
Unknown close outcome retains an obligation; generation exhaustion retires
without wrap. GC creates a broker cleanup obligation. Quiescence explicitly
does not prove effect absence.

Each resource may declare up to 32 operations in this capsule/tool profile.
Several operations may have the same read, mutate, or close role; operation IDs
and exact operation identities must be unique. The close policy selects its
own declared close operation. This limit is a tool capacity, not a claim that
the full language permits only 32 resource operations.

CALLBACK inputs declare a parent-call scoped token. Callback outputs and
callback-valued callback parameters are outside this metadata profile.
Capture release requires completed children and producer quiescence.
Child stop terminates the parent; fault delivery declares supervisor
maintenance work without new business effects or budget reset. No scheduler
or control plane is executed by this validator.

The exact current-check policy requires:

- Current dispatch authority under a serialized gate.
- Actual resource, lease mode, and current authority at each broker request.
- Caller/current/bound/parent intersection at callback admission.
- Current read authority before receipt disclosure.
- Denial of new effects when current authority is unavailable.

No field claims that these checks have actually succeeded. Effect comparisons
are between declarations and do not inspect native effects or callback code.

## Exact types and concrete bounds

The capsule permits 4–64 local objects and 1–128 external entries. A manifest
exports 1–32 functions, 0–32 resources, and 0–32 callbacks. Slot vectors have
at most 256 entries. Per-call resource and callback binding lists have at most
256 and 64 entries. Source-origin lists contain 1–8 entries.

Unsigned identities range from zero through 18,446,744,073,709,551,615.
Generations and session epochs require at least one. Tokens and call/execution
IDs have exactly 32 lowercase hex digits and cannot be all zero. They are
synthetic values, not authenticated registry tokens.

The exact-builtin preflight accepts dict/list/str/int/bool/null, with no
subclasses or floats. Thus true is not an integer field and 1.0 is outside the
profile. It rejects surrogate code points, strings over 8,192 code points,
dicts over 256 entries, arrays over 512 entries, depth over 32, and more than
100,000 value occurrences. Root depth is zero; keys are checked but do not
count as value occurrences. Schema-specific bounds are tighter. The integer
type checker independently requires exact Python int.

All the following limit fields are mandatory. These maxima are declarations,
not claims of available resources:

| Limit | Maximum |
|---|---:|
| Frame body bytes | 16,777,216 |
| Wire DATA bytes | 8,388,608 |
| String/Bytes bytes | 4,194,304 |
| Collection entries; type nodes | 65,536 each |
| Total value nodes | 262,144 |
| Arena units per component | 67,108,864 |
| Concurrent per-call arena units | 134,217,728 |
| Codec stack depth | 1,024 |
| Slots; resources per call | 256 each |
| Callbacks per call | 64 |
| Session calls | 4,096 |
| Pending ingress frames | 1,024 |
| Callback depth | 32 |
| Callback invocations; queue | 1,024 each |

Positive scalar/collection limits start at one and arena limits at 32.
Resource/callback capacities and callback depth/invocation/queue declarations
may start at zero, subject to local checks against exported contracts and
declared slots. Checks compare string <= wire <= frame, component arena <=
per-call arena, frame <= declared ingress, and slot/callback counts <= declared
limits. They do not prove that an unknown typed payload fits the capacity.

Platform capacity separately bounds memory (1–2^40 bytes), CPU time
(1–86,400,000 ms), threads (1–256), processes (1–64), descriptors (3–4,096),
and ingress (1–16,777,216 bytes). Semantic arena units are never equated to RSS.

## Validation order and result categories

The order is exact-builtin preflight (JSON_DOMAIN), closed Draft 2020-12
schema validation (SCHEMA), then local checks. Pinned dependencies are copied
from R22 into
schema-validation-requirements.txt.
Schema references are local; validation performs no network lookup.

Local stages check catalogue identity/resolution, reachability/DAG, exported
adapter/interface/operation declarations, slots and codec/effect bounds,
selectors, CallBinding identity/signature/origin, resource binding and aliases,
callback bindings, and capacity consistency. The first failing stage returns
its stable category and a local path.

The complete local error vocabulary is DUPLICATE_IDENTITY, ENTRY_IDENTITY,
REF_UNRESOLVED, REFERENCE_CYCLE, UNREACHABLE_OBJECT, UNUSED_EXTERNAL_REF,
PLATFORM_DECLARATION, ADAPTER_IDENTITY, DUPLICATE_DECLARATION,
OPERATION_DECLARATION, DUPLICATE_FUNCTION_ID, SLOT_NAME_DUPLICATE,
CODEC_DECLARATION, SLOT_DECLARATION, SLOT_MODE, OPERATION_NOT_EXPORTED,
LIMITS_DECLARATION, CLEANUP_DECLARATION, CALLBACK_BOUND, CALLBACK_EFFECT_BOUND,
SELECTOR_MISMATCH, BINDING_FUNCTION_NOT_EXPORTED, BINDING_IDENTITY,
BINDING_ORIGIN, BINDING_SIGNATURE, RESOURCE_BINDING, LEASE_DUPLICATE,
RESOURCE_ALIAS, CALLBACK_BINDING, and LIMITS_LOCAL.

Success returns accepted=true and code="OK", meaning only that this capsule
passed these shape and declared local-link checks. The seven function
boundary-fault names are a closed metadata-profile subset; this schema does
not replace the full diagnostic registry or claim every runtime failure.

## Finite metadata checks

The R23 experiment is outside this source package. Shape and local-link validation alone cannot establish native ABI behavior, runtime safety or full conformance. The architectural contract remains a design for a separate implementation.

Примечание к составу: экспериментальные пакеты R16–R23 не включены; упоминания их проверок описывают границы метода, а не результаты запуска этого пакета.
