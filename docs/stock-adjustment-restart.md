# Stock adjustment across three processes

This extends the [fixed stock-adjustment example](stock-adjustment.md) from
object reconstruction to a selected process boundary. The existing source,
A–E inputs, business receipts and fixture manifest remain unchanged.

The [serial driver](../tests/probes/stock_adjustment_restart_checks.py) accepts
the same explicit reader/reference/hash arguments and a fresh output directory
as the earlier example. Its [stage process](../tests/probes/stock_adjustment_restart_child.py)
is reviewed source, not a background service. Execution still requires a
separately admitted bounded host profile; hashes alone do not grant permission.

## Frozen sequence

1. Execute A–D, then E. A controlled connection exits immediately after E's
   dirty COMMIT returns, before the bridge returns a response. The selected exit
   code is 87 and no stage-complete marker exists. The parent independently reads
   G5/R10, quantity7 and three mutations. Five application evaluations occurred.
2. A fresh process reconstructs the same source/policy/clock binding. With
   current observation denied, an E retry gives AccessDenied. With observation
   allowed but submit/write denied, E returns its retained Applied/R10, A its
   Declined/R7 and a new F submit is denied. The complete image is unchanged and
   no application evaluation occurs during that recovery. Explicitly enabling
   the synthetic host's current submit/write conditions permits existing F:
   expected revision10 and delta1 produce Applied/R11, quantity8, G6 and four
   mutations. F is the only new application evaluation.
3. A third process, with writes disabled, reads F and old E/A. It performs no
   application evaluation and leaves the exact G6/digest/image unchanged.

The F expectation is fixed independently: key sku1, note kept and quantity8 at
revision11, bound to F's existing complete intent. Old E remains an R10 fact
although the current application revision is R11. No hidden new operation ID or
automatic re-execution is used to recover a lost result.

## Actual observations and limits

All three sequential processes passed: 52, 83 and 60 reader/reference calls,
respectively, with five, one and zero application evaluations. Parent checks
compare the stored digest across process boundaries and preserve the
executable-selection file and stage source bytes. These 195 calls include source/value
checking, not 195 independent business cases. No generated native application
kernel or model was invoked.

The same sequence also passed on a clean subset with 85 original dependency
blobs verified against the pre-fix main commit and only the two new drivers
added. It therefore does not depend on the separate final-CAS fixes. That
repetition is the same lifecycle coverage, not another independent workload.

This is one selected post-COMMIT process exit followed by ordinary process
restart. It is not power loss, arbitrary interruption coverage, a machine reboot,
new clock-domain activation or production authorization. Current conditions are
explicit synthetic host inputs and are never restored as rights from the image.
Trusted filesystem, SQLite, selected executable and single-writer assumptions
remain. No timing, memory, cost or availability claim is made.

The complementary [pre-COMMIT interruption](stock-adjustment-rollback.md)
checks rollback and an explicit retry that can repeat pure evaluation. It keeps
durable receipt recovery distinct from exactly-once physical execution.

[Cancellation after either cut](stock-adjustment-cancel.md) separately checks
that a pending uncommitted intent can be cancelled while an already Applied
adjustment is reported honestly and never undone.
