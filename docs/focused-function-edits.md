# Change one function without resending the catalogue

The fixed form4 focused API exports one function and the existing type graph as
a readable fragment. Other function bodies are excluded. The fragment's entry
names the selected function; external helper references may remain unresolved
inside that fragment. It is editing material, not a standalone accepted program.

```console
python3 -B tools/record_function.py extract Catalog.bagaev --name id_ok --output fragment.json
```

The JSON packet contains `source`, `base`, `function` and `function_sha256`.
Edit only the readable `source` and save that string as a replacement .bagaev
file. Retain the independently selected base and function pins:

```console
python3 -B tools/record_function.py replace Catalog.bagaev --replacement replacement.bagaev --base BASE_PIN --function-pin FUNCTION_PIN --output draft.json
```

Replacement requires exactly one existing function with the same signature and
complete original type graph. It preserves the original application entry and
all unrelated function definitions. Stale base/function pins, altered types,
extra functions, signature changes and no-op are refused. The candidate is a
detached copy and its computed target identity is returned. That identity is not
an independently approved desired target. Semantic checking and execution
admission remain false; no file is applied, stored or executed automatically.

The catalogue example replaces only id_ok's body with a redundant true branch.
All99 existing literal responses still match through the separately reviewed
reference. The exported source is934bytes versus11713bytes for the full readable
catalogue in this example. This is byte accounting, not token, model or total-cost
measurement. A smaller fragment is useful only if its context is sufficient.

The portable probe covers the full responses, seven scope/pin refusals, four CLI
calls, detached output and unchanged source/input/existing output bytes. For
adding helpers or changing several function bodies together, use the existing
[full detached draft](catalog-edit-workflow.md) instead.

Use [direct caller/callee context](function-context.md) when signatures around a focused fragment are useful; it does not replace semantic checking.

A [pinned draft exporter](record-draft-export.md) produces source for explicit
invocation preparation without manual envelope extraction or execution.
