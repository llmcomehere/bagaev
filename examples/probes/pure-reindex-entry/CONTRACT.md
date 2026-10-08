# Pure reindex_entry contract

The record-form/1 program returns a new Entry with unchanged id and the exact
manual tag sequence, replacing indexed tags with ascending unique new tags.
No input is mutated. Empty new tags clear indexed only. Unicode normalization
is not performed, so composed and decomposed spellings remain distinct.

The frozen cases cover four complete values and one RR_WORK refusal for costly
normalization. This is pure computation, not persistent catalogue state, source
admission, a transaction or a production/performance claim. Existing TextList
and work budgets apply unchanged. No new runtime operations are introduced.
