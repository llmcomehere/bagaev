# Separate bounded pure record profile 11

The explicit `bagaev-typed-record/11` reference supports named record lists with
capacity 0–16. Earlier profiles 1–10 retain capacity 0–4. The new entrypoint is
`record_wide_main.rs`, using `typed_record::process_v11`; it accepts invocation/11
and returns result/11. It does not auto-detect older schemas.

All other existing limits remain: eight named types, expanded shape budget 4096,
32 functions, 2048 nodes, bounded recursion/work/transport and primitive values.
A capacity 16 declaration can still be refused when its expanded nested shape
exceeds 4096 units. Length, access and immutable append use the declared capacity;
appending to a full list refuses RR_RECORD_LIST_ITEMS with no partial result.
This is a separately versioned pure reference profile, not an expanded native ABI,
component-owned state, durable catalogue or production runtime.

The pure [conditional work analyzer](../src/bagaev_record_work.py) estimates
upper logical work for a small expression subset using declared
argument bounds. It requires separately checked program semantics and valid
arguments. Unsupported operations return `UNKNOWN`; a bound above 65,536 means
possible budget exhaustion, not certain failure. It grants no execution admission
and does not measure latency or memory. [Literal tests](../tests/probes/test_record_work.py)
include the sorted-unique example's boundary and the extra charge of negated equality.
Integer addition, subtraction and multiplication charge their node and strict
operands; their work bounds do not prove absence of integer overflow. A fitting
work budget can still accompany an `RR_OVERFLOW` refusal.
Conditionals add the condition's bound and the larger arm bound; both arms must
be supported. Branch shapes join conservatively, without refining bounds from
guards. Supported-shape helper calls use fresh parameter/local scopes and
charge each call separately; cycles or excessive expansion yield `UNKNOWN`.
Literal-count loops are summarized only when a primitive accumulator's body
shape stays within its initial maxima. The bound is one loop entry, initial
work, and count times the body bound. Even zero-count loops require a supported
invariant body. Growing shapes and nominal accumulator types remain
unsupported; no body is executed or unrolled by this analysis.
With declaration maps, nominal record-list input bounds use
`{"type":"Items","items":N}` for a declared capacity up to 16. The supported
element fields are Int64/Bool only. Length, index and scalar field projection
retain nominal names; helpers can accept/return these declared scalar record/list
shapes without losing their identity or bounds. Nested/Text fields and nominal
accumulators remain unsupported. A fitting work bound does not prove index validity.
Declared scalar record constructors also retain nominal identity, with fields
checked in sorted field-name order. Opaque non-scalar or undeclared constructors
keep their earlier cost-only summary, which cannot support field projection or
a nominal helper result.
The [helper extraction specimen](../examples/probes/record-work-helper-edit/Extracted.bagaev)
uses the existing whole-source draft to add `amount` and replace only `main`.
Its [pinned graph/result data](../examples/probes/record-work-helper-edit/cases.json)
preserve values at counts 0/2/16, while upper work changes from 178 to 210 and
observed work increases by 0/4/32. The six complete responses reuse prior exact
invocation captures, not new execution. This example grants no semantic admission
and does not claim work equivalence or optimization.
The [finite cardinality cases](../examples/probes/record-work-cardinality/cases.json)
preserve 49 complete reference observations: all 17 lengths of one guarded sum,
30 positive/negative overflow positions and two invalid indices. All matched
their pre-frozen full result envelopes; observed work stayed within the bound.
The accompanying static test checks analysis only, without launching an evaluator.
These are finite conformance observations, not exhaustive Int64/AST coverage or
performance measurements.
Eight additional [composition cases](../examples/probes/record-work-composition/cases.json)
matched pre-frozen complete reference responses. They cover componentwise branch
joins used by subsequent work, loop invariants after shrinking lists, helper
costs, nested loops and left-to-right early refusal. An overflowing left operand
stops at work 4 although the full expression's upper bound is 3007. The analyzer
need not predict which branch/refusal occurs to provide a conservative bound.
Expression refusals include a function name and body-relative JSON pointer;
the analysis library uses a null function for its supplied root expression.
These identify the unsupported expression, not a source character span.

The explicit [resource-aware edit](../examples/probes/record-work-edit/Reuse.bagaev)
reuses a sorted-unique value that [the original](../examples/probes/record-work-edit/Repeated.bagaev)
computes twice. [Frozen paired cases](../examples/probes/record-work-edit/cases.json)
pin both graphs: at 64 items and 256 UTF-8 bytes the upper bound changes from
73739 to 36874. The draft changes only `summarize`; this is not an automatic
optimizer or a claim of identical refusal behavior. Six own reference observations
matched the full expected envelopes, including the original's `RR_WORK` and the
edited version's success on that boundary case. This is no latency measurement.
`record_text.py inspect SOURCE --form 5 --bounds BOUNDS --output NEW_FILE`
adds that analysis and the exact bounds-file SHA-256 to inspection data.
`BOUNDS` is a JSON map matching entry parameters, for example
`{"xs":{"type":"TextList","items":64,"bytes":479}}`. These are declared maxima,
not validated runtime arguments. The default inspection output is unchanged;
other operations/forms reject `--bounds`. No program is run.

## Readable source

Explicit record-form/5 selects this new schema and allows capacities up to 16:

```bagaev
bagaev record-form/5;
program {
  record Item { n: Int64 };
  list Items of Item capacity 16;
  entry main;
  fn main(xs: Items) -> Int64 =
    fold (16, 0) with (i, sum) in
      sum + record.field(records.at(xs, i), "n");
}
```

This particular function requires 16 actual elements to avoid an index refusal.
For values 0 through 15 it returns 120. For variable lengths, guard each access by
records.len as in earlier batch examples. Choose `record_text.py ... --form 5`
explicitly for decode/encode/prepare/inspect. Preparation writes invocation/11;
it still launches no evaluator. Old forms and fixed form1/4 diagnostics/drafts
remain unchanged and do not silently accept form5.

## Build and evidence boundary

Compile the reviewed `examples/probes/backend/rust/record_wide_main.rs` using a
separately approved local build profile (Rust edition2021, warnings denied).
No toolchain installation, environment authority or execution permission is
provided by this document. Use an explicitly reviewed/hash-identified executable
with the portable `record_wide_checks.py --reference PATH --reference-sha256 HASH
--legacy PATH --legacy-sha256 HASH --output NEW_DIRECTORY` under your execution
profile. The legacy executable must be the profile 10 reference.

Seven new literal cases cover 16-element length/sum/push, full append refusal,
capacity 17, 17 arguments and expansion-budget refusal. These and 99 unchanged
catalogue responses passed through profile 11, plus an old-profile capacity
refusal: 107 reference calls. A readable sum invocation returned 120. The freshly
rebuilt old profile 10 matched its previous executable byte-for-byte on all 99
catalogue result wires, including work/status/refusal fields (198 calls).
These are conformance/regression observations, not performance measurements.

The old catalogue application contract itself still allows four entries. This
profile enables larger pure functions; it does not rewrite that contract or its
frozen 99-case oracle. The initial reference-profile change did not alter native exporters, adapters
or execution controls. Later separately versioned native stages are linked below.
Independent reproduction and broader acceptance remain open.

A separate [sixteen-entry catalogue](catalog-wide.md) now exercises this profile
without changing the old application contract.

[Focused form5 editing](wide-function-editing.md) exports direct context and
creates pinned detached single-function replacements.

[Data-only LLVM preparation](probe-native-wide-emitter.md) is a separate initial
native stage. Its initial checks did not execute generated code; subsequent
selected native qualification is linked below.

## Subsequent selected native execution

The [generated-kernel qualification](probe-native-wide-qualification.md) records
a later bounded execution of two fixed profile11 kernels. Earlier unrun-stage
statements above retain their historical scope; this does not claim complete
native coverage or performance.

## Json numeric argument transport

For a Json-only entry that needs to inspect fractional or large JSON numbers,
use the separately selected [lossless Json preparation](json-argument-prepare.md)
route. The original typed-argument preparer remains strict and unchanged.


## Form5 record-list literal boundary correction

The explicit form5 reader now accepts up to sixteen items in a records.list
constructor, still subject to the declared list capacity. It previously inherited
the older reader's hard four-item parsing limit: a valid capacity 16 literal could
not decode, and encoding the same graph also failed its roundtrip check.
Only the form5 reader's constructor branch changes. Older codecs, runtime work,
profile bounds and native semantics remain unchanged.

Eight pre-frozen boundary cases cover counts 0/4/5/16, zero capacity, count 17 and
declared-capacity overflow. Three data tests check exact graphs, roundtrip,
formatting/idempotence and unchanged form4 behavior. The accepted sixteen-item
sum source now encodes/decodes to its existing exact graph. Five literal-list
invocations and that sum passed six fresh preparation/reference calls with full
values and logical work; the sum remains 120 at work 610. Existing native results
for the identical sum graph are prior evidence, not new native execution.

Existing form5 graph, diagnostic and formatter suites also passed unchanged.
The [before-fix observation](../examples/probes/wide-record-literals/reproduction.json)
is retained alongside the [literal cases](../examples/probes/wide-record-literals/cases.json).
The initial reproduction harness assumed encoding would return before decoding;
the encoder itself performs a roundtrip and already refused. No oracle was
changed to conceal that behavior.

## Control-expression operand grouping

The form5 encoder now groups `fold`, `if`, `let` and `match` when they appear as
operands of arithmetic or `<`. A real focused batch-policy edit exposed the bug:
`fold(...) ... in (...) + value` put the addition inside the fold body instead
of outside it. The encoder's final graph-roundtrip check correctly refused;
that check remains intact. Right-hand control expressions could instead refuse
syntax because they were emitted where an atom was required.

Six [graphs frozen before the correction](../examples/probes/wide-control-operands/cases.json)
cover loop/if on either addition side, let in multiplication and match in a
comparison. They now roundtrip exactly. Six fresh reference calls matched the
literal results 12,12,6,6,9,true. Two existing default context packets remained
byte-identical. The previously blocked batch fragment also roundtripped exactly
in local preparation; that does not claim acceptance or execution of the new
batch policy. Grammar, programme semantics, old codecs and execution controls
are unchanged. No new native execution or measurement was performed for this fix.

An explicit [source-once Json reference API](prepared-json11-reference.md) reuses
checked profile11 source across owned argument arrays. It is separate from the
full-invocation and native paths and grants no native execution admission.

## Lazy Boolean authoring in form5

Use `bool.and(left, right)` or `bool.or(left, right)` when combining conditions.
These are short-circuit surface forms, not eager ordinary function calls:

```
bagaev record-form/5;
program {
  fn main(x: Int64) -> Bool = bool.and(0 < x, x < 10);
  entry main;
}
```

`bool.and(a,b)` lowers exactly to `if a then b else false`;
`bool.or(a,b)` lowers exactly to `if a then true else b`. The right branch is
therefore evaluated only when needed. Both branches must still type-check:
`bool.and(false,7)` is rejected as invalid IR even though the right branch would
be skipped. Arity is exactly two. Earlier forms do not accept these spellings.

No IR operator, runtime rule, native ABI or resource budget was added. Canonical
encoding deliberately keeps the existing `if` spelling, so formatting may expand
the shorthand while preserving the exact graph and program pin. In the readable
source map, the generated Boolean literal has an enclosing call range, never a
fabricated exact token range.

Fourteen frozen graphs cover both truth tables, nesting, skipped/executed right
side overflow and the skipped type error. Twenty-eight bounded reference calls
matched shorthand and explicit-if outputs including work/refusal metadata. Four
arity and two old-form refusals were checked. Fourteen portable tests covering
this feature and existing source maps/control operands/list literals passed.
No generated native code or model was run for this syntax addition.

## Named arguments for user functions

Form5 also accepts fully named calls to declared user functions:

```
bagaev record-form/5;
program {
  fn main() -> Int64 = diff(b: 2, a: 9);
  fn diff(a: Int64, b: Int64) -> Int64 = a - b;
  entry main;
}
```

This lowers to `diff(9,2)` and returns 7. Declaration-parameter order determines
both the lowered argument order and runtime evaluation order, including which
failing argument is encountered first. Textual named-argument order does not
change evaluation order. Forward function declarations and local `let`/`fold`
bindings are supported. Canonical formatting retains positional calls.

Every argument in a call must be named, or every argument must be positional.
Duplicate, unknown and missing names, unknown callees and ambiguous duplicate
callee parameters are refused. At most eight arguments are accepted. Intrinsics
and constructors retain their own positional syntax; older source forms are
unchanged. Named calls add no IR operator, native ABI or runtime semantics.
Source-map argument pointers follow each original value expression after reordering.

Six frozen cases, each with both declaration orders, produced 24 bounded
reference observations equal to explicit positional graphs and complete outputs.
A reversed-text pair of failing arguments still failed at the declared first
argument with the same work count. Eight syntax refusals and old-form rejection
were checked; portable tests additionally cover eight/nine argument boundaries.
No new native or model execution was needed for this exact lowering.

### Opt-in named-call encoding

The codec's `encode_named(program)` returns an alternate graph-to-source view
with declaration parameter labels on user-function calls. `encode(program)`
remains the same canonical positional encoder. The command-line selection is:

```
python tools/record_text.py encode program.json --form 5 --named-calls --output named.bagaev
```

The flag is valid only for form5 `encode`; other operations/forms refuse it
before input access or output creation. Known unambiguous declarations and exact
argument arity are required. Zero-argument calls remain `f()`, and intrinsics
remain positional. The complete output is decoded and compared to the original
graph before the existing exclusive output writer is used. Explicit named-mode
receipts add `named_calls:true`; default receipts and outputs are unchanged.

This is an opt-in source view. The existing token formatter already preserves
named labels supplied in source; it is not replaced by this encoder. Eight
frozen graphs retained their previous default bytes and matched named round-trip,
source-map and idempotence checks. Seven data CLI observations covered both views,
wrong operation/form and existing-output preservation; three malformed callee
contracts refused. No program, native code or model was executed for this view.

## Line comments

After the required `bagaev record-form/5;` header, `//` starts a line comment
outside string literals, ending at LF or end of file. For example:

```
bagaev record-form/5;
program {
  // Return the difference; named arguments still follow declaration order.
  fn main() -> Int64 = diff(b: 2, a: 9);
  fn diff(a: Int64, b: Int64) -> Int64 = a - b;
  entry main;
}
```

Comments may appear between tokens or after the program. `//` inside a quoted
Text value stays text. Comments before or inside the mandatory header and block
comments are not supported. Raw comment control characters other than tab/CR
are refused. All comment bytes count toward the existing source byte bound;
semantic-token, graph and runtime bounds are unchanged. Earlier forms are unchanged.

The reader, source-map ranges and lexical diagnostics share one tokenizer.
Comments do not enter the program graph or its canonical pin. Exact source hashes
and byte/line ranges still include the original layout. The token formatter
retains comment text/order on standalone lines and may normalize trailing
whitespace; canonical and named graph encoders omit comments because IR contains
no comment data. Comments cannot supply execution authority or provenance.

Seven frozen cases cover body/inline/inter-token/trailing/CRLF/Unicode comments,
comment punctuation and slash-like string values. Graph, value ranges, comment
retention and formatter idempotence were checked; prior comment-free formatter
bytes and seven existing exact diagnostic observations remained unchanged.
Twenty-five portable tests and 21 data CLI observations passed. No source program,
native kernel or model was executed for lexical trivia.

### Value-preserving extraction can cross the work limit

The [helper-limit pair](../examples/probes/record-work-helper-limit/cases.json)
uses a 1024-iteration scalar loop. Its balanced addition body has 32 leaves
and 31 additions: the accumulator plus 31 ones. The direct program returns
31744 at 64514 logical work units. Extracting the rightmost literal into a
zero-argument helper preserves the unbounded arithmetic value but adds one
charge per iteration. Its upper bound is 65538; the observed profile11 result
is `RR_WORK` at work 65536 and
`/program/functions/main/body/5/2/2/2/2/2`. Two own-reference observations
matched independently frozen complete envelopes. These are logical charges,
not elapsed-time measurements. An excessive upper bound alone does not prove
failure for arbitrary programs; this particular straight-line body has an
independently enumerated exact charge sequence. Value equivalence does not
establish resource-bounded observational equivalence or execution admission.

### Data-only paired upper-bound comparison

The pure [comparison API](../src/bagaev_record_work_compare.py) accepts original
and candidate form5 source, one shared entry-bound map, and exact base/target
program SHA-256 pins. It applies the existing whole-source function-draft scope:
unchanged declarations and signatures, with added/replaced functions only.
The receipt retains both exact source hashes, graph pins, the canonical JSON
bounds hash, the function delta and both conditional analyses. This bounds hash
is over canonical JSON data, unlike inspect's hash of the original bounds file.

`upper_work_delta` is candidate upper bound minus original upper bound and is
present only when both analyses are supported. It is not a difference in actual
work, a speed measurement, or an equivalence verdict. Unsupported shapes remain
`UNKNOWN`, including their function-relative locations. The receipt explicitly
keeps semantic checking, execution admission and equivalence checking false.
The API has no evaluator dispatch, filesystem effects or automatic optimizer.
Seven data-only tests cover the arithmetic delta, equal bounds for different
values, source/graph/bounds pins, draft refusals, unknown shapes, missing entry,
input preservation and the two existing resource-aware edit specimens.

The separate data-only command is:

```
python tools/record_work_compare.py original.bagaev candidate.bagaev --form 5 --bounds bounds.json --base BASE_PROGRAM_SHA256 --target TARGET_PROGRAM_SHA256 --output comparison.json
```

Form5 and both graph pins are mandatory. Input files use the existing bounded
regular-file reader, strict JSON parsing and exclusive output writer. Existing
outputs are never replaced. The comparison includes both canonical-bound and
raw bounds-file hashes, so formatting differences remain distinguishable.
The stdout receipt pins the output bytes; refusals return a JSON error and
exit status 2. `UNKNOWN` is a successful analysis result without a numeric
difference, not a successful execution. Five CLI tests cover successful
receipts, usage/pins, malformed bounds, symlinks, existing-output preservation
and unknown analysis. The existing record-text command is unchanged.

The work-limit counterexample also includes exact readable
[original](../examples/probes/record-work-helper-limit/Direct.bagaev) and
[candidate](../examples/probes/record-work-helper-limit/Extracted.bagaev) sources,
[empty entry bounds](../examples/probes/record-work-helper-limit/bounds.json),
and a [complete comparison artifact](../examples/probes/record-work-helper-limit/comparison.json).
The source graphs were matched to the two previously captured invocations before
reusing their execution evidence. No new execution is implied by this source
bridge. Repeating the data-only command with the artifact's base/target pins
produces the same output bytes and upper-bound delta 1024. Three tests pin the
graphs, complete artifact and stale-target refusal after changing the loop count.

### Conditional Text comparison work

Text entry bounds use exactly `{"type":"Text","bytes":B}` with an integer
maximum 0–1024. They still require separately valid Text arguments within the
existing scalar limit. Explicit `text.eq` and `text.lt` charge their node, both
operand bounds and the sum of both UTF-8 byte maxima. They do not normalize
Unicode or overload scalar equality. Existing `text.bytes`/`text.scalars` work
analysis remains unsupported in this slice.

Six [frozen Text cases](../examples/probes/record-work-text-comparison/cases.json)
matched complete own-reference outputs: non-normalized Unicode, NUL ordering,
short/empty inputs within larger maxima, a Text helper and a bulk-charge refusal.
The last refuses at work63586 although its upper bound is65634: a bulk charge
that would exceed65536 is rejected as a whole. Neither a bound nor the remaining
budget establishes execution success. Five data tests cover these observations,
shape/type refusals and branch/loop composition; existing unknown-location
fixtures remain unchanged. No native or model execution or timing measurement
was performed for this analyzer extension.

`list.at` can now supply a Text shape to that comparison: its charge is one
entry plus the list and index operand bounds; the selected item's byte maximum
is the smaller of1024 and the whole-list byte maximum. This deliberately does
not prove the index is valid or that any element exists. Five
[frozen index cases](../examples/probes/record-work-text-index/cases.json) matched
complete own-reference outputs, including empty/negative-index refusals at
work4 and the nested comparison pointer. Four data tests cover the byte cap,
argument types, arity and index-expression costs. This extends conditional
analysis only; runtime, scalar-overload and admission rules are unchanged.

### Declared maxima must actually apply

The [assumption controls](../examples/probes/record-work-assumptions/cases.json)
reuse two earlier complete observations with exactly matched invocation graphs
and arguments. Declaring zero-byte bounds for actual nonempty Text arguments
produces upper3 while the earlier valid invocation used work7. Declaring zero
total list bytes for the indexing example produces upper9 while its captured
invocation used work11. Both inputs violate the declared maxima; these are
inapplicable bounds, not counterexamples to a bound under its prerequisites.
Corrected maxima give upper7 and14 respectively. Neither inspect nor compare
validates actual invocation arguments against these declarations. Two data tests
preserve these controls and their prior-observation provenance; no new program
execution or admission mechanism was added.

The optional pure [argument-dimension observer](../src/bagaev_record_argument_dimensions.py)
compares actual name-mapped Int64, Bool, Text and TextList values with declared
maxima. It returns `WITHIN` or `EXCEEDS` for supported valid values,
`INVALID_ARGUMENT` for invalid tags/value limits, and `UNKNOWN` for unsupported
shapes or mismatched maps. All declarations are checked before values, in sorted
name order. Without declaration maps, nominal records/lists remain unsupported.

Successful observations retain canonical bounds/argument hashes and numeric
dimension rows, without returning the argument values. Text bytes/scalars,
per-item limits and whole-list count/bytes follow the existing value profile.
`WITHIN` establishes only these dimensions: it does not check a source program,
match a function signature, prove index/overflow safety or admit execution.
Semantic checking and execution admission remain false. Eight data tests cover
boundary values, the two applicability controls, invalid/unsupported shapes,
identity stability and input preservation; no program execution was performed.

The pure [source observation API](../src/bagaev_record_work_observation.py) binds
these two separate facts to an exact form5 graph pin and source hash. It maps a
positional argument array using the declared entry parameter order, rejects
bounds/name/type/count mismatches, then returns both conditional work analysis
and actual-dimension observation. A `WITHIN` dimension result can coexist with
`UNKNOWN` work; unsupported argument shapes remain distinct from supported work.
There is no combined success/admission verdict. Full program semantics and
execution permission remain separate requirements. Seven data tests cover
violated/applicable maxima, parameter order, invalid/unsupported observations,
stale pins, missing entry and unchanged graph identity under comments.

A separate bounded command writes that observation without executing source:

```
python tools/record_work_observe.py source.bagaev --form 5 --program PROGRAM_SHA256 --bounds bounds.json --arguments arguments.json --output observation.json
```

The arguments file is a positional JSON array. Existing bounded regular-file
reads, strict JSON parsing and exclusive output rules apply. Raw bounds and
arguments file hashes are retained in addition to the nested canonical named-map
identities. A successful tool receipt means an observation file was written;
`EXCEEDS`, `INVALID_ARGUMENT` and `UNKNOWN` remain explicit data outcomes, not
execution success. Malformed transport/binding or stale pins return JSON error
with exit2 and no output. Five transport tests cover these distinctions, exact
output identity, wrong usage, symlinks and preservation of existing output.

The finite `examples/probes/record-work-observe/cases.json` fixture freezes four
complete observation envelopes and exact output hashes: valid two-byte Text
inputs within maxima, the same inputs exceeding zero maxima, a wrong argument
type, and a supported input with unsupported work analysis. Two data tests
check graph identities and complete CLI output/receipts. Four serial standalone
CLI invocations also matched these frozen envelopes. None executes the source
program. The conditional upper bound of3 in the exceeded case is inapplicable
to its actual inputs; the dimension result preserves that fact. An output file
and successful transport receipt are never a combined semantic acceptance.

The dimension observer additionally accepts keyword-only `records` and `lists`
declaration maps for named lists of scalar-only records. The source observation
API supplies its pinned declarations. Supported lists have capacity0..16 and
records have1..8 exact Int64/Bool fields; nested, optional, Text and standalone
record argument shapes remain `UNKNOWN`. An actual length above the type's
capacity or an invalid record field set/scalar is `INVALID_ARGUMENT`; valid
values above the supplied item maximum are `EXCEEDS`. Integer fields reject
booleans and out-of-range values. Declaration shapes precede actual values.

Nominal dimension rows retain list type, element type, capacity and actual item
count. Successful observations also retain a canonical declaration-map hash.
Existing primitive observation envelopes are unchanged. Seven focused data
tests cover applicability, exact field sets, scalar limits, unsupported shapes,
precedence, pinned source binding and input preservation; the prior22 related
tests, including complete frozen primitive outputs, also pass. No program is
executed and no result grants semantic or execution admission.
