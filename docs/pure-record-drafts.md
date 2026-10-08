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
