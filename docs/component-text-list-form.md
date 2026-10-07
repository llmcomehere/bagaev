# Readable Text and TextList operations

Explicit component-form/5 adds fixed pure Text/TextList calls over the existing
typed-record/10 core. It still produces component-source/2. Earlier form codecs
remain unchanged. This is an expression vocabulary extension, not a new host
library loader, collection implementation or backend.

For example, a helper can express a normalized tag list directly:

```text
fn normalized(tags: TextList) -> TextList =
  list.unique(list.push(tags, "new"));
```

The original list remains immutable. The result is sorted and unique; the name
list.unique must not be read as stable-order deduplication.

## Fixed calls

| Call | Arguments | Result |
| --- | --- | --- |
| list.text | zero to 64 Text expressions | TextList |
| list.len | TextList | Int64 |
| list.at | TextList, Int64 index | Text |
| list.contains | TextList, Text | Bool |
| list.increasing | TextList | Bool |
| list.unique | TextList | TextList |
| list.push | TextList, Text | TextList |
| text.bytes | Text | Int64 |
| text.scalars | Text | Int64 |
| text.eq | Text, Text | Bool |
| text.lt | Text, Text | Bool |

These names select exact existing core operators. No arbitrary method lookup or
input-selected module is performed. Fixed arities are checked by the codec;
operand types and runtime bounds remain actual core responsibilities. The
constructor accepts at most 64 operands. Known intrinsic names cannot also be
encoded as a variant constructor in form/5; such a source refuses FORM_PROFILE.
Other variant constructors retain their existing representation.

Text byte count and Unicode scalar count differ. Equality is exact and performs
no Unicode normalization; composed and decomposed spellings may compare unequal.
Ordering is the existing scalar order, not locale collation. Scalar count is
not a grapheme, word or model-token count.

TextList preserves input order and duplicates. list.push appends to a new list.
list.increasing tests strict order, so duplicates make it false. list.unique
returns ascending unique values. list.at fails on negative or out-of-range
indices rather than inventing an empty/default value.

## Bounds and meaning

The [existing list contract](probe-typed-list.md) and [append contract](probe-list-push.md)
remain authoritative: at most 64 items, 4096 aggregate UTF-8 bytes, and the existing
per-Text 1024-byte/256-scalar bounds and logical work cap. Operand evaluation and
failure precedence are unchanged. Count/aggregate overflow and bad indexing are
computation failures, not automatically business Decline outcomes.

Let locals, match binders and lazy conditionals keep their prior meaning. Both
branches are still statically checked. Encoding must decode to exactly the same
semantic source; malformed operator kinds and unsupported representation shapes
refuse rather than choosing code dynamically. This slice adds no named record
list declarations, map/filter operation, text concatenation or mutation.

## File conversion and compatibility

Use the fixed bagaev_component_text_list_form API or explicitly select --form 5
in [component_text.py](component-text-cli.md). The converter's default remains
2; forms 3 and 4 remain explicit choices. Conversion continues to report
semantic_check:false and execution_admission:false and never overwrites outputs.

The existing diagnostic, expression-location and detached-edit APIs remain
bound to their documented earlier form versions. They do not silently autodetect
5. Source/2 checking is available after explicit conversion.

## Bounded observations

The [manifest](../examples/probes/component-text-list/manifest.json) binds fourteen
pre-implementation exact graphs and literal results, four form refusals and
four core refusal expectations. Eighteen actual reference invocations checked
those values and indexing, append-count, aggregate-byte and type refusals. One
actual source/policy check passed. Whole work/location records are observations;
they are not claimed as independently frozen full-wire oracles here.

Roundtrips, namespace collision, malformed operator kinds and explicit version
gates passed. Six new file-tool calls and existing default, arithmetic, match
and diagnostic checks passed. The two diagnostic manifests track the updated
shared converter dependency; their form implementations are unchanged.

Portable drivers component_text_list_checks.py, component_text_list_core_checks.py
and component_text_list_cli_checks.py live under tests/probes. The core driver
requires separately reviewed reader/reference paths and hashes and a fresh
output directory. These finite same-maintainer observations are not independent
reproduction, complete language acceptance, a native-backend change or a cost
measurement.

## Use the calls in a component

The [TagBox example](tag-box.md) connects actual TextList business rules to typed
outcomes and retained receipts, including a distinct aggregate-byte failure.

For a fixed literal-count accumulator, see [counted fold](component-fold-form.md).
