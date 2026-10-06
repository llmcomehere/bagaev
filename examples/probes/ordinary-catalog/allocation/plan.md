# Equal-output allocation lifecycle and stage accounting plan

Frozen before new allocation observations, 2026-10-06. Follow the accepted equal
application-output boundary from PR81. Do not tune or rewrite its144timing rows.
This new unit records allocator requests, not elapsed time or RSS, and does not
attribute the earlier time gap solely from allocation counts.

Reuse the reviewed System GlobalAlloc counter unchanged. It counts successful
allocation/reallocation/deallocation requests and requested live/peak bytes after
completed operations. Failed realloc leaves the old accounting unchanged. It does
not measure allocator-internal realloc overlap, fragmentation, stack, code pages,
OS memory, CPU cache or whole process-tree resources. Compiler allocation-elision
and instrumentation effects limit generalization; observations are implementation
and build specific. No timers in this unit.

Input/expected bytes and observer storage are prepared before the measured
baseline. Record Session preparation separately: live increase, peak above input
baseline and operation deltas. Native scratch and prepared source remain retained
between calls. Execute16checked repeats for each of the same4fixed cases and
three modes, keeping the first use. At call return require the only retained
per-call allocation to be the owned output buffer; dropping it must restore the
session baseline. After dropping the Session require the input/observer baseline
again. Report output length/capacity separately. No row deletion or warmup.

For attribution, derive an instrumented copy of the exact accepted call
wrapper by inserting stack-stored counter snapshots only. Endpoints:
0before call;1after evaluation/intermediate result;2after projection and releasing
evaluation owners;3after encoding and releasing Response, with only output bytes
alive. Ordinary has no intermediate wire or projection: its second stage is
parsed-input owner cleanup. Reference/native first stage includes request wrapping,
admission/evaluation and language JSON/binary export. Second stage includes
projection/copy and destruction of its argument/result owners. Third stage is
shared application encoding and Response destruction. Names are path-specific,
not claims of identical internal work.

Snapshot/reset bookkeeping allocates nothing. Per-stage allocation deltas are
additive; live peaks are not. Report peaks relative to declared baselines and
recover whole-call peak by maximum of phase peaks, never their sum. Before stage
claims, calibrate against explicit two-allocation/cleanup literals and a normal
wrong-bookkeeping control. Compare complete outputs and whole allocation totals
of unmodified versus instrumented call wrappers on all103prior cases for all
three modes. If the extra snapshots change any observed totals/whole peak, stop
at that diagnostic and do not present the phase numbers as an attribution of the
unmodified wrapper. No silent source/parameter changes to obtain agreement.

Reuse only own admitted exact catalogue kernel and current reviewed modules in
existing bounded serial profiles. No settings, credentials, workflows, external
models, additional executors or new resource limits. Publish only after separate review and exact-head CI.
