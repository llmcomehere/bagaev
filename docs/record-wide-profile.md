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
upper logical work for a small straight-line expression subset using declared
argument bounds. It requires separately checked program semantics and valid
arguments. Unsupported operations return `UNKNOWN`; a bound above 65,536 means
possible budget exhaustion, not certain failure. It grants no execution admission
and does not measure latency or memory. [Literal tests](../tests/probes/test_record_work.py)
include the sorted-unique example's boundary and the extra charge of negated equality.

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
