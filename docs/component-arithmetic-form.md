# Readable arithmetic and local values

The explicit component-form/3 representation adds arithmetic and lexical locals
over the existing typed-record/10 core. It still decodes to component-source/2.
The original component-form/1 and/2 codecs are unchanged and refuse/3. No new
owner, runtime, persistence or execution permission is implied by the new notation.

## Use a value once and give it a name

The complete [stock adjustment](../examples/probes/component-arithmetic/StockAdjustment.bagaev)
uses an AdjustStock request with a delta. Its application body is:

```text
let next = state.quantity + request.delta in
  if next < 0
  then StockOutcome.Decline(StockError { reason: "negative-quantity" })
  else StockOutcome.Propose(Stock { key: state.key, note: state.note, quantity: next })
```

This expresses a calculation followed by a business decision without duplicating
the calculation or editing a JSON expression tree. With quantity 10, deltas 3, -10
and -11 produce proposed quantities 13, 0 and a typed decline respectively.
The receiver still controls whether a proposal becomes an applied state.

## Grammar and meaning

Multiplication binds more tightly than addition/subtraction. Binary arithmetic
associates left: 9-3-2 means (9-3)-2. A single non-chained < comparison binds after
arithmetic. Parentheses select grouping. Existing if/then/else remains lazy.

A let initializer sees outer bindings; its body also sees the new local.
The codec lowers local uses to the existing use node and other identifiers to
arg nodes. The actual core checker still validates parameter references, types,
fresh binding names and depth/work bounds. Shadowing a parameter and referring
to an unbound initializer name do not gain new meanings. Conversion is not
semantic checking.

A minus directly before an integer literal is supported, including Int64 minimum.
General unary negation, division, chained comparisons and mutation are not
added. Arithmetic retains checked Int64 overflow; an overflow is a computation
failure, not an ordinary business decline. A future surface feature must not
silently change those existing semantics.

## Explicit file conversion

After source review and selection of an authorized local profile:

```console
python3 -B tools/component_text.py decode examples/probes/component-arithmetic/StockAdjustment.bagaev --form 3 --output adjustment.json
python3 -B tools/component_text.py encode adjustment.json --form 3 --output adjustment-canonical.bagaev
```

Default form 2 deliberately refuses the form 3 header. Explicit form 3 refuses
form 2 text. Encoding requires an exactly representable source and checks
decode(encode(source)) equality, so a local use cannot silently turn into an
unbound argument. The existing [transport limits and exclusive-output behavior](component-text-cli.md)
still apply. Output observations keep semantic_check:false and
execution_admission:false. Type/source-policy checks use the same separately
reviewed checker as before.

## Bounded evidence

The [fixture manifest](../examples/probes/component-arithmetic/manifest.json)
binds 11 exact source graphs, eight syntax refusals and three literal adjustment
outcomes frozen before codec implementation. Before implementation, the adjustment
example was renamed from a set request to AdjustStock.delta for clarity, without
changing arithmetic expectations. Two explicit version gates preserve old forms.

Supplemental literal checks cover ten helper results, one Int64 overflow and two
existing binding refusals. One actual component-policy check uses the explicit
adjustment policy. The portable component_arithmetic_checks.py driver makes 16
reference invocations and one policy check with separately selected reviewed
executables/hashes. Complete work/location wires are retained as observations;
only the stated values/reasons are independently expected here.

Six supplementary codec controls reject excessive depth and unrepresentable
local/argument or scalar-kind substitutions. Encoding preserves the input data.
Six file-CLI calls check explicit selection and roundtrip, and the unchanged 32-call
default CLI checks still pass. These are representation/compatibility checks,
not a new native backend, model study, production acceptance or performance claim.

## Checked changes

The [explicit edit/3 route](component-arithmetic-edits.md) carries this readable
notation through the existing source/2 compatibility and policy checks. A
checked draft remains separate from qualification and live admission.

## Locate a refused source

The [optional diagnostic command](component-diagnostics.md) reports lexical or
parser-context spans while retaining the existing refusal code. It does not
replace semantic checking or change the converter output.

## Connected authoring route

Follow [write, diagnose and change a component](readable-authoring.md) to connect
this notation, syntax diagnostics and a checked helper extraction.
