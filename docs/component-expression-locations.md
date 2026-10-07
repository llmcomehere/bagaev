# Find a semantic expression in readable source

The optional form/4 location helper maps an exact component-source/2 JSON
expression pointer to a source-bound text range. It helps a caller show the
expression named by a typed-core refusal without reconstructing positions from
a canonical JSON file. It does not check types, run the component or identify
a uniquely guilty token.

## Bind both representations

Call `bagaev_component_expression_locations.locate(source, pointer,
source_sha256=..., component_sha256=...)` with:

- the actual form/4 text or UTF-8 bytes;
- the component-root pointer, such as `/program/functions/quantity/body/2/1/2`;
- SHA-256 of the exact readable UTF-8 bytes;
- SHA-256 of the canonical decoded component-source/2 JSON bytes.

The component checker's source_sha256 field is the semantic component digest;
supply it as component_sha256 here. The raw text digest is separate. Neither
hash establishes trust, authority or permission. A pointer supplied by an
unrelated observation does not become valid checker evidence through lookup.

The result has schema component-form-location/1, both identities, the queried
pointer, nullable span, semantic_check:false and execution_admission:false.
Only exact mapped expression pointers return spans. Declaration paths, scalar
fields inside a node and absent expressions return null, without a guessed
nearest ancestor.

Spans are labelled expression. Byte offsets are zero-based and half-open over
UTF-8; line and Unicode-codepoint column numbers are one-based, with LF line
breaks. A range covers the expression's tokens, including its grouping
parentheses where applicable and internal whitespace. Record children follow
canonical field order even when the text uses another order. Match arms retain
authored order. The original decoder's AST and binding meaning are unchanged.

## File tool

After reviewing source and selecting an authorized bounded profile:

```console
python3 -B tools/component_locate.py component.bagaev /program/functions/apply/body --source-sha256 RAW_TEXT_SHA256 --component-sha256 COMPONENT_JSON_SHA256
```

Replace the placeholders with the actual identities. Explicit form/4 conversion
through [component_text.py](component-text-cli.md) produces canonical component
JSON whose output digest supplies the second identity. The location tool reads
one bounded regular nonsymlink file and prints JSON, exiting 0 for a lookup
(including null) or 2 for a refusal. It never rewrites source or loads a checker.

Malformed identities refuse LOCATION_PIN; malformed or over-4096-byte RFC6901
pointers refuse LOCATION_POINTER. The API then performs normal lexical checks,
checks the raw pin, parses/lowers, checks the component pin and looks up the
pointer. Mismatches refuse LOCATION_SOURCE or LOCATION_COMPONENT. Original
FormError codes remain form refusals. The file tool additionally retains the
existing transport/usage refusals. Changing only whitespace still changes the
raw identity, so an old range cannot silently be attached to shifted text.

## Evidence and bounds

Nine pre-implementation observations fixed match/payload/field and unmapped
ranges, including UTF-8 offsets. Seven supplemental exact observations cover
precedence, parentheses and canonical record-field order. Seven pin/pointer
refusals and seven file-tool calls passed. Supplemental checks preserve prior
form graphs/refusals, byte/token limits and stale-text rejection.

One actual typed-record/10 type refusal on the exact component program selected
`stock.quantity` through its emitted pointer and returned work 0. Its other arm
had the incompatible type; the highlighted expression is therefore useful
context, not a claim about the only possible correction. The location helper
itself still performed no semantic checking.

Review identified a resource-amplification risk from repeating an extremely
long function name in every descendant pointer. Paths longer than any admitted
query are now omitted before descendant expansion; a long-identifier control
passed. UTF-8 offsets use one prefix table and a line-start index rather than
re-encoding the entire prefix per node. Existing form byte/token/depth/value
bounds remain. These are finite same-maintainer observations, not independent
reproduction, an all-input proof, production acceptance or a performance result.
