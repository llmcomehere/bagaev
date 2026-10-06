# Failure and recovery allocation lifecycle

The [frozen plan](../examples/probes/ordinary-catalog/allocation/failure-plan.md) extends the equal-output boundary with five malformed or oversized byte sequences. It does not change application semantics or native admission. Exact error wording is intentionally not an oracle; each request must return a nonempty owned diagnostic.

One Session per ordinary/reference/native path receives one prior REV-3 success and three cycles of five failure/success pairs. All sixteen successful outputs remain retained. Across 93 attempts there were 48 byte-exact successes and 45 boundary errors. Each error retained only its diagnostic String capacity, and dropping it restored the pre-call live-byte baseline. After destroying Session, all sixteen outputs still matched and accounted for 6656 retained capacity bytes per path. Dropping them restored the input/observer baseline.

[All three summaries](../examples/probes/ordinary-catalog/allocation/failure-results.json) retain diagnostic capacities. Six controls were detected: one wrong expected success and one deliberately retained extra allocation for each path. The extra allocation is safe ordinary Vec code, not a change to the allocator. Initial qualification compilation failed because the unchanged counter's reset_peak was unused under warnings-as-errors. Calling reset_peak before the baseline corrected the harness; no application, oracle or counter change was made. Only the subsequent complete run is reported as passed.

## Reproduction

Use [the driver template](../tests/probes/backend/catalog_failure_lifecycle.rs.in) with BACKEND, CATALOG_DIR, ALLOCATION_DIR and SOURCE substitutions as for the allocation driver. Compile edition2021, warnings denied, opt-level2, and link only the separately admitted exact own /10 kernel. Invoke MODE REQUEST EXPECTED normal, with the existing REV-3 bytes emitted by catalog_equal_wire.py. hold-extra is the deliberate safe negative control and must fail the error-restoration assertion. A byte-modified expected response must fail before the receipt.

The same unsafe exact-kernel obligations apply. This is single-threaded finite requested-byte accounting, not phase attribution for early returns, timing, RSS, operating-system allocation failure or proof of universal leak freedom. Snapshot/reset operations are not a concurrent globally consistent trace. Local bounded execution and documentation CI remain distinct; separate same-maintainer review is not independent reproduction.
