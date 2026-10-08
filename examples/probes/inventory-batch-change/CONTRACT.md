# Focused batch total policy change, synthetic revision 1

A separate development exercise over accepted inventory-batch programme166,
not a new real inventory policy. Preserve the original source,32-case oracle,
entry,types and every function except batch_apply. The new draft limits the sum
of successful requested amounts in one batch to ten, in addition to existing
per-request cap five. Shape validation and existing per-request business failure
precedence remain. A successful individual result that would exceed total ten
instead returns BatchRejected at that step, reason batch-limit and original
stock; later requests are skipped and tentative receipts discarded. Equality
ten succeeds. The total is derived from the previous successful receipts (at
most four), without new fields/types or helper functions.

Freeze full outcomes before modifying source. Preserve every old expected value
except sixteen-long-four, which now rejects at step2 after the first two amounts
of five. Add literal total9/10/11, limit on fourth, business-refusal-before-limit,
shape-before-limit and rollback tests. Do not rewrite original32cases.
Use ordinary independent values, exact programme/function pins, detached one-
function replacement, source export, lossless Json preparation and bounded
reference checks. Stale base/function pins refuse without output. Only after
source review use existing native profiles for finite conformance. No model
calls, durable effects, new execution helper or performance claim.

