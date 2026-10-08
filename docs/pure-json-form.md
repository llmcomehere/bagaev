# A readable complete bounded catalogue

Explicit record-form/4 closes representation gaps for the existing catalogue
program. [Catalog.bagaev](../examples/probes/pure-json-form/Catalog.bagaev) contains
all 24 functions in readable syntax. It lowers exactly to the accepted catalogue
graph, with only its compatible typed-record schema tag changed from8 to10.
Application rules and the frozen 99-case oracle are unchanged.

## Existing operations, explicit spellings

The form adds `json.kind`, `json.len`, `json.int`, `json.is_text`, `json.at`,
`json.text_or`, `json.field`, `text.byte_at`, `int.eq`, `int.le` and `bool.not`.
These represent existing typed-core operations. `json.field(value, "key")` has a
literal metadata key limited to64 UTF-8 bytes; a computed key is refused.
`record.field(value, "name")` represents projection from a computed record,
without introducing mutable fields or reflection. The core checks operand types.

JSON views are supplied argument data. These operations do not read files,
contact services or parse arbitrary source as code. `json.kind` distinguishes
missing from null; optional omitted fields preserve the existing distinction.
Select `tools/record_text.py ... --form 4` explicitly. Defaults, earlier forms and
fixed diagnostic/draft interfaces remain unchanged.

## What the catalogue does

The pure program validates the existing bounded application request, applies its
behavior revision's tag-list/set rules, preserves manual-origin tags during
reindexing, and produces the specified ID ordering including absent dates.
It returns a complete success or application-refusal payload inside Result.
It does not itself create a durable Store or operation receipt. Its four-entry
application bound is unchanged; this is not an unrestricted production catalogue.

## Evidence and use

Use the [preparation command](pure-record-form.md#prepare-explicit-arguments-for-execution)
with --form4 and an argument array containing one catalog-application/2 request.
A separately reviewed typed-record/10 reference can execute the resulting input.
The converter never launches it.

The exact readable graph passed all99 pre-existing literal requests/responses,
plus four actual chain steps with three predecessor-state feeds:103 reference
calls. The comparison checks the complete Result payload and separates business
refusal from language failure. Portable checks also cover four CLI operations,
literal-key and version refusals. These are same-maintainer conformance runs,
not new independent cases, native AOT measurements or proof of model preference.

An initial encoding exposed the old form's inability to spell projection from a
computed record. The new record.field spelling resolves that representation gap;
no graph or expected response was rewritten. Original refusal evidence was kept.

For explicit form4 syntax diagnostics and exact-base helper extraction, see the [catalogue change workflow](catalog-edit-workflow.md).

A [formatted view](record-formatting.md) adds line breaks without changing the catalogue graph or canonical program identity.

A separately selected [pure profile11 / record-form5](record-wide-profile.md) admits record-list capacities up to16; it does not change this catalogue contract.
