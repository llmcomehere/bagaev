# Sixteen-entry pure catalogue

The separate `catalog-application/3` interface accepts up to sixteen entries.
[Readable source](../examples/probes/catalog-wide/Catalog.bagaev) uses explicit
record-form/5 and lowers to typed-record/11. The original application/2, its
four-entry limit, source and 99-case oracle remain unchanged.

## Contract

Only the interface tag and entry capacity change from [application/2](application.md).
Behavior revisions 0–3, identifier/title/tag/date bounds, ordered refusal gates,
manual-origin preservation and missing-date ordering retain their definitions.
State entries retain ID order. The separate ID view sorts by date and ID, placing
missing dates last in revision 3 and first in earlier revisions. An absent date
is distinct from zero; explicit null remains invalid.

The graph contains guarded sixteen-step reads and immutable appends. Its view
selects the next entry after the previously selected entry, keeping a typed
optional candidate and accumulator. Unique IDs provide a total ordering.
No membership search or repeated whole-list rank calculation is needed for each
candidate. This is an algorithm description, not a speed measurement.

This is a pure returned value, with no durable storage, native ABI or component
ownership extension. Profile 11's work and shape limits remain in force: a
schema-valid request is not promised to fit every runtime budget. No limits or
execution controls are raised by this example. Focused edits require [explicit form5 selection](wide-function-editing.md);
other diagnostic, whole-program draft and formatting tools retain their version limits.

## Evidence and reproduction

Fifteen complete literal requests and expected responses were frozen before the
implementation. They cover sixteen entries, list/set behavior, reindexing the
last entry, clearing indexed tags while preserving manual tags, empty state,
zero versus missing dates, capacity seventeen, and validation refusal ordering.
Both the ordinary Python reference and typed reference matched all fifteen.

The portable check additionally translates only the interface tag in 98 old
cases and compares their unchanged complete expected responses. It excludes the
old ENTRIES-LIMIT case because five entries deliberately have different semantics
in the new contract. An initial attempt to reuse that old capacity expectation
failed in the ordinary reference; the original failure was retained. Neither
old oracle nor new literal expectations were changed.

After independent execution admission, run `tests/probes/catalog_wide_checks.py`
with `--reference PATH --reference-sha256 HASH --output NEW_DIRECTORY` under an
approved bounded execution profile. The executable must be a reviewed profile11
reference; a matching hash alone does not authorize execution. This check made
113 typed-reference calls and 113 ordinary-reference comparisons. These are
same-maintainer bounded conformance observations, not independent reproduction,
performance, model-cost, adoption or continuous-service measurements.

Preparation remains inert: use `tools/record_text.py prepare SOURCE --form 5
--arguments ARGUMENT_ARRAY --output NEW_FILE`, where the array contains one
application/3 request. It writes invocation/11 without launching a reference.
