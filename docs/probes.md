# Experimental probe contracts

This specification freezes three distinct interfaces: `bagaev-probe-ir/1`
(typed native kernels), `probe-forms/1` (representations of actual
`bagaev-l2/1`), and `probe-context/1` (portable decision context). Their
declarative manifests are [kernel](../examples/probes/kernel-contract.json),
[forms](../examples/probes/form-contract.json), and
[context](../examples/probes/context-contract.json). These interfaces define
behavior for future independent oracle and implementation work. They supply
neither expected fixture results nor execution, installation, model invocation,
admission, performance evidence, or a production infrastructure choice.
The existing [L2 specification](l2.md), L0/L1, catalog application and frozen
P0 remain separate. There is no arithmetic or static type extension to L2.

## Shared encoding and observation

`C(x)` is the canonical JSON encoding defined in L2: UTF-8 without BOM,
Unicode scalar strings, keys sorted by Unicode code point, preserved array
order, minimal decimal integers, lowercase true/false/null, no whitespace or
Unicode normalization, unescaped non-ASCII and slash, JSON escapes for quote,
backslash and controls (`\b`, `\t`, `\n`, `\f`, `\r`, otherwise lowercase
`\u00xx`). `H(x)` is `sha256:` plus lowercase SHA-256 of `C(x)`.
`B(bytes)` is the same prefix plus SHA-256 of the exact bytes, without JSON
quoting. Digests match `sha256:[0-9a-f]{64}`. No digest supplies authority.
`ID` matches `[A-Za-z][A-Za-z0-9._-]{0,63}`. IDs are case sensitive ASCII;
there is no implicit normalization, lookup of a latest version, or ambient
registry. A symbol occurrence is a JSON string, never a bare JSON token.

Every frame is one complete UTF-8 document; trailing JSON whitespace is
allowed on input, but a second value, BOM, duplicate object key, malformed UTF-8
or invalid JSON is refused. Whitespace counts toward source bytes. No prefix
of an oversize or interrupted frame is processed. JSON object/array/scalar
depth starts at one; each value occurrence counts separately, object keys
do not count as values. For new JSON interfaces there are no floats, NaN,
Infinity, or isolated surrogate strings. The L2-specific exception for parsing
program errors and fixture argument descriptors is stated below.

Locations for new contracts are JSON Pointers, constructed by escaping `~`
as `~0` and `/` as `~1` in each object key; array indices are minimal decimal.
The root pointer is the empty string. Locations are data paths, never host
paths. A malformed transport always has the root location; no parser-specific
byte offset or diagnostic wording is normative. Unknown object fields refuse
at that object, as do missing fields and wrong container shapes. Within a
phase, fields follow the specified order, map keys follow sorted ID/key order,
arrays follow index order, and a bound is checked before descent. Later phases
cannot supersede an earlier failure. Diagnostics may be short English text
outside the conformance record; host exceptions, allocation failures, crashes
and transport timeouts are environment failures, not successful observations.

## Typed kernel grammar

A program has exactly `schema`, `entry`, `functions`. Schema is
`bagaev-probe-ir/1`; entry is an ID; functions is a map of 1..8 IDs to definitions.
A definition has exactly `params`, `result`, `body`. Params is an ordered array
of 0..8 pairs `[ID, Type]` with distinct names. Type is exactly `Int64` or `Bool`.
Result is a Type and body is an expression. The entry can have 0..8 parameters.
Functions, parameters and lexical names use ID. Every function is checked,
including unreachable functions. The complete call graph is acyclic.

All expressions are arrays of the following exact forms. `E` means expression,
`n` means a JSON integer with a disjoint integer tag (never bool or float),
and `b` means a Boolean. Metadata does not count as an expression.

| Form | Type and meaning |
| --- | --- |
| `["int", n]` | Int64 literal, -9223372036854775808..9223372036854775807. |
| `["bool", b]` | Bool literal. |
| `["arg", ID]` | Current function's parameter, with its declared type. |
| `["use", ID]` | Lexical let or loop binding; parameters use `arg`. |
| `["add", E, E]`, `["sub", E, E]`, `["mul", E, E]` | Int64 operands/result; mathematical result checked for Int64 overflow. |
| `["eq", E, E]` | Same scalar type on both sides; Bool result. |
| `["lt", E, E]`, `["le", E, E]` | Int64 operands; Bool result. |
| `["not", E]` | Bool operand/result. |
| `["let", ID, Type, E, E]` | Value must have Type; bind it only in the body, whose type is the expression's type. |
| `["if", E, E, E]` | Bool condition; equal branch types; evaluate only the selected branch. |
| `["call", ID, E, ...]` | Exact target arity/types; result is its declared result type. |
| `["loop", n, ID, ID, Type, E, E]` | Literal count 0..1024; index then accumulator name, accumulator Type, initial value, body. Initial/body must have Type; result has Type. |

No other forms or implicit coercions exist. Names cannot shadow any active
parameter or lexical name. Loop index and accumulator names are distinct and
fresh. Loop initial value sees the outer scope only; body sees the outer scope
plus index:Int64 and accumulator:Type. An `arg` reference cannot resolve a
lexical binding and `use` cannot resolve a parameter. A callee sees only its
own parameters and lexical bindings, never the caller's scope. Literal values,
name/type/count metadata and signatures are not evaluated nodes.

Kernel source has at most 1048576 transport bytes, JSON depth 128 and 8192
JSON value occurrences. Across all bodies it has at most 512 syntactic
expression occurrences and expression depth at most 32 (body root depth 1).
Repeated syntax counts separately. Count/depth checks use preorder, functions
sorted by ID, children in evaluation order; both conditional arms are visited
statically. A loop's children are initial then body. Let children are value
then body. Call's children are its arguments. There is no heap language value,
recursion, string, float, pointer, division, import, effect or callback.
Compiler/runtime bookkeeping storage does not add a language heap feature.

### Static refusal order

Complete these phases before code generation or evaluation:

1. Transport byte bound (`IR_BOUNDS`), then text grammar/UTF-8/duplicate keys
   (`IR_JSON`); malformed transport has root location. Decimal tokens with a
   fraction/exponent are JSON numbers but fail the integer-only grammar later.
2. Envelope shape (`IR_SHAPE`), field order schema, entry, functions. A missing
   or non-string schema is `IR_SHAPE`; any other string schema is `IR_VERSION`
   at `/schema`. Then JSON depth/occurrence bounds (`IR_BOUNDS`) in preorder
   with sorted object keys. Then full structural checking: entry ID, function
   count/IDs, definition fields params/result/body, params in index order,
   result type, and body preorder. Bad ID/type spelling, duplicate parameter or
   binder, shadowing, unknown op, wrong arity/tag/metadata are `IR_SHAPE`.
   Integer literal/count/node/depth bounds are `IR_BOUNDS`. An out-of-range
   count or int literal reports its metadata element. Node/depth overrun
   reports the expression which would exceed the bound. Surrogate strings
   are `IR_SHAPE` at that value, or at the containing object for a bad key.
   Structural checking
   completes before resolving any name.
3. `IR_REFERENCE`: entry exists first; then body preorder by sorted function
   ID resolves `arg`, `use`, call target and call arity. Bad entry reports
   `/entry`; a missing reference or wrong call arity reports its expression.
4. `IR_CYCLE`: sorted-ID depth-first traversal of direct calls, callees sorted
   by ID. The first edge to a grey function refuses at that call expression;
   repeated calls to that callee use the first body-preorder occurrence.
5. `IR_TYPE`: bodies by sorted function ID; infer a child recursively, then
   immediately check its required type before visiting the next child. For
   add/sub/mul/lt/le check left then right as Int64; not checks Bool; call
   checks each argument against the corresponding signature. Eq infers left
   then right, requiring right's type to equal left's. If checks condition
   as Bool, infers yes then no, requiring no's type to equal yes's. Let checks
   value against its declaration before inferring body. Loop checks initial
   then body against its accumulator declaration. Arg/use return the resolved
   declaration's type. A mismatch reports that child; after a complete body's
   inference, a return mismatch reports the body. Both lazy arms are checked.
   Called signatures are available without recursively checking the callee.

For envelope exact-field failures, report the containing object before
inspecting its children. Other shape/tag/spelling/bound errors report the
offending field or array element; bad map keys report their containing map.
Expression wrong shape, empty array, unknown op or wrong operand count reports
the entire expression. Bad parameter-pair shape reports that pair; duplicate
parameter or shadowing reports the offending name occurrence. In phase 2
params is checked completely before
result/body; at an expression, arity is checked before metadata left to right,
then children. Loop freshness/type/count metadata are checked in array index
order. Static scopes track all names even before type checking. Structural
surrogate checking traverses metadata/scalars in the same order; this is not
a general callable-input rule for L2. Each reason above is an invalid-ir
observation, with value/type null and work zero.

### Invocation and evaluation

A native process input has exactly `schema`, `program`, `arguments`. Schema
is `bagaev-probe-invocation/1`; program is the complete kernel program;
arguments is a 0..8 element array. The input is limited to 1048576 bytes,
depth 132 and 16384 value occurrences. First check bytes/text, then outer
exact shape and version, then its depth/count, then the complete program
phases, then argument array shape/count and each argument left to right.
Invocation envelope failures use `IR_SHAPE`/`IR_VERSION`/`IR_BOUNDS`/`IR_JSON`;
argument failures use `IR_ARGUMENT`. Argument count equals entry arity;
each Int64 is an in-range JSON integer, each Bool a JSON Boolean. No field
defaults exist. Native process locations prefix program locations with
`/program`; invocation/argument locations already refer to the outer frame.

Work starts at zero. On entry to each evaluated expression, if work is 65536
refuse `work-limit` at that node before touching children and keep work at
65536; otherwise increment by one. Arguments and operands are evaluated left
to right. Call ticks, evaluates arguments, then the callee body; entry does
not add an implicit tick. Let ticks, evaluates value then body. If ticks,
evaluates condition then exactly one arm. Loop ticks, evaluates initial once,
then body for count iterations, with Int64 index 0..count-1 and the previous
scalar accumulator; count zero returns initial. Index increments, accumulator
assignment, parameter binding and return add no ticks. Not/comparisons add
only their expression tick. Arithmetic checks overflow after both operands
succeed; first observed runtime failure wins and aborts the entire invocation.
Unused branches and zero-count bodies cannot produce runtime errors/work.

Assign node numbers 1..512 by the same complete structural preorder, across
sorted functions. They include statically valid unused nodes. Overflow and
work-limit report the failing node's JSON Pointer. No partial value is exposed.
Every optimization mode preserves these source expression ticks, first-failure
order, work and location, including constant folding and removed machine-code
branches. Faster machine work does not remove semantic work. Program identity
is H(the complete checked program); no separate function
pins are supplied in this IR. A kernel result is exactly:

```
{"schema":"bagaev-probe-result/1","status":Status,"reason":Reason,
 "location":PointerOrNull,"value_type":TypeOrNull,"value":ScalarOrNull,
 "work":Integer}
```

Status is `success`, `integer-overflow`, `work-limit`, or `invalid-ir`.
Success has null reason/location and declared value_type with the actual
JSON Boolean/Int64. Runtime failure has null value_type/value, reason
`IR_OVERFLOW` or `IR_WORK`, location as above and consumed work. Invalid-ir
has the static/invocation reason, pointer, null value_type/value and work 0.
No compiler-specific trap or host exception is translated into these outcomes.
Process stdout is exactly C(result) followed by one LF, with no other text.
Exit code is 0 for all four complete language observations; inability to
complete the protocol is a nonzero environment failure, with no valid result.
Capture/resource policy is external. Stderr is never part of conformance.

### Fixed native ABI

Target is x86_64 Linux, little endian, baseline x86-64 CPU features, system C
calling convention. The entry symbol is `bagaev_probe_entry`; its C signature
is `void bagaev_probe_entry(const int64_t arguments[8], void *output)`.
Both caller-owned regions must be non-null, 8-byte aligned, valid for 64 and
32 bytes respectively, and disjoint; output is writable. Failure of these
memory preconditions is outside the callable domain, not a language result.
There is no struct return, pointer retention, callback or allocation API.
An entry's frozen signature determines the number/types of active slots.
Int64 is signed two's complement; Bool slots contain exactly 0 or 1; unused
slots contain 0. All input slots are read before output is written. The
function overwrites every output byte, including zero-valued fields.

| Byte offset | Width | Meaning |
| --- | --- | --- |
| 0 | uint32 | status: 0 success, 1 integer-overflow, 2 work-limit, 3 invalid-ir |
| 4 | uint32 | value type: 0 absent, 1 Int64, 2 Bool |
| 8 | int64 | success value (Bool 0/1); 0 on failure |
| 16 | uint64 | consumed semantic work, 0..65536 |
| 24 | uint32 | reason: 0 success, 1 IR_JSON, 2 IR_VERSION, 3 IR_SHAPE, 4 IR_BOUNDS, 5 IR_REFERENCE, 6 IR_CYCLE, 7 IR_TYPE, 8 IR_ARGUMENT, 9 IR_OVERFLOW, 10 IR_WORK |
| 28 | uint32 | location number: 0 success; node number for runtime failure; 0x80000001+i for bad argument slot i (0..7) |

Before any tick, direct ABI invocation checks active Bool and then unused
slots in increasing slot order (a single increasing-index pass). First bad
slot returns status 3/reason 8, absent value and work zero. The driver maps a
slot location to `/arguments/i`; it validates JSON arguments before calling
the ABI. A checked generated entry cannot return static IR errors; those
are driver observations before entry invocation. Static reasons have no ABI
node number because malformed IR never produces an entry. Driver JSON and
ABI callable domains differ only in this explicit transport/slot validation.
Node numbers map to `/program/functions/...` in process output. ABI status,
fields, work and JSON observations are identical for LLVM, Cranelift and
the independently written ordinary C baseline. A baseline may implement its
own checker/driver; it may not obtain expectations from another candidate.

Experimental modes are LLVM/Clang O0/O2/Os, Cranelift
none/speed/speed_and_size, and ordinary C11 O0/O2/Os. Unsupported settings
must be labelled unsupported, not substituted. No JIT, dynamic library,
catalog/storage bridge or architecture-specific host optimization is in this
kernel domain. Tool identities and dependency closure belong to separate
reviewed execution profiles; this contract does not adopt a Rust/tool release
for production. It defines byte layout directly and makes no broader platform
or external standards conformance claim.

## Actual L2 form family

Semantic contract/IR is exactly `bagaev-l2/1`, including all existing operations:
`literal`, `var`, `let`, `call`, `if`, `and`, `or`, `not`, `object`, `set`,
`array`, `get`, `has`, `null`, `shape`, `int.range`, `text`, `array.bound`,
`eq`, `lt`, `length`, `map`, `all`, `any`, `unique`, `sort`, `increasing`,
`sort.by`, and admitted scalar expressions. Each form recovers the entire
four-field L2 program, including pins, without arithmetic, type refinement,
normalization or changed semantics. The L2 checker is the semantic boundary;
every lazy arm, reference, call cycle and transitive pin retains its obligation.

The normative source is L2's Values and invocation, Exact program and expression
form, Bounds/deterministic errors/identity, and Transactional structural change.
In particular: callable ingress is borrowed and shallow, no pre-call deep
validation/copy/hash; errors are exactly existing L2 codes; n*n charges apply
to unique/sort/increasing/sort.by; each expression costs one; tags precede
Unicode validity then bounds as specified, short circuit is left to right,
object fields are ordered, and export is detached/bounded. Form receivers must
not replace these checks with kernel typing or kernel work limits. Runtime
results/errors and program/definition pins are form independent.

### Three exact encodings

Form names are `json`, `sexpr`, `familiar`. Their version is `probe-forms/1`.
Each source has at most 1048576 UTF-8 bytes. Forms are entire documents, with
no comments, interpolation, macros from the environment, escapes outside those
below, or include/import facility. The grammar's whitespace is only space,
tab, CR and LF. Initial transport overrun gives `FORM_BOUNDS`; invalid UTF-8,
BOM, incomplete syntax, duplicate decoded object key or trailing tokens give
`FORM_SYNTAX`. Source nesting beyond 256 or source value occurrences beyond
32768 gives `FORM_BOUNDS`, before further descent. Source strings use JSON
quoted-string syntax, including escaped surrogate code units: reconstruction
keeps them so the existing L2 checker supplies its existing semantic error.
There is no Unicode normalization. JSON floats are representable syntax and
reach the existing L2 checker rather than silently becoming ints.

`json` is exactly an L2 program JSON document. Its existing oversize/JSON
errors are `L2_BOUNDS`/`L2_JSON`, not remapped to FORM codes; L2 text limits,
depth and error priority remain normative. Roundtrip output for every accepted
form is the same C(checked L2 program), with exactly the supplied valid pins.
Encoding never repins or repairs a program on ordinary decode/check.

Compact S-expression grammar, where `string` and `number` use JSON tokens:

```
V := null | true | false | number | string
   | (arr V*) | (obj (string V)*) | (OP V*)
OP := literal | var | let | call | if | and | or | not | object | set
    | array | get | has | null | shape | int.range | text | array.bound
    | eq | lt | length | map | all | any | unique | sort | increasing | sort.by
```

Tokens require whitespace or a parenthesis boundary; unquoted arbitrary names
are invalid. `(arr ...)` reconstructs a JSON array; `(obj ("k" v) ...)`
reconstructs an object and refuses repeated decoded keys. `(OP ...)`
reconstructs `["OP", ...]`, including when that array occurs in literal data
or metadata: it is a representation macro, never an evaluated operation.
There is no ambiguity between scalar `null` and `(null V)` or between object
data and the L2 `object` expression. The program envelope is an obj value.
Check reconstructed JSON with the unchanged L2 checker. Source grammar
bound violations occur before reconstruction/L2 checking; otherwise complete
syntax reconstruction precedes L2 phases. Unknown operation text can be
represented as `(arr "unknown" ...)` and is then `L2_PROGRAM`.

Canonical compact rendering recursively emits scalars as C(scalar), objects
as `(obj (C(key) S(value))...)` with sorted keys, and arrays as `(OP S(rest)...)`
if their first element is exactly one known OP string, otherwise
`(arr S(element)...)`. Join sibling tokens with one ASCII space, with no
space after `(` or before `)`. Empty objects/arrays are `(obj)`/`(arr)`.
The same rule applies inside literal data. This is reversible JSON encoding,
not a claim of minimum size or an S-expression host interpreter.

The familiar-code form is a restricted construction grammar, not Python:

```
V := None | True | False | number | string
   | [ V (, V)* ] | { string : V (, string : V)* } | FN( V (, V)* ) | P | D
P := l2_program(entry=V,definitions=V,pins=V)
D := l2_def(params=V,body=V)
```

Empty list/object/argument sequences are allowed; trailing commas are not.
A program document is any V. P is an optional shorthand allowed only at its
root, not a required envelope. D is an optional shorthand allowed only as a
direct value in the definitions map: either P's definitions argument or the
root generic object's `"definitions"` field, when that value is an object.
Other definition values use generic V, including scalars, arrays and objects
with missing/extra fields. Neither a generic root nor a generic definition
is a syntax failure merely because it is not a valid L2 shape. P and D in
any other position are FORM_SYNTAX; these position rules inspect only source
structure, not L2 schema/type/reference/pin validity. Generic keys remain strings.
FN is exactly `l2_` followed by an OP name with each dot replaced by underscore
(for example `l2_int_range`, `l2_sort_by`). FN constructs `[OP, ...]` and
has no host execution. Its argument count is checked by L2. D constructs
`{"params":...,"body":...}`; P constructs the four-field L2 program with
schema `bagaev-l2/1`. P's three keywords and D's two keywords appear exactly
in the stated order; no others/repeats exist. P's entry argument is any V;
its required string/ID type is checked by L2 after reconstruction. A different,
absent or malformed schema is represented by the generic root, never repaired
by inserting P. All generic V keys/strings use
double-quoted JSON syntax; numbers use JSON grammar; None/True/False reconstruct
null/true/false. Bare identifiers, attributes, operators, indexing, assignments,
statements, comprehensions, f-strings, lambdas, decorators and calls to any
other name are `FORM_SYNTAX`. There is no import, eval or general host parser.
Complete syntax reconstruction precedes the unchanged L2 checking phases.
Malformed root/definition shapes, versions and metadata remain L2 errors;
construction does not omit unknown fields, add absent fields or repin anything.

Canonical familiar rendering chooses P only for a root object with exactly
`schema`, `entry`, `definitions`, `pins` and schema exactly `bagaev-l2/1`.
Otherwise render the entire root as generic V, preserving every key/value and
the root's scalar/container tag. At the permitted definition positions, choose
D only for an object with exactly `params` and `body`; otherwise render that
value as generic V. These choices depend only on shape/value, not successful
L2 admission: invalid entry/params/body/pins values are not repaired or checked
early. Thus valid canonical programs keep their P/D rendering, while negative
shape/version mutations retain their exact reconstructed JSON and L2 priority.
Use FN for every JSON array with a known first OP string, and lists otherwise,
recursively including literal data. Generic objects have sorted keys;
strings/numbers use C; null/bools use None/True/False. Separate comma-delimited
items by `, `, key and value by `: `, with no internal leading/trailing spaces.
P uses `l2_program(entry=..., definitions=..., pins=...)`; D uses
`l2_def(params=..., body=...)`. Accepted input may have arbitrary grammar
whitespace; canonical output is unique. The root/definition constructors add
no semantic feature and repair nothing.

### Finite fixture domain and encoding cost

The shared program fixture domain is valid L2 programs, and invalid mutations
of their shapes, with C(program) <=65536 bytes, <=8192 JSON value occurrences,
<=8 definitions, <=512 expression occurrences and expression depth <=32.
All remaining L2 bounds/semantics apply unchanged. These are fixture selection
bounds, not a change to L2 admission. Valid source programs in this common
domain fit all three canonical forms' transport bounds: constructor/token
overhead is bounded by the same value count. Negative mutations use the same
reconstructed JSON and common bounds; transport-specific malformed syntax
has separate format refusal cases. All forms decode the entire L2 grammar,
but acceptance/comparison covers this finite common fixture domain. A common
independently frozen selection is used without per-form removal of difficult
outcomes. The pure family is separate from full AP1 and the typed kernel.
An unsupported transport cannot count as successful evaluation or silently
narrow the workload. No form is given a weaker expected result.

Argument fixtures use a finite descriptor domain: depth <=256, occurrences
<=65537, objects <=33 fields, arrays <=257 elements, strings/keys <=4097
decoded code points (Unicode scalars or isolated surrogate code points,
with an astral character counting once), integers
from -1208925819614629174706176 through 1208925819614629174706176, and floats
exactly -1.5, 0.0 or 1.5, plus bool/null. Descriptors have <=1048576 ASCII JSON
bytes and represent strings as arrays of integer code points 0..1114111,
floats as one of the strings `-1.5`, `0.0`, `1.5`, integers as minimal decimal
strings, objects as ordered `[keyDescriptor,valueDescriptor]` pairs with
distinct decoded keys, and arrays as ordered descriptor arrays. Each descriptor
is exactly `[tag,payload]`, tags `null`, `bool`, `int`, `float`, `string`,
`array`, `object`; null payload is null, bool payload a bool. Array payload
contains descriptors; object keys use string descriptors. No cycles, custom
objects, aliasing or caller mutation exists. The descriptor's JSON nesting
limit is 1024 and value occurrences 524288, separately from decoded bounds.
Descriptors are fixture preparation, not a new runtime input gate. Once
constructed, pass the argument directly to L2 without validation/copy/hash;
large/deep or surrogate content can be rejected by a reached shallow predicate
without traversing it. This finite domain intentionally includes values outside
L2 export bounds. It supplies no literal expected values or fixture selection.

For each program record the same semantic identity H(program), raw source
bytes including whitespace, canonical source bytes for each form, canonical
JSON program bytes, request/context/response bytes separately, and actual
tokenizer tokens only when observable under a declared tokenizer profile.
No byte count is called a token count. Diagnostics, failed attempts and edit
frames count in their own actual encodings; no form receives free hidden
context, smaller oracle or omitted failure. Decode/encode does not perform
runtime evaluation.

### Structural edit drafts

An edit frame has exactly `schema`, `form`, `base`, `candidate_id`, `patch`.
Schema is `probe-form-edit/1`; form is one of the three forms; base is a digest;
candidate_id is an ID or null. Patch is a UTF-8 source string encoded as a
JSON string; it reconstructs an ordinary `bagaev-l2-patch/1` value in the
selected form. A familiar patch document is generic V; a valid patch has an
object root, with optional D for values directly in root add/replace maps.
P is not permitted anywhere in a patch. As with programs, generic V also represents
malformed patch roots, map values and definition shapes without syntax-level
repair or semantic filtering; ordinary L2 patch checking supplies their errors.
D has the same positional restriction and exact two-key reconstruction;
canonical patch rendering selects it only for exact params/body objects in
those positions, with generic V otherwise. Compact and JSON use the same
generic grammars. Rendering never repins source. Entire frame <=2097152 bytes,
depth <=8, <=32 value occurrences; decoded patch source <=1048576 bytes. No files are
written, candidate IDs allocated, live snapshots replaced or effects run.

Validation checks the original L2 program first, retaining its L2 error code.
Only a valid original reaches these outer-frame gates, in this exact order:

1. `FORM_BOUNDS` at the root for more than 2097152 received bytes, including
   whitespace, before decoding; no truncated prefix is processed.
2. `FORM_SYNTAX` at the root for invalid UTF-8, BOM, malformed JSON syntax, duplicate
   decoded object keys, nonfinite/non-JSON number spellings or a second value.
   Trailing JSON whitespace is allowed. Well-formed escaped surrogate code
   units are parsed and left for field validation; they are not repaired.
3. `FORM_BOUNDS` at the root for parsed depth greater than 8 or more than 32 value
   occurrences. Traverse preorder, object keys sorted by Unicode code point,
   arrays in index order, checking each value before descent. Root depth is 1;
   keys do not count as values or add depth. Stop at the first value exceeding
   a bound; depth wins over occurrence count at the same value. The location
   remains the root, including when a traversed object key is a surrogate.
4. `FORM_SHAPE` at the root unless it is an object with exactly the five
   required keys above. Missing/unknown keys refuse before field inspection.
5. Inspect `schema`: a non-string or isolated surrogate gives `FORM_SHAPE`
   at `/schema`; a scalar string other than `probe-form-edit/1` gives
   `FORM_VERSION` there.
6. Inspect `form` the same way: non-string/surrogate gives `FORM_SHAPE` at
   `/form`; any other scalar string than `json`, `sexpr`, `familiar` gives
   `FORM_VERSION` there. No fallback or guessed codec is used.
7. `FORM_SHAPE` at `/base` unless it is a Digest with the exact shared spelling.
8. `FORM_SHAPE` at `/candidate_id` unless it is null or an exact shared ID.
   This checks spelling/type only; candidate-map resolution remains later.
9. Inspect `patch`: a non-string or isolated surrogate gives `FORM_SHAPE` at
   `/patch`; then more than 1048576 decoded UTF-8 source bytes gives
   `FORM_BOUNDS` there. A source's literal backslash-u escape spelling is
   preserved for its own decoder/L2 checker, not interpreted as an outer
   surrogate character. No patch syntax/semantics is checked at this gate.

Outer locations are JSON Pointers in the edit frame; root means the empty
string. The first failure is the only observation, with no candidate. The
patch string counts as one outer value, not its later reconstructed contents.
These wrapper checks do not normalize input, repin, or precheck L2 definitions.

After all outer gates, decode the patch in the selected source form, retaining
its specified source-form errors; check ordinary L2 patch envelope/digest
spellings/map shape; require frame base equals patch base (`FORM_BASE` at
`/base`);
require optional candidate_id resolves to the caller-supplied immutable
candidate map and that its kind is patch and its content pin equals H(patch)
(`FORM_CANDIDATE` at `/candidate_id`); then apply ordinary L2 base CAS,
add/replace constraints,
atomic candidate checking/repinning and exact target checking, in existing
L2 order. A caller with no candidate map must use null candidate_id.
The normal L2 codes including L2_STALE/L2_TARGET are retained; they have no
normative location, and an enclosing location field is null. Source-form
locations refer to the decoded patch source, not an invented path through
the outer JSON string. The late FORM_BASE/FORM_CANDIDATE locations above
refer to the outer frame. An earlier patch syntax/envelope error wins over
these late comparisons; a stale original base is still checked after them.

Success returns a detached draft with exactly schema `probe-draft/1`,
status `draft`, base, target, program (the complete checked new L2 snapshot),
patch (the reconstructed patch), and admission false. Target is H(program).
Failure returns no candidate and preserves original/patch/retained snapshots.
Caller is the sole snapshot owner; there is no shared transaction, write queue,
DB, implicit commit or receiver admission. A successful draft can be submitted
for separate checking/admission; it cannot authorize itself. Complete changes
are add/replace definitions only: no delete, root edit or in-place mutation.

## Portable context and finite choices

This contract is a bounded probe context, not a generic project service or
model API. It can transport exact sources, obligations, unknowns and candidate
choices to a fresh receiver without earlier messages, hidden reasoning,
KV/cache, decoder state, filesystem/network discovery or model calls.
Receivers perform deterministic validation/reconstruction only. Validity,
semantic intent, authority, execution admission and empirical model benefit
are different facts.

A context has exactly `schema`, `axes`, `snapshot`, `sources`, `obligations`,
`unknowns`, `open_effects`, `candidates`, `candidate_set`, `metadata`:

| Field | Exact structure |
| --- | --- |
| schema | `probe-context/1` |
| axes | Exactly semantic, ir, form, envelope, evidence; supported tuples below. |
| snapshot | H(the semantic program), independently expected by the receiver. |
| sources | 1..16 records: id:ID, pin:digest, text:string. Pin=B(UTF-8(text)); each text <=131072 bytes, aggregate <=1048576 bytes. IDs distinct, sorted. |
| obligations | 1..32 records: id:ID, text:string, refs:1..8 source references, pin:digest. Pin=H(record with pin omitted). IDs distinct, sorted. |
| unknowns | 0..32 records: id:ID, text:string, refs:0..8 source references. IDs distinct, sorted. |
| open_effects | 0..16 records: id:ID, text:string, refs:1..8 source references. IDs distinct, sorted. These describe unresolved effects, never replay/authorize them. |
| candidates | 0..16 records: id:ID, kind:`program` or `patch`, state:`choice` or `draft`, content:JSON object, pin:H(content). IDs distinct, sorted. Immutable within this context. |
| candidate_set | H({schema:`probe-candidate-set/1`,candidates:[{id,kind,state,pin},...]}); same sorted order, including drafts. |
| metadata | Exactly representation:`canonical-json/1`, model_profile:string or null, codec:string or null. Claimed metadata is opaque, not attested capability/authority. |

Except source text, text/model_profile/codec strings have <=4096 UTF-8 bytes.
Text fields in obligations/unknowns/effects are nonempty. References have
exactly `source`, `pin`, `start`, `end`: source ID, B(source bytes), and integer
UTF-8 byte offsets 0<=start<end<=source size, both at code-point boundaries.
Reference arrays sort by (source,start,end), no duplicates. References cannot
resolve through a summary or source with a different pin. Every context record
has exactly its stated fields. IDs need only be unique within each collection;
references explicitly identify their collection. Candidate content is bounded
by its own semantic source contract; each C(content) <=1048576 bytes, aggregate
<=2097152 bytes. Context C/text transport <=4194304 bytes, depth <=136,
value occurrences <=65536. Validate source bytes before computing source pins.

Supported axes are independently versioned but supported combinations are
explicit: semantic=ir=`bagaev-l2/1` or semantic=ir=`bagaev-probe-ir/1`,
form=`probe-forms/1`, envelope=`probe-context/1`, evidence=`probe-evidence/1`.
Form describes representation/accounting protocol; the three L2 source forms
apply only to the L2 tuple. Kernel candidates use canonical JSON only, not
new L2 forms. A future semantic/IR/form/evidence axis needs explicit support;
equal version numbers do not imply compatibility. Metadata's model/codec
claims never make an unknown mandatory axis acceptable.

Candidate content is a complete semantic program or a complete L2 patch.
Kernel tuple supports program kind only. `choice` programs must pass their
semantic checker including all supplied L2 pins; choice patches must apply
against the exact snapshot and supplied pinned baseline with matching target.
Draft content may be structurally incomplete JSON but never selectable; it
remains bounded scalar-value JSON and is explicitly labelled draft. Candidate
ID cannot denote different content, kind or state under the same candidate_set.
Refinement creates a new context/map digest and, if a draft is offered as a
new candidate, a new ID; old mapping remains immutable. Receiver stores or
receives its expected map from outside the candidate; a packet cannot replace
that expectation. There is no ordinal/index fallback or latest-ID lookup.

### Reconstruction and refusal priority

The receiver is supplied a baseline semantic program, expected axes/snapshot,
expected candidate_set, required source ID/pins and required obligation ID/pins
by its caller in a separate expectation frame. It has exactly schema
`probe-expectation/1`, axes (the same five-field shape), snapshot:digest,
candidate_set:digest, sources:1..16 sorted records, obligations:1..32 sorted
records, baseline:complete semantic program. Both record kinds have exactly
id:ID and pin:digest, with distinct IDs within each array. Baseline has its own
semantic bounds; the expectation frame is <=2097152 bytes, depth <=136 and
<=32768 occurrences. These finite expectations are separate trusted inputs,
not invented by the packet; trusted here means caller-supplied comparison
data, never a grant of execution authority. Their absence means `CTX_MISSING`
at the root; unrecognized expectation schema/axes means CTX_VERSION.
Record open unknowns explicitly; they are not evidence that an obligation
has been met. A required obligation/source cannot be silently dropped because
a summary fits. Matching pins/closed syntax alone do not prove context complete.

Validate in this exact order (first failure, root location for transport):

1. Transport bounds `CTX_BOUNDS`, then UTF-8/JSON/duplicate keys `CTX_JSON`.
2. Context exact root/axes shape `CTX_SHAPE`, known mandatory axes/schema
   `CTX_VERSION`, then all depth/count/collection/field bounds and shapes,
   IDs/order/duplicate records in field-table order. Bound errors CTX_BOUNDS,
   other structural errors CTX_SHAPE. Surrogates refuse CTX_SHAPE.
3. Caller expectations presence/shape/version; reconstruct baseline with its
   semantic checker (underlying IR/L2 code is retained if invalid), compare
   expected axes and snapshot to baseline and packet (`CTX_STALE`).
4. Sources in sorted order: content pin (`CTX_PIN`), required source absence
   (`CTX_MISSING`) or expected source pin mismatch (`CTX_STALE`). Then all
   references in obligations, unknowns and open_effects, in that order:
   missing source CTX_MISSING, pin mismatch CTX_STALE, invalid byte span
   CTX_SHAPE. No external resolution or fetching exists in this profile.
5. Obligation record pins (`CTX_PIN`), required obligation presence
   (`CTX_MISSING`) and expected pins (`CTX_STALE`), sorted by ID within each
   subpass. Open required unknowns are not resolved by this check; the caller
   must either disclose sufficient pinned material or keep the task unknown.
6. Candidate content pins then calculated candidate_set (`CTX_PIN`), expected
   mapping (`CTX_REMAPPED`), then choice semantic checking by sorted ID.
   Drafts are not checked as complete programs. Missing choice baseline is
   CTX_MISSING. Semantic failures retain the underlying checker code.
7. Evidence records and decision frames as specified below. No admission or
   model/provider activity follows validation automatically.

For candidate pin failure report `/candidates/i/pin`; set digest/expected-map
failure reports `/candidate_set`. For missing expected record report its
collection pointer, not a fabricated index. Locations otherwise follow the
failed field/ref; underlying L2 errors have null location because L2 code alone
is normative. Underlying IR paths are prefixed by their baseline/candidate
   content frame location. A refused context exposes no partially validated choice.

### Evidence frame

Evidence is a separate optional input frame, never embedded authority. It has
exactly schema `probe-evidence/1`, context:H(context), snapshot:digest,
records:0..32 records. A record has exactly id:ID, subject:digest,
obligations:1..32 sorted distinct obligation IDs, result:`supported`,
`negative`, `indeterminate` or `not-run`, source:one source reference.
IDs are distinct and sorted, subject names snapshot or a candidate content
pin, and the reference must resolve in the exact context. Frame <=262144
bytes, depth <=16, occurrences <=4096. Parse/shape/version/bounds use CTX
codes; compare context/snapshot (`CTX_STALE`), resolve subject/obligations
and source (`CTX_MISSING`/`CTX_STALE`), then retain the stated result.
No text assertion, previous local run, confidence or supported label proves
external execution; evidence applicability is tied to these exact pins.
Missing evidence stays unknown, never silently supported.

### Decision roles and response frames

A request has exactly schema `probe-decision/1`, context:H(context),
snapshot:digest, candidate_set:digest, role, target, intent:string.
Intent is 1..4096 UTF-8 bytes. Role is generate/refine/select/rank/solve.
Target is ID for refine, null otherwise. Request <=65536 bytes, depth <=8,
occurrences <=64. Parse/shape/version/bounds use CTX codes; compare context,
snapshot then map (`CTX_STALE`, `CTX_STALE`, `CTX_REMAPPED`), then role support:
rank/solve give `CTX_UNSUPPORTED`. Refine's target must exist and be a draft
(`CTX_MISSING`/`CTX_DRAFT`); generate/select require null target. Supported
roles have different capabilities: generate/refine produce drafts; select
chooses a pinned choice. Nothing claims ranking, solving or model availability.

A response has exactly schema `probe-response/1`, request:H(request),
context:H(context), snapshot:digest, candidate_set:digest, role, outcome,
candidate_id, content, content_pin, code. Response <=2097152 bytes, depth
<=136, occurrences <=32768; content <=1048576 canonical bytes.
First parse/shape/version/bounds, then compare request/context/snapshot in
that order (`CTX_STALE`), map (`CTX_REMAPPED`), role equality (`CTX_ROLE`),
then outcome rules below. IDs/pins and all fields remain present with null
where specified. Wrong outcome field combinations give CTX_SHAPE.

| Role/outcome | Exact payload and interpretation |
| --- | --- |
| generate/refine + draft | candidate_id null; content a bounded JSON object, possibly incomplete; content_pin H(content); code null. Return a draft, not a checked/admitted change. |
| select + choice | candidate_id a pinned ID with state choice; content/content_pin/code null. Resolve content only from the validated immutable map; absent ID CTX_MISSING, draft ID CTX_DRAFT. |
| any supported role + abstain | candidate_id/content/content_pin/code null. Terminal no change, no failure concealed. |
| select + no-choice | candidate_id/content/content_pin null, code CTX_NO_CHOICE. Terminal no change; empty set permits this outcome, not an invented option. A nonempty set may also have no suitable choice. |
| any supported role + refused | candidate_id/content/content_pin null, code one of the defined CTX codes. A declared refusal, not automatic recovery/admission. |

Returning choice for generate/refine or draft for select is `CTX_ROLE`.
Trying to treat any draft response as an admission-ready choice is `CTX_DRAFT`;
complete independent checking and external admission remain separate. Content
pin mismatch is CTX_PIN. No-choice/abstain has no content, selection or latent
execution. Output is C(response) as a complete frame; model streaming partial
tokens are incomplete transport, never successive implicit admissions.
Generation/refinement creates only a proposal; select does not prove semantic
intent or optimality. There are no credentials, provider endpoint, tool port,
budget allocation, mutable registry, external effect or model call in these
interfaces. Raw/canonical source, candidate-map, context, request, response,
evidence and edit bytes are counted separately; repeated/failed frames count.
Tokenizer counts and model metadata require separately observed profiles.

## Acceptance boundaries

Independent expectations must freeze before candidate implementation. Required
families include typed minimum/maximum/overflow, first failure/order/laziness,
exact work boundary, zero/maximal loops, invalid structural/name/type/version
cases, L2 shallow/error/order/work/pin parity across all forms, roundtrip/CAS
and malformed encodings, portable context loss/staleness, missing obligations,
changed candidate mappings, unknown axes, abstain/no-choice and draft refusal.
Mutations must challenge unchecked arithmetic, eager branches, omitted work,
repinning/normalization, changed shallow ingress and automatic draft admission.
This list defines coverage obligations, not literal expected outputs.
Contract/source review cannot close runtime, native, resource isolation,
comparative measurement, full AP1 or model-benefit gates. Unobserved checks are
NOT_RUN; unsupported/negative/indeterminate findings remain distinct.
