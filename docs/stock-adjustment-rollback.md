# Provisional evaluation before commit

This complements [post-COMMIT restart](stock-adjustment-restart.md) with the
other side of the same stock-adjustment transaction boundary. It uses the
unchanged source, A–E fixture and complete receipt expectations.

The [serial driver](../tests/probes/stock_adjustment_rollback_checks.py) accepts
explicit reader/reference executables, their expected hashes and a fresh output
directory. Its [stage source](../tests/probes/stock_adjustment_rollback_child.py)
runs only under a separately admitted bounded profile.

## Selected sequence

1. Commit A–D. E's pure application evaluation completes, then the process exits
   with code88 immediately after its SQLite UPDATE returns and before COMMIT.
   No stage-complete marker exists. The parent opens the database and checks
   that the complete image equals the saved D image: G4/R9, quantity0, two
   mutations. The interrupted process recorded five application evaluations.
2. A fresh process observes E as Unknown, observes D's retained receipt and
   refuses E submission while current write/submit conditions are denied.
   These actions perform no application evaluation and preserve the image.
   After explicit synthetic permission, retrying the same complete E packet
   evaluates once and returns its frozen Applied/R10 receipt: G5, quantity7,
   three mutations. A subsequent duplicate E returns the receipt without another
   evaluation or generation change.
3. Another process observes E and old A with writes disabled. It performs zero
   application evaluations and preserves the complete G5 image.

## Meaning and observed limits

All stages passed with 52, 60 and 26 reader/reference calls and five, one and
zero application evaluations. The same sequence passed on the base-main
dependency subset used for the post-COMMIT check, without either final-CAS fix.
That repeat is not additional semantic coverage. CI remains static validation;
these runtime results came from the separately admitted experiment.

The two sides are intentionally different. After COMMIT, receipt recovery does
not rerun E. Before COMMIT, E has no durable receipt, and explicit retry can
evaluate it again. Six physical evaluations in this sequence correspond to five
logical intents and three committed state mutations. This is not exactly-once
physical execution and does not make an evaluator with external side effects
safe to retry. The application evaluator here is pure.

One controlled process exit is not arbitrary crash coverage or power-loss
safety. No current authority is reconstructed from storage, no clock domain is
migrated, and no production durability or performance claim is made.
