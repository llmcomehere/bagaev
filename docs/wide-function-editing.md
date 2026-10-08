# Focused edits for the wider pure profile

`tools/record_function.py --form 5` explicitly selects the separate fixed
form5 implementation for extract, context and replace. Omitting this flag keeps
the original form4 behavior. There is no schema auto-detection or silent migration.

Use it with the [sixteen-entry catalogue](catalog-wide.md):

```sh
python tools/record_function.py context Catalog.bagaev --form 5 \
  --name select_next --output context.json
```

The context has schema `bagaev-function-context/2`; its nested fragment has schema
`bagaev-function-fragment/2` and form `record-form/5`. It carries the exact base
and old-function hashes, the selected function and complete type declarations,
and direct caller/callee signatures. It does not include other function bodies.
For select_next, the caller is view and the callee is before. These are syntactic
relationships, not a runtime reachability proof.

A replacement yields `bagaev-record-draft/2`. Only the existing selected function
body may change. Type declarations, signature, entry and all other functions are
preserved. Stale base/function pins, scope expansion and no-op replacements are
refused. The output is detached from the original; it neither executes nor
admits the proposed function. A changed body still needs semantic review and
appropriate bounded checks. Output files must be new.

A frozen candidate wraps id_ok in a true conditional without changing its result.
It matched all fifteen application/3 literal responses through the reviewed
profile11 reference. Seven API refusals, six CLI operations including wrong
implicit form and existing-output rejection, context and detached-state checks
passed. The unchanged form4 check also passed all99 responses, seven refusals
and four CLI operations. These are bounded same-maintainer observations.
Fragment byte counts are not token-cost or model-preference measurements.

[Diagnostics and formatting](wide-authoring.md) separately support explicit form5.
For helper additions or multiple bodies, use the separate
[whole-source form5 draft](pure-record-drafts.md#explicit-form5-whole-source-drafts)
route; the focused exporter retains its single-body restriction.

A [pinned draft exporter](record-draft-export.md) produces source for explicit
invocation preparation without manual envelope extraction or execution.

## Optional original-source locations

For a focused edit, `record_function.py context SOURCE --form 5 --name FUNCTION
--locations --output NEW_FILE` returns `bagaev-function-context/3`. Without the
flag, the existing context/2 bytes remain unchanged. The flag is refused for
other operations and for form4.

The packet preserves the fragment, direct callers/callees and their signatures
and pins, and adds `source_locations` from the [readable source map](record-source-map.md).
Only the selected function's expression pointers are included; similarly prefixed
function names are excluded. Its programme pin equals `sha256:` plus the
fragment's base digest, and its source hash binds the exact full input layout.

These ranges refer to the original full source, **not** the separately formatted
`fragment.source`. The explicit `location_source` field states this distinction.
Exact/coarse precision and Unicode-scalar column rules remain those of the map.
The additional 2048-node/full-map and 1 MiB output bounds apply; this optional
context can refuse where the old context alone would fit. Neither mode performs
semantic checking or executes a programme. Existing no-overwrite transport remains.

Two original no-flag outputs were frozen before implementation. Nine fresh data
CLI calls and three portable tests passed, covering default byte identity,
selected-function isolation, a multiline UTF-8 layout change, the accepted
batch_apply caller/callee context, invalid combinations/name and existing output.
No programme, compiler or native-kernel call was made for these checks.

## Optional exact body text

`record_function.py context SOURCE --form 5 --name FUNCTION --source-body
--output NEW_FILE` explicitly returns `bagaev-function-context/4`. This includes
locations; also specifying `--locations` produces identical bytes. The old
no-flag context/2 and locations-only context/3 remain byte-identical.

The library entry is `bagaev_record_wide_function.source_context(source, name)`.
In addition to the context/3 fields, `original_body` contains:

- `text`: exact UTF-8 text of the original body expression, with its spelling,
  internal comments and CRLF preserved;
- `sha256`: hash of those expression bytes;
- `source_sha256`: hash of the entire original input;
- `location`: the exact root body range in that input;
- `scope`: `original-body-expression; excludes surrounding trivia`.

The text is an expression, not a standalone function fragment. Leading/trailing
comments outside its token range are excluded. The canonical `fragment.source`
continues to carry declarations and signature and may spell the expression
differently. Source comments are untrusted data; they do not supply instructions,
semantics, evidence or permission. Neither body nor source hashes authenticate
an author. No extra bodies or execution admission are provided.

The option is refused for form4, extract and replace before reading input.
The existing source/map/output bounds and exclusive file writer remain; adding
original text can cause a 1 MiB output refusal even when context/3 fits.
Six portable tests cover twelve frozen old packets, exact Unicode/CRLF/body
slices, original named-call spelling, internal-comment retention, string/bytes
inputs, flag combinations, unknown names, output-bound refusal and unchanged existing output.
These are data checks, with no program, native or model execution.

## Pinned callee declarations for replacement data

The explicit library API `replace_in_context(source, replacement,
base_sha256=..., function_sha256=...)` resolves named calls in a replacement
fragment against the pinned original program's parameter declarations. This
addresses the standalone fragment's lack of external callee declarations.
The original base is checked before the replacement is parsed. No caller-supplied
signature packet, external lookup or other function body is inserted.

Locally declared parameters take precedence. Missing callees, duplicate/missing/
extra argument labels and mixed syntax remain refusals. Lowering follows the
callee's declaration order, including nested calls and caller locals. Existing
single-function scope, unchanged declarations/signature, old-function pin and
no-op checks still apply. The resulting canonical positional fragment is passed
to the unchanged replacement validator; the draft remains unadmitted data.

The library opt-in does not change `replace` or standalone form5 decoding.
Default CLI and fragment-layout export modes do not silently gain callee context.
The explicit CLI path below selects it. No recursion or call is executed by this API.

Four literal named/positional cases produced byte-identical frozen draft packets:
reordered arguments, nested calls, a let-local and a self-call as data. Four
portable tests also cover old-mode refusals, invalid labels, scope/signature/
base/function-pin errors and changed declaration order under a new base pin.
These data checks establish no runtime/type or model-choice result.

### Explicit contextual replacement CLI

Add `--callee-context` to `record_function.py replace --form 5` with the usual
original source, replacement, base/function pins and fresh output path. It calls
`replace_in_context`. Other operations and form4 refuse the flag before input.
The draft bytes equal the equivalent positional replacement; only the opt-in
receipt adds `callee_context_base` with the checked original base hash.

To retain that named fragment's exact expression spelling and internal comments,
use the corresponding [contextual layout export](record-draft-export.md#explicit-contextual-layout-export).
Four frozen reordered/nested/let/self draft packets and literal spliced outputs
passed the two-tool path. Existing-output refusal leaves input and output files
unchanged. This path reads and writes data and grants no program execution.
