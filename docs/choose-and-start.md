# Compact language reference

One use reference; primary budgets: 32,768 UTF-8 bytes here, 4,096 in README.
These are byte limits, not measured tokens or a universal model context-fit claim.

## Choose a route from the task

| Task/source | Explicit choice | Important boundary |
| --- | --- | --- |
| New readable typed pure code | `record-form/5`, typed-record/11 | Main language below; immutable values, bounded first-order computation. |
| Existing owned-state component | `component-form/7`, component-source/2, typed-record/10 | Same basic expression style, a narrower vocabulary and explicit state contract; select its receiver separately. |
| Existing dynamic JSON/Store program | `bagaev-l2/1`, or explicit `/2` for `filter` | Different dynamic language and pins; see the complete operation summary below. |
| Small original dataflow example | `bagaev/l0-program/v1` | Ten operations; all nodes evaluate, including unreachable ones. |

Respect prescribed stacks and explicit versions. Production/mobile/GPU/distributed
support and cost advantage are unproven. Pure code needs no LLM and has no I/O,
clock, randomness, imports, callbacks, dynamic evaluation or mutation.

## Start with readable typed source

```bagaev
bagaev record-form/5;
program {
  record Item { amount: Int64 };
  list Items of Item capacity 16;
  entry total;
  fn total(items: Items) -> Int64 =
    fold (16, 0) with (i, sum) in
      if i < records.len(items)
      then sum + record.field(records.at(items, i), "amount")
      else sum;
}
```

Arguments `[[{"amount":3},{"amount":4}]]` specify result Int64 `7`. Arguments
are one array in parameter order. The 16-iteration loop guards actual length.

### Source grammar

UTF-8, no BOM: `bagaev record-form/5; program { declarations }`. Whitespace is
space/tab/CR/LF. After the header, `//` outside strings comments through LF/EOF.
No block comments, interpolation or comments inside/before the header. Comment
controls except tab/CR refuse. Comments are untrusted layout data, absent from IR.

Declarations end in semicolons; order may vary and forward references are allowed:

| Declaration | Meaning |
| --- | --- |
| `entry NAME;` | Exactly one selected function. |
| `fn f(a: T, b: U) -> V = expression;` | Explicit parameter/result types; 0..8 parameters. |
| `record R { field: T, other: U };` | Nominal immutable product; exact field set. |
| `variant V { A: T, B: U };` | Nominal closed sum; one payload per alternative. |
| `list L of R capacity N;` | Nominal list of a declared record type, capacity 0..16. |

Readable identifiers start with an ASCII letter, followed by letters, digits or
underscore. For accepted execution, function/parameter/local names are at most
64 bytes; type/field/alternative names at most 32. Reserved expression words are
`if then else true false let in match fold with list of capacity omit_none`.
Keep type names distinct from built-in types and other named types. Duplicate
fields/functions/types/parameters and unresolved references refuse. There are
no generics, methods, closures or overloaded user functions.

Expressions:

| Form | Rule |
| --- | --- |
| `0`, `-42`, `true`, `false`, `"text"` | Int64, Bool, Text literals. Negative sign is for an integer literal, not general unary negation. Text uses JSON quoting/escapes, with valid Unicode scalars. |
| `name` | Parameter or active lexical local; no global variable. |
| `(e)` | Grouping. |
| `a + b`, `a - b`, `a * b`, `a < b` | Int64 operators; `*` binds tighter than `+/-`, then one nonchained `<`. Arithmetic is left-associative and checked. |
| `let x = value in body` | Evaluate value once; bind inferred type only in body. Active-name shadowing refuses. |
| `if condition then yes else no` | Bool condition; same arm types; evaluate only selected arm. |
| `fold (N, initial) with (i, acc) in body` | Literal N in 0..1024. Evaluate initial once; i is Int64 0..N-1, acc is previous value; body must have initial's type. N=0 returns initial. Binders are distinct and fresh. |
| `f(a,b)` | Pure call; exact arity and declared types; arguments evaluate in parameter order. |
| `f(second:b, first:a)` | All named or all positional. Named labels must exactly match known parameters; evaluation follows declaration order, not textual label order. |
| `R { field:e, other:v }` | Supply every field once, including omitted-on-wire optional fields. Expressions evaluate in sorted field-name order, not textual order. |
| `r.field`, `record.field(e,"field")` | Declared field projection; the latter handles computed records. Key is literal metadata. No mutable assignment. |
| `V.A(value)` | Construct declared nominal alternative. |
| `match (value) { A(x): e; B(y): f; }` | Every alternative once, fresh arm binder, same result type; only chosen arm evaluates. |

Control expressions (`if`, `let`, `fold`, `match`) should be parenthesized when
used inside arithmetic/comparison operands. Use `bool.not(e)` for negation and
`int.eq`/`int.le` for equality/non-strict comparison; no `/`, `%`, `==`, `<=`,
assignment or general `while`. A function cannot see its caller's locals.
The entire call graph must be acyclic: self/mutual recursion is refused even
if unreachable. All branches and zero-iteration bodies still type-check.

### Values and argument/result JSON

| Type | Value and wire rules |
| --- | --- |
| `Int64` | Signed -2^63..2^63-1; exact integer token, no Bool/float coercion. Overflow is an error, never wraparound. |
| `Bool` | JSON true/false only. |
| `Text` | At most 1,024 UTF-8 bytes and 256 Unicode scalars. Empty/control/NUL/noncharacter values allowed via valid encoding. No normalization, locale or grapheme processing. |
| `OptionInt64` | None or Some(Int64); JSON null or integer. Some(0) differs from None. |
| `TextList` | Ordered, duplicate-preserving array of at most 64 Text values and 4,096 aggregate UTF-8 bytes. |
| Named record `R` | Exact JSON object fields and declared value types; nominal identity is not structural equality. |
| Named list `L` | JSON array of its exact record element type, at most declared capacity. |
| Named variant `V` | Exactly `{"case":"Alternative","value":payload}`. |
| `Json` | Bounded raw JSON view, including missing projections and arbitrary JSON number lexemes. May be a parameter/intermediate/helper result, but never the entry result or a record/variant payload. |

For a record field declared `date: OptionInt64 omit_none`, missing input means
None, explicit null refuses, and output omits None. A present zero survives.
A plain `date: OptionInt64` field is required and uses null for None. Constructors
always supply the field, e.g. `date: none.int()`; omission is a wire rule.
There is no general null type, optional Text, array literal or map type in form5.

Records/variants/lists may refer forward but their combined type graph is acyclic.
There are at most 8 named types total, 8 fields per record, and 1..8 alternatives
per variant. Each expanded type is at most 4,096 descriptor units: primitive=1,
TextList=65, record=1+sum(fields), variant=1+max(payloads), record-list=1+capacity
* element units. 

### All named intrinsic spellings

`I`, `B`, `T`, `O`, `TL`, `J`, `L`, `R` below mean Int64, Bool, Text,
OptionInt64, TextList, Json, a particular nominal record-list and its element.
Names select fixed operations.

| Call | Type/result and behavior |
| --- | --- |
| `int.eq(a,b)` | `(I,I)` or `(B,B)` -> B, exact equality; no container/Text equality. |
| `int.le(a,b)` | `(I,I)` -> B. |
| `bool.not(x)` | B -> B. |
| `bool.and(a,b)`, `bool.or(a,b)` | B,B -> B; exact lazy sugar for `if a then b else false` / `if a then true else b`. Both sides statically checked. |
| `text.eq(a,b)`, `text.lt(a,b)` | T,T -> B; exact equality / lexicographic Unicode-scalar order. |
| `text.bytes(t)`, `text.scalars(t)` | T -> I; byte length / scalar count. Neither counts model tokens. |
| `text.byte_at(t,i)` | T,I -> O; unsigned UTF-8 byte 0..255, None for negative/out-of-range index. |
| `none.int()` | -> O, absent. |
| `some.int(i)` | I -> O, present. |
| `option.is_some(o)` | O -> B. |
| `option.or(o,fallback)` | O,I -> I; evaluates fallback only for None. |
| `list.text(t,...)` | 0..64 T expressions -> TL, preserves order/duplicates. |
| `list.len(xs)` | TL -> I. |
| `list.at(xs,i)` | TL,I -> T; invalid index refuses. |
| `list.contains(xs,t)` | TL,T -> B, exact membership. |
| `list.increasing(xs)` | TL -> B, strictly ascending; duplicates fail, empty/singleton pass. |
| `list.unique(xs)` | TL -> TL, ascending sorted unique values, NOT stable-order deduplication. |
| `list.push(xs,t)` | TL,T -> new TL; old value unchanged, item/byte bounds apply. |
| `records.list(L,r,...)` | Literal declared type name and 0..capacity R expressions -> L. |
| `records.len(xs)` | L -> I. |
| `records.at(xs,i)` | L,I -> R; invalid index refuses. |
| `records.push(xs,r)` | L,R -> new L; exact nominal element type, capacity enforced. |
| `record.field(r,"field")` | Declared projection, described above; no reflection. |
| `json.kind(j)` | J -> T: `missing`, `null`, `bool`, `int`, `number`, `text`, `array`, `object`. Kind `text` alone does not establish valid bounded Text. |
| `json.len(j)` | J -> O: length for array/object, None otherwise. |
| `json.int(j)` | J -> O: exact Int64 integer token only. Fraction/exponent token, overflow or another kind -> None. |
| `json.is_text(j)` | J -> B: true only for valid bounded Text. |
| `json.field(j,"key")` | J -> J: field or missing, including for nonobjects. Literal scalar key <=64 UTF-8 bytes. |
| `json.at(j,i)` | J,I -> J: element or missing, including for nonarrays/invalid indices. |
| `json.text_or(j,fallback)` | J,T -> T: bounded Text projection or lazy fallback. |

Check Json kinds before constructing domain values. Missing, null and number
lexeme categories remain distinct; projection does not validate business rules.

### Evaluation, limits and failures

Strict operands evaluate left to right and stop at the first error. The exceptions
are conditional/match arms, the two lazy fallback operations and Boolean sugar.
Records use sorted field order; named calls use parameter order. Values are
immutable, results detached. Nominal types do not authenticate origin.

| Boundary | Limit |
| --- | --- |
| Readable source | 1,048,576 UTF-8 bytes; 32,768 semantic tokens; parser/reconstructed depth 128; 10,000 reconstructed values. |
| Checked profile11 program | 1..32 functions, at most 8 parameters each, 2,048 expression occurrences, expression depth 32; program JSON depth 128 and 8,192 values. |
| Full invocation | 1 MiB, JSON depth 132 and 16,384 values, exact entry arity, argument validation in parameter order. |
| Evaluation | 65,536 logical work units, fixed by the profile. This is not a CPU, memory or latency measurement. |
| File-tool output | 1 MiB unless a separately documented artifact format says otherwise; fresh file required. |

Codec success is not type checking. Check order: transport/envelope/bounds;
named type references/cycles/expansion; function structure/scopes; references/arity;
call cycles; ordered types; entry-result restriction; arguments. Static/argument
refusal has work 0.
Core refusal codes: `RR_JSON`, `RR_VERSION`, `RR_SHAPE`, `RR_BOUNDS`,
`RR_REFERENCE`, `RR_CYCLE`, `RR_TYPE`, `RR_ARGUMENT`. Diagnostics identify JSON
pointers; under an invocation, program pointers start `/program`.

Every entered expression first reserves one work unit. In addition, after its
operands succeed:

| Operation | Extra logical charge |
| --- | --- |
| Text literal | UTF-8 byte length. |
| Text equality/order | Sum of both byte lengths, even on early mismatch. |
| `list.contains` | n + b + n*q, where n=list length, b=aggregate bytes, q=search Text bytes. |
| `list.increasing` | n + 2*b. |
| `list.unique` | n*n + 2*n*b. |
| `list.push`, `records.push` | Result length n+1, before capacity/byte refusal. |
| `json.field` on object | Object field count * (key byte length+1); otherwise zero. |
| `json.int` on integer token | Token byte length, including sign; otherwise zero. |
| Successful `json.text_or` projection | Projected Text byte length. |

Other operations have no extra charge beyond entered expressions. A call's body,
loop iterations and selected branches count normally. Reserve extra charges
atomically: an insufficient remainder fails without consuming that reservation;
previous work remains. Untaken branches add no work. Optimizers must preserve
logical charges. Runtime errors return no partial value: `RR_OVERFLOW`, `RR_WORK`,
`RR_INDEX`, `RR_LIST_ITEMS`, `RR_LIST_BYTES`, `RR_RECORD_LIST_ITEMS`.

A full reference result has exactly `schema`, `status`, `reason`, `location`,
`value_type`, `value`, `work`, schema `bagaev-typed-record-result/11`. Success has
status `success`, null reason/location and the typed value. Invalid code uses
`invalid-ir`; runtime statuses are `integer-overflow`, `work-limit`, `list-index`,
`list-bound`, `record-list-bound`. Failure has null value/type. Record/list/variant
labels are `Record:NAME`, `RecordList:NAME`, `Variant:NAME`. Business refusals are
ordinary application-defined returned values, not these language errors.
Allocation, process, I/O and unavailable-service failures are environment failures.

### Program identity and source locations

Decoded form5 is exactly a JSON object with `schema`, `records`, `lists`,
`variants`, `entry`, `functions`; schema is `bagaev-typed-record/11`. Functions
have exactly `params` (ordered `[name,type]` pairs), `result`, `body`.
The canonical graph pin hashes compact UTF-8 JSON with sorted object keys,
unescaped non-ASCII, no insignificant whitespace and preserved array order.
Tool pins are 64 lowercase hex SHA-256; reference/map pins prefix `sha256:`.
Hash the program, not its observation envelope. Unused definitions count. Raw
source SHA-256 also binds layout/comments. Hashes authenticate neither author nor
correctness and grant no execution authority.

Source maps have half-open UTF-8 byte offsets and one-based Unicode-scalar
line/columns. LF starts a line; CR/tab count as one scalar, not display width.
Ranges are `exact-expression` or `enclosing-expression` (e.g. a literal generated
by Boolean sugar). Node IDs come from the checked inspector, never map row order.
Join checked nodes and maps only when program pins match, using JSON pointers.

## Finish one change

Use reviewed tools in an authorized environment. From the checkout, `-B`
suppresses bytecode writes, not sandboxing. Inputs are bounded regular nonsymlink
files, outputs exclusively new. Structured refusals exit 2; an OS failure can
leave a partial new file. These data tools do not launch an evaluator.

| Need | Command shape (`python3 -B tools/` prefix omitted) |
| --- | --- |
| Decode readable source | `record_text.py decode S --form 5 --output P` |
| Encode graph | `record_text.py encode P --form 5 [--named-calls] --output S` |
| Inspect identity | `record_text.py inspect S --form 5 --output INFO` |
| Prepare typed arguments | `record_text.py prepare S --form 5 --arguments A --output INV` |
| Prepare raw Json arguments | `record_json_prepare.py S --form 5 --arguments A --output INV` |
| Syntax context | `record_diagnose.py S --form 5 --output DIAG` |
| Token-preserving format | `record_format.py S --form 5 [--width 40..120] --output NEW` |
| Function fragment | `record_function.py extract S --form 5 --name F --output PART` |
| Focused context | `record_function.py context S --form 5 --name F [--locations|--source-body] --output CTX` |
| Pinned body replacement | `record_function.py replace S --form 5 --replacement PART --base BASE --function-pin OLD_FN [--callee-context] --output DRAFT` |
| Add helpers/change several bodies | `record_draft.py S CANDIDATE --form 5 --base BASE --target TARGET --output DRAFT` |
| Export one changed body | `record_export.py S --form 5 --draft DRAFT --base BASE --target TARGET [layout options below] --output NEW` |
| Pinned source map | `record_source_map.py S --form 5 --program-pin sha256:BASE [--source-sha256 RAW] [--pointer PTR] --output MAP` |
| Discovery | `record_capabilities.py --form 5 --revision 5` |

Typed preparation accepts strict Int64 JSON transport, so it refuses fractions
and out-of-range integers even inside Json. Raw Json preparation preserves number
lexemes and accepts only an all-Json or zero-parameter entry, with exact argument
count. It refuses duplicate keys, non-JSON numbers and isolated surrogates.
Both write invocation/11 data with `schema`, `program`, `arguments`, not a result.
The Rust reference entry is `examples/probes/backend/rust/record_wide_main.rs`;
a separately reviewed/built executable consumes `run --input INV`. A compiler,
result pin or this document never grants permission to execute untrusted code.

Graph encoding preserves meaning, not comments/layout; `--named-calls` is form5
encode-only. Token formatting retains comment text/order and existing named
spelling, normalizes whitespace and checks graph equality/idempotence. Optional
width is a soft Unicode-character goal: indivisible text/comments and punctuation
may exceed it. Defaults retain old bytes. Syntax `valid_form` is not type checking.

Focused context/2 includes a canonical selected-function fragment plus direct
caller/callee signatures and pins. `--locations` gives context/3 with original
full-source ranges. `--source-body` gives context/4, including exact original body
text, body hash and whole-source hash; it implies locations. Surrounding trivia
is excluded. Canonical fragment text and original-source coordinates differ.

Replacement changes one existing body only, preserving types, entry, signatures
and other functions; stale pins and no-op refuse. A standalone fragment requires
positional external calls because their declarations are absent. Explicit
`--callee-context` resolves named labels using only the base-pin-checked original
parameter declarations, without injecting other bodies. It is replace/form5-only.
Whole-source drafts may add helpers or change multiple bodies but cannot remove
old functions or change their signatures/type/entry declarations. Delta names
are sorted. Every draft is detached, `semantic_check:false`,
`execution_admission:false`; a structurally valid wrong answer is still possible.

The focused exporter reconstructs and validates the complete packet and target;
it refuses helper additions/multiple changed bodies. Default export is canonical.
`--preserve-layout --source-sha256 RAW` replaces only the exact original expression,
preserving every outside byte. Add `--replacement-source PART` to retain that
fragment's exact expression spelling/internal comments; add `--callee-context`
when it needs original callee declarations. All require explicit form5/layout
mode. Leading/trailing fragment trivia is excluded. Full output graph, target,
size and packet equality are rechecked. Existing outputs are never overwritten.

Freeze expected inputs/results before proposing a change. Review independently
selected source/target and delta, then check actual behavior/refusals. Blindly
trusting a candidate-announced target defeats pinning. Source acceptance, executed
conformance, independent review and measurement differ. [Batch example](inventory-batch-change.md).

Prepared APIs reuse checked source. Load [native ABI/ownership](prepared-json11-native.md)
only for native hosting: exact-kernel admission and buffer safety are separate
from language/source acceptance; wire consistency is not origin authentication.

## Existing stateful component programs

The readable `component-form/7` envelope is explicit:

```component
bagaev component-form/7;
component StockItem operation set_quantity {
  record Key { code: Text };
  record Revision { value: Int64 };
  record Stock { key: Key, quantity: Int64 };
  record Request { key: Key, base: Revision, quantity: Int64 };
  record Error { reason: Text };
  variant Outcome { Decline: Error, Propose: Stock };
  state Stock identity key;
  request Request identity key revision base: Revision;
  replace quantity;
  outcome Outcome error Error;
  entry apply;
  fn apply(state: Stock, request: Request) -> Outcome =
    if request.quantity < 0
    then Outcome.Decline(Error { reason: "negative" })
    else Outcome.Propose(Stock { key: state.key, quantity: request.quantity });
}
```

Component-source/2 embeds typed-record/10. Form7 supports literals, grouping,
`+ - * <`, let/if/fold/match, positional calls, records, variants and the Text/
TextList/record-list operations above, with record-list capacity 0..4. It lacks
form5 named calls, comments, omission/Json syntax, Boolean sugar and new tool flags.
Use `component_text.py decode|encode ... --form 7`; older versions stay separate.

The five clauses state/request/replace/outcome/entry occur exactly once. Entry is
exactly `(State, Request) -> Outcome`, with exact alternatives Propose:State and
Decline:ErrorRecord. State/request identity fields have the same nominal record
type; request revision has the named record type exactly `{value:Int64}`.
Replace fields are sorted, unique, nonempty, at most eight, direct state fields
excluding identity. Every other state field must be preserved.

Owned state/request/revision/error closure permits required primitive fields and
acyclic records, including TextList; it refuses Json, optional omission, record
lists and nested variants. Record lists may still occur inside pure helpers.
The independent component policy fixes names, complete reachable types, bindings
and allowed fields; matching names alone is insufficient and metadata grants no
rights. Actual typed checking precedes component/policy compatibility checks.

Propose is not Applied. The selected owner validates result, preserved fields
and current conditions before state replacement, revision increment and Applied.
Equal-state proposals still advance revision. Decline records typed error without
state/revision change. Exact-intent replay requires current observation permission;
changed source/request/deadline conflicts. Lost reply remains unknown. Work/type/
service failure is not a business decline. Cancellation request, confirmed stop
and compensation differ. Load [receiver/persistence](stateful-components.md) for
hosted effects/recovery; codecs provide neither durability nor rights. L2 Store
is separate.

## Existing dynamic L2 programs

L2/1 is dynamic pure JSON; L2/2 adds filter with distinct identities, no automatic
upgrade. A source has exactly `schema`, `entry`, `definitions`, `pins`. Schema is
`bagaev-l2/1` or `/2`. Each definition has `params` (0..8 distinct names) and `body`;
entry has exactly one parameter. Names match `[A-Za-z][A-Za-z0-9._-]{0,63}`.
There are 1..64 definitions; all calls resolve with exact arity and the entire
call graph is acyclic. Only parameters and lexical bindings are visible.

L2 tags are null/bool/int/float/string/array/object, without coercion. Borrowed
input is finite acyclic JSON, string keys, arbitrary integers and finite floats;
no concurrent mutation. Shallow predicates do not deep-validate rejected data.
Output is a fresh bounded tree without floats/surrogates. CLI transport is narrower.

Expressions are null/bool/Int64/string literals or arrays below; variables use
`var`. No bare-object/float expressions. Names/keys/bounds/ranges are metadata.

| Expression array | Meaning |
| --- | --- |
| `["literal",value]` | Bounded JSON constant without floats; contained arrays are data. |
| `["var",name]` | Lexical reference. |
| `["call",name,arg,...]` | Left-to-right arguments to pinned definition. |
| `["let",[[name,e],...],body]` | 1..32 sequential fresh bindings, later ones see earlier ones, not themselves. |
| `["if",c,yes,no]` | Bool condition; one lazy arm. |
| `["and",e,...]`, `["or",e,...]`, `["not",e]` | Bool only; and/or have 1..32 operands and short-circuit left to right. |
| `["object",{key:e,...}]` | Up to 32 fields evaluated in sorted Unicode-key order. |
| `["set",object,{key:e,...}]` | Shallow new record, replacing/adding fields; input/result at most 32 fields. |
| `["array",e,...]` | Left-to-right array, at most 256 items. |
| `["get",object,key]` | Object field; absent key -> L2_FIELD; no child traversal. |
| `["has",value,key]` | Total shallow object/key predicate. |
| `["null",value]` | Total null predicate. |
| `["shape",value,required,optional]` | Total shallow exact-key predicate; disjoint distinct key arrays, at most 32 total. |
| `["int.range",value,lo,hi]` | Total int-tag/range predicate; literal Int64 endpoints, lo<=hi. |
| `["text",value,lo,hi,first,rest]` | Total string grammar predicate; 0<=lo<=hi<=4096, first/rest nonempty lists of at most 16 disjoint ascending ASCII intervals in 0..127. Checks length before characters; empty passes iff lo=0. |
| `["array.bound",value,max]` | Total shallow array/length predicate, literal max 0..256. |
| `["eq",a,b]` | Exact same-tag scalar equality; false for either container. |
| `["lt",a,b]` | Same-tag Int64 or bounded scalar strings; ascending numeric/Unicode order. |
| `["length",array]` | Array length, at most 256. |
| `["map",array,name,body]` | Fresh binder; one body per item, input order. |
| `["all",array,name,body]`, `["any",array,name,body]` | Bool body, short circuit; empty gives true/false. |
| `["filter",array,name,predicate]` | L2/2 only: Bool predicate, stable selection, preserves order/duplicates. |
| `["unique",array]` | Bounded strings, FIRST-occurrence deduplication (different from typed list.unique). |
| `["sort",array]` | Bounded strings, ascending order, duplicates retained. |
| `["increasing",array]` | Strictly increasing bounded strings. |
| `["sort.by",array,name,key]` | Compute each key once in input order, stable lexicographic sort. Keys have 1..8 columns with same per-column int/string types and lengths. Empty input needs no key type. |

Traversal arrays have at most 256 items and fresh binders. All ordinary operands
are evaluated before primitive validation; lazy forms are exceptions. Every
branch must have valid syntax/references, but unreached type errors do not run.
Reached bounded strings require Unicode scalars and <=4,096 UTF-8 bytes. For lt,
check both tags, both Unicode-validity checks, then both byte bounds, left to right.
For unique/sort/increasing, check outer array/length, all element tags, all Unicode
validity, then all byte bounds. For sort.by, fully validate each key before the
next: array/length, all column tags/types, Unicode validity, then scalar bounds.
Shallow predicates/eq do not reject large or malformed nested values; text returns
false for a surrogate rather than treating it as a valid bounded string.

Program/patch text: 1 MiB, no BOM/duplicate keys, JSON depth 128; expression depth
64 and 8,192 occurrences. Literal/export data: depth 64, 65,536 values, object
width 32, arrays 256, strings/keys 4,096 UTF-8 bytes, Int64, no floats, canonical
size <=1 MiB. Runtime call depth <=64. Each entered expression costs one of
100,000 steps; unique/sort/increasing/sort.by additionally reserve n*n after
operand validation, before traversal/key evaluation. First overrun fails without
partial output. Input is not subject to export bounds until actually exported.

Checking order: L2_JSON transport, L2_PROGRAM structure, L2_REFERENCE names/arity,
L2_CYCLE, L2_PIN. Structural bounds use L2_BOUNDS before further descent. Definitions
are visited in sorted ID order; parameters before body and expressions in operand
order, including lazy arms. Runtime wrong type is L2_TYPE, missing field L2_FIELD,
reached size/step/call/export limits L2_BOUNDS. Codes are stable; English diagnostic
text is not normative. Environment exceptions never become a successful value.

Let C be canonical UTF-8 JSON (sorted keys, compact, non-ASCII unescaped, scalar
Unicode, minimal integers, normal JSON control escapes, no normalization), and
H=`sha256:`+SHA256(C). A definition pin is H of
`{"schema":"bagaev-l2-definition/N","definition":D,"dependencies":{callee:pin,...}}`,
for exactly its distinct direct calls, recursively. The source pin is H of the
complete checked source. A callee change updates callers' pins even with unchanged
bodies. No ambient latest-name lookup. A checked snapshot owns immutable data.

Patch exactly: `{"schema":"bagaev-l2-patch/N","base":H,"target":H,"add":{},"replace":{}}`.
Maps have disjoint names and a nonempty union. Add IDs must be absent, replace IDs
present. No deletion or in-place/store mutation. Build/check the entire candidate,
recompute all pins and verify target atomically; original unchanged on failure.
L2 existing signatures may change if the whole candidate remains valid, unlike
typed-record drafts. Stale base is L2_STALE; bad patch L2_PATCH; target mismatch
L2_TARGET. A patch is not execution or storage admission.

For new L2/2 code, `prepare` accepts exactly schema `bagaev-l2-draft/2`, entry and
definitions, without pins, validates and derives them. A small complete draft is:

```l2-draft
{"schema":"bagaev-l2-draft/2","entry":"main","definitions":{"main":{"params":["items"],"body":["filter",["var","items"],"item",["get",["var","item"],"open"]]}}}
```

For `[{"open":true,"id":"a"},{"open":false,"id":"b"}]`, the specified result is
`[{"open":true,"id":"a"}]`; missing/non-Bool open fails, it is not silently false.
Under an authorized profile, `python3 -B -m src.bagaev_filter prepare DRAFT --output P`,
then `check P` or `run P --input INPUT`. L2/1 uses `src.bagaev`; both support check,
run, patch, compile, inspect and diff, with separate schemas. Compilation produces
a source/generator/hash-bound CPython artifact and grants no execution authority.
CLI JSON input: 1 MiB, depth 128, 65,536 values, finite floats, integer tokens at
most 4,096 digits. Outputs are fresh. Saved revisions/admission/replay use the
separate [Store/1](store.md) or explicit [filter saved workflow](filter-saved-workflow.md),
not pure evaluation and not the typed component receiver.

## Original L0 compatibility

A source is exactly `{"schema":"bagaev/l0-program/v1","nodes":[...],"result":{"ref":ID}}`.
It has 1..256 nodes with unique IDs matching `[A-Za-z][A-Za-z0-9._-]{0,63}`.
Each node has id/op and only the listed fields; a reference is exactly `{"ref":ID}`.
Types are int (Int64), bool, string (<=4,096 UTF-8 bytes), string_list (<=256 strings).
Input names are unique IDs. JSON text is bounded to 1 MiB, no duplicate keys.

| op | Fields after id/op | Meaning |
| --- | --- | --- |
| input | name,type | Exact named supplied input. |
| literal | type,value | Typed constant. |
| identity | value ref | Return referenced value. |
| list.concat | items:1..32 refs | Concatenate string lists, enforce result bound. |
| list.unique | value ref | First-occurrence deduplication. |
| list.sort | value ref | Ascending Unicode order, duplicates retained. |
| list.length | value ref | Int64 length. |
| int.add | left,right refs | Checked sum. |
| int.equal | left,right refs | Bool equality. |
| bool.not | value ref | Boolean negation. |

Check every node's exact fields, references, types and acyclic graph, then exact
input keys/types/bounds. Eager evaluation visits EVERY node once in topological
order, even if not reachable from result; any failure rejects without partial
output. Node order is not semantic. Hash canonical compact sorted-key UTF-8 JSON
after sorting nodes by ID, prefixed `sha256:`. Other array order is preserved.
Patch exactly schema `bagaev/l0-patch/v1`, base, add array and replace array; IDs
occur once across both, add new IDs, replace existing complete definitions, retain
result. Validate private complete candidate and return only on success. Stale base
or invalid graph leaves original unchanged. The L1 CPython backend adds no language
syntax. `src/bagaev_l0.py check P`, `run P INPUT`, `patch P PATCH` print structured
observations; extract the returned program field before using it as a source.

## Decide what to try next

For pure authoring, this guide replaces loading the research/history catalog.
Host ABI, persistence and recovery need only their selected contract. Proposed
syntax is not accepted code; unknown versions refuse, and changing a header is
not migration. Record forms 1..4 select profile10/capacity4 with progressively
added option/omission/Json syntax; form5 selects profile11. Maintain old artifacts
against their own pinned contracts.

Semantic authorities for disputed edges: [typed core](probe-record-source.md),
[profile11](record-wide-profile.md), [Text](probe-text-values.md),
[components](probe-component-outcomes.md), [L2](l2.md), [L0](l0.md).
Size/operator/example tests do not prove prose completeness or model understanding.
No runtime semantics changed here.
