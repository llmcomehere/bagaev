# Context around a focused function

```console
python3 -B tools/record_function.py context Catalog.bagaev --name id_ok --output context.json
```

The separate `bagaev-function-context/1` packet nests the unchanged focused
fragment and lists direct callers/callees with name, signature and canonical
function SHA-256. Other function bodies are not included. Missing callees are
explicitly `declared:false`, with null signature/hash. The base pin binds the
whole source used to compute this view.

This is direct syntactic context. Calls in unexecuted branches are included.
It is not a runtime trace, type check, test selection, affected-consumer closure
or guarantee that all required context is present. Variant arm labels and binders
are metadata, not calls. No evaluator is launched and admission remains false.

For the accepted catalogue, id_ok has direct callers entry_ok, reindex_ok and
tags_ok, each taking Json and returning Bool. Its own body calls no user-defined
helper. The focused fragment still excludes those caller bodies; retrieve the
full source when their actual behavior is relevant.

Three finite context checks cover the catalogue and a synthetic match whose arm
is named call, plus an unresolved helper in an unexecuted branch. Two CLI calls
and unknown-function refusal passed. An initial supplemental expected caller
list omitted tags_ok; inspection of the existing program confirmed the omission.
Only that expectation was corrected. No runtime or business oracle changed.

## Optional form5 original-body view

For original spelling without all descendant expression locations, use:

```console
python3 -B -S tools/record_function.py context Source.bagaev --form 5 --name batch_apply --source-body --compact --output new-context.json
```

This emits `bagaev-function-context/5`: the same fragment, direct callers/callees,
source/program/function identity pins and exact original-body text/hash/root
range as `--source-body`, omitting only `source_locations`. Its `location_scope`
explicitly says descendant locations are omitted. The root range refers to the
original full input, not the canonical fragment. Internal source comments remain
untrusted data. Semantic checking and execution admission remain false.

Without `--compact`, existing outputs are unchanged. Plain `context` is preferable
when original spelling is unnecessary. Compact mode requires `context --form 5
--source-body` and refuses `--locations`; form4/form6 are not supported by this
projection. Input/output bounds and exclusive output creation remain unchanged.
It first constructs the existing bounded context, so it does not expand accepted
source sizes or establish reduced computation/memory use. Fewer output bytes are
not evidence of fewer tokens, reliable model delivery, better answers or cost.
