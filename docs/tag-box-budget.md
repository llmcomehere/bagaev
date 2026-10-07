# TagBox byte-capacity preflight

This is a separate fixed-source `TagBoxBudget / add_budgeted_tag` example,
using form6/source2 and the unchanged typed-record/10 core. The original
[TagBox](tag-box.md) source and expectations are retained. This is not a live
source migration or an implicit replacement of saved receipts.

The rule order is empty tag, exact existing tag, original list count below 64,
then total original UTF-8 bytes plus new tag bytes at most 4096. Only after these
guards does it append and sort/deduplicate. The byte sum uses a guarded 64-step
[fold](component-fold-form.md). No trimming, case folding or Unicode normalization
is performed. Declines preserve the original order and duplicates.

## Three distinct outcomes

- A small in-bounds addition proposes state and advances the application revision.
- An overflowing byte budget produces the typed `byte-capacity` business decline,
  stores its terminal receipt, and leaves application state/revision unchanged.
- An in-bounds but expensive sort can still return `RR_WORK`, surfaced as
  `OWNER_EVALUATION`. It commits neither a terminal receipt nor a state change.

Do not interpret the preflight as totality. The core's `list.unique` work charge
is `n*n + 2*n*aggregate_bytes`, with a total invocation budget of 65536. A design
that normalized a 16-item, 4096-byte duplicate-heavy list first hit this limit.
The present example deliberately counts original entries and bytes before
normalization. No runtime budget was raised to make a test pass.

## Reproduction

[Source and frozen cases](../examples/probes/tag-box-budget/CONTRACT.md) cover nine
cases: small and Unicode additions, duplicate-heavy and distinct byte overflow,
an exactly fitting but computationally expensive result, distinct and duplicate
count capacity, empty input, and existing input. Two apply, six decline, and one
refuses computation. Fresh handler objects observe each terminal receipt without
another business evaluation. This is not a process-crash or concurrency test.

Run `tests/probes/tag_box_budget_checks.py` using the existing explicit reader
and reference executable/hash arguments and a new absolute output directory.
The driver retains raw native observations and SQLite images. These are bounded
conformance checks, not a performance, adoption or production-reliability claim.
