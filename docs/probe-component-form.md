# A readable form for the working component

The [component source](probe-component-source.md) now has a small readable view.
It reconstructs the same typed source and feeds the existing checked computation,
[change admission](probe-component-change.md) and continuation example. It adds
no evaluator, effects, permissions or production runtime.

The first programme can be written as:

```text
bagaev component-form/1;
component CatalogEntry operation reindex {
  record EntryId { value: Text };
  record CatalogRevision { value: Int64 };
  record Entry { id: EntryId, indexed: TextList, manual: TextList };
  record ReindexRequest { base: CatalogRevision, id: EntryId, tags: TextList };

  state Entry identity id;
  request ReindexRequest identity id revision base: CatalogRevision;
  replace indexed;
  entry main;

  fn main(state: Entry, request: ReindexRequest) -> Entry =
    Entry { id: state.id, indexed: list.unique(request.tags), manual: state.manual };
}
```

This names ordinary types, one state/request boundary and one pure function.
The function constructs a new Entry with unique indexed tags. Identity and manual
tags are preserved; the receiving component enforces its declared frame before
simulated commit. The source cannot grant write rights by declaring an operation.

The [second source](../examples/probes/component-form/S2.bagaev) extracts
`normalize(tags: TextList) -> TextList` and calls it from main. Its canonical
component/core identities are exactly those already qualified in the component
example. Changing the editable notation does not silently rebind an old run.

## Pure codec and deliberate scope

`src/bagaev_component_form.py` exports `decode(source)` and `encode(value)`.
Decode returns component-source/1 data with an embedded typed-record/10 programme.
Encode produces canonical UTF-8 text for its supported subset. Neither method
checks admission, invokes a compiler, evaluates host source or touches files.
The existing component/core reader remains the semantic checker.

This first grammar supports required record fields, typed function signatures,
parameter references, chained field access, named pure calls, list.unique and
named record construction. Named fields lower to the existing record's canonical
sorted positional order, independent of textual field order. Declaration order
may vary. Canonical output sorts records/fields/functions while preserving
parameter, argument and replacement-list order.

It is a bounded readable view, not the full proposed language grammar. Numeric
or text literals, comments, quoted identifiers, imports, macros, interpolation,
general expression syntax and nonempty list/variant declarations are outside it.
Existing JSON source remains available for supported core constructs outside this
view. Encoding refuses unsupported or extra data rather than dropping it. No
L2 semantics change or host-language eval/AST fallback is used.

The existing generic JSON/S-expression/familiar codecs also preserved the same
two components and nominal-error input across nine checker observations. Their
generic dictionary/legacy-constructor output is not presented as this readable
notation or evidence of model/token efficiency.

## Bounds and failures

Source is UTF-8 with no BOM, at most1MiB. Identifiers are ASCII letters followed
by letters/digits/underscore. After the fixed version header there are at most
32768 tokens. Expression recursion and reconstructed data depth are bounded by128,
with at most10000 reconstructed values. No partial reconstructed source is returned.

FormError retains a code: FORM_VERSION, FORM_BOUNDS, FORM_SYNTAX,
FORM_DUPLICATE, FORM_SHAPE, FORM_REFERENCE, FORM_RECORD_FIELDS or FORM_PROFILE.
Resource/encoding/version/complete lexing precede sequential grammar checking;
required clauses precede record lowering and reconstructed bounds. Unknown named
construction cannot be lowered. Unknown ordinary field/function/type references
remain for the actual semantic checker where this view can represent them.
Encoding checks representability and cycles before producing text. No repair,
error-location recovery or automatic source pinning is claimed.

## Verified path and reproduction

Thirteen pre-parser literal reconstruction/refusal cases cover both handwritten
sources, reordered constructor fields, nominal confusion, duplicates, missing
clauses/fields, unknown record/version and host-code tokens. Eight additional
encoding/resource guards cover UTF-8/BOM, byte/token/depth limits, unsupported
expressions, extra fields and cycles. Successful reconstruction is compared with
complete previously qualified component data/checker wires. These are not thirteen
new independent runtime semantics cases.

The connected path starts from the handwritten readable sources, requires the
independently pinned canonical component/core identities, invokes the actual
component checker and runs the unchanged seventeen world/receipt expectations.
Existing evidence is reused with its original timestamp; new application calls
are recorded separately. State, rights and recovery remain explicitly simulated.

In an independently approved bounded profile, with reviewed executable hashes:

```
python tests/probes/component_form_checks.py --reader /absolute/component-reader --reader-sha256 RETAINED_READER_SHA --output /absolute/new-form-checks
python tests/probes/component_form_cycle.py --matcher /absolute/matcher --matcher-sha256 RETAINED_MATCHER_SHA --reader /absolute/component-reader --reader-sha256 RETAINED_READER_SHA --reference /absolute/record-reference --reference-sha256 RETAINED_REFERENCE_SHA --output /absolute/new-form-cycle
```

Output parents must exist and outputs must be new. No model call, performance
measurement, native compilation or authority expansion follows from decoding a
form. Same-maintainer review and static CI do not establish full-language or
production acceptance.
