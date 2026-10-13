# Cancellation after an interrupted adjustment

Cancellation and [explicit retry](stock-adjustment-rollback.md) are different
choices for the same pending E intent. The
[serial cancellation check](../tests/probes/stock_adjustment_cancel_checks.py)
reuses the unchanged pre/post-COMMIT cut stages and a
[fresh cancellation stage](../tests/probes/stock_adjustment_cancel_child.py).
It takes the same explicit executable/hash and fresh-output arguments. Execution
requires the separately admitted bounded profile.

Before COMMIT, E's evaluation ran but its transaction was not committed. The
fresh process first proves that denied current cancel permission produces
AccessDenied without changing G4/R9, quantity0 or the complete image. Granting
current cancel permission binds the complete E intent to Cancelled/R9. Storage
advances to G5; quantity0 and the two prior mutations stay unchanged. Delayed
submission of E returns that cancellation, and cannot apply the discarded result.

After COMMIT, E is already Applied/R10, quantity7, three mutations at G5. A denied
cancel is still AccessDenied. With current cancellation and observation allowed,
the answer is AlreadyApplied with the exact retained E receipt. The full image
stays unchanged. A delayed E submission returns its original Applied receipt.
Cancellation never undoes the committed stock adjustment.

Neither cancellation stage evaluates the application. Each case ends in another
fresh process observing E with submit/write/cancel disabled, zero evaluations and
an unchanged complete image. Current observation is explicitly allowed; stored
receipts do not supply permission.

Both cases passed. The pre-COMMIT sequence recorded 52/47/12 reader/reference
calls; the post-COMMIT sequence recorded 52/52/13. Each cut process performed
five application evaluations; cancellation and verification performed zero.
The repeated base-main dependency run passed the same cases without either
final-CAS fix. These are two selected cases and repeated controls, not 228
independent business cases. No arbitrary interruption, power-loss, external-effect,
production authorization or performance guarantee follows.
