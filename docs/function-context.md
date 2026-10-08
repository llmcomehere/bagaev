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
