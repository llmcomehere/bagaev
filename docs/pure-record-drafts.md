# Detached pure function changes

`bagaev_record_draft.draft` compares two readable record-form/1 sources with
explicit canonical typed-program SHA-256 base and target pins. A whitespace-only
rewrite does not change a program pin. Pins guard against stale or substituted
program data; they are not signatures or authentication.

Existing function parameter/result signatures and the entire type/entry schema
must remain unchanged. Functions cannot be removed. Bodies can be replaced and
helpers added. The returned `bagaev-record-draft/1` contains a detached candidate,
sorted add/replace names, and false semantic-check/admission flags. No Store,
receiver, persistence, source selection or execution is involved.

```console
python3 -B tools/record_draft.py original.bagaev candidate.bagaev --base BASE_SHA256 --target TARGET_SHA256 --output draft.json
```

Pins refer to the compact UTF-8 JSON typed program with sorted object keys,
unescaped Unicode and no extra whitespace, not raw source bytes. The API's
`digest` computes that representation's SHA-256. Use independently selected
expected pins; copying whatever a candidate announces defeats substitution checks.

The CLI reuses regular-file, size and exclusive-output checks. It never launches
a checker. Requiring unchanged signatures does not establish type correctness or
business correctness. The finite example extracts `plus_one` while retaining
result 8 for argument 7. Another structurally compatible draft returns 0: the
separately selected reference and expected result detect that business error.

The portable probe covers two drafts, eight explicit refusals, three CLI calls
and three reference invocations. It also checks detached output ownership and
input/existing-output preservation. Draft success is neither approval to apply
nor evidence of performance or production reliability.

## Explicit form5 whole-source drafts

`record_draft.py ORIGINAL CANDIDATE --form 5 --base BASE --target TARGET
--output NEW_FILE` selects `bagaev_record_wide_draft.draft` for profile11.
The default remains form1 and explicit form4 is unchanged. The wider packet uses
`bagaev-record-draft/2`, the same version as focused form5 data, with sorted
`delta.add` and `delta.replace` arrays. It is still a detached candidate.

This route permits adding helpers and changing multiple existing bodies, while
fixing entry, type declarations, all existing parameter/result signatures and
the presence of every old function. Stale base/target pins and no-op/whitespace-only
changes are refused. Existing codec bounds apply, and CLI output remains bounded
to1MiB with no overwrite. The original base is checked before parsing a candidate.

The focused source exporter deliberately refuses helper additions and multiple
body replacements, even when their whole-source draft is valid. That exporter
has a narrower contract. The original candidate source is already available for
separately selected preparation and checking. A draft cannot approve itself.

Four portable tests cover literal helper-extraction graphs, sorted multiple-body
deltas, detached data, pin/scope/signature/no-op refusals and file preservation.
Old form1/form4 packet hashes and receipts are unchanged. A helper returning the
wrong business value is deliberately accepted structurally to show the boundary:
no program or reference was executed in this data-only slice, and semantic,
business and runtime acceptance remain separate.
