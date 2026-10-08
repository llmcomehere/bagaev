# Separate catalog-application/3 contract

Retain catalog-application/2 unchanged. New interface /3 expands entries from four
to sixteen; keep behavior revisions0..3, identifier/title/tag/date bounds, seven
ordered refusal gates, manual-origin behavior, list/set revisions and missing-date
ordering identical. The returned state preserves id order; the ID view follows
date/id ordering. This remains a pure returned value, not a durable store.

Use literal cases for sixteen entries, missing dates/zero dates, revision0 list
preservation, revision3 sets, selected reindex/manual preservation, empty clear,
capacity17, duplicate/order/origin/date and shape-before-date refusals. Freeze
complete expected responses before implementation. A separate ordinary Python
reference changes only interface/capacity constants. No performance or universal
runtime-totality claim; typed profile11 retains its work limit.
