# Equal-output allocation observations

Observed 2026-10-06 14:51 UTC. Same-maintainer data readback passed for all 192 retained calls; 309 normal/instrumented pairs had zero whole-call mismatches. No timers ran in this unit.

| Case | Path | alloc | realloc | dealloc | Peak above prepared baseline (bytes) |
|---|---|---:|---:|---:|---:|
| REQUEST-TYPE | ordinary | 3 | 1 | 3 | 288 |
| REQUEST-TYPE | reference | 110 | 82 | 110 | 3070 |
| REQUEST-TYPE | native | 26 | 5 | 26 | 858 |
| EMPTY-0 | ordinary | 34 | 49 | 34 | 1569 |
| EMPTY-0 | reference | 199 | 136 | 199 | 4992 |
| EMPTY-0 | native | 73 | 44 | 73 | 3237 |
| REV-0 | ordinary | 219 | 178 | 219 | 7607 |
| REV-0 | reference | 935 | 399 | 935 | 16414 |
| REV-0 | native | 372 | 151 | 372 | 17065 |
| REV-3 | ordinary | 219 | 178 | 219 | 7607 |
| REV-3 | reference | 952 | 400 | 952 | 16559 |
| REV-3 | native | 373 | 151 | 373 | 17065 |

Preparation retains 0 additional requested bytes for ordinary mode, 151372 for reference, and 3821636 for native. Preparation peaks are respectively 0, 589064 and 3821636 bytes above the input/observer baseline. Zero additional ordinary preparation does not mean zero process memory.

The native REV-3 stage-1 path accounts for 346 of 373 allocations; reference projection/cleanup stage 2 adds 261 of 952 allocations. Shared encoding stage 3 adds one allocation per path. Stages include owner cleanup, so live deltas may be negative. These are allocation counts, not time fractions or proof of the previous timing gap.

All outputs matched canonical bytes. Dropping each output restored the prepared baseline; dropping Session restored the input/observer baseline. This finite check does not prove absence of all leaks.

Counter records requested bytes after completed System operations. It excludes allocator-internal realloc overlap, fragmentation, RSS, stack/code pages and native arena suballocations. Optimizer allocation elision and instrumentation limit generalization. Peaks are not additive. All sixteen repetitions per group, including first use, are retained.

## Reproduction surfaces

The [frozen plan](../examples/probes/ordinary-catalog/allocation/plan.md), [all 192 rows](../examples/probes/ordinary-catalog/allocation/results.json), and [309 whole-call pairs](../examples/probes/ordinary-catalog/allocation/qualification.json) are data, not a grant to execute arbitrary code.

The [driver template](../tests/probes/backend/catalog_allocation_driver.rs.in) uses the same module and source substitutions as the equal-output driver, plus ALLOCATION_DIR for examples/probes/ordinary-catalog/allocation. Compile with edition2021, warnings denied and opt-level2, linked only to the separately admitted exact /10 catalogue kernel. Invoke MODE normal|profiled qualify|collect REQUEST EXPECTED. qualify performs one checked call; collect retains sixteen. It emits raw snapshots only after restoring both lifecycle baselines. Obtain inputs through the existing catalog_equal_wire.py helper.

The unchanged System counter and direct/phase toy sources are adjacent. Direct toy expects live32,48,96,24,0 and peak96. Phase toy expects live0,64,128,0 and phase peaks64,192,128. Replacing peak fetch_max with store yields the normal wrong phase peak144, which must be detected. The failed-resize check is a modeled bookkeeping control, not a forced operating-system allocation failure. No allocation-failure or process-tree memory guarantee follows.

Stage1 covers evaluation/export (including parsing); stage2 covers projection and owner cleanup, or only parsed-input cleanup for ordinary Rust; stage3 covers encoding and Response destruction. Output destruction is outside the three stages and adds one deallocation to the whole-call total. The unsafe native preconditions from call_boundary.rs remain mandatory. CI validates documentation; bounded native observations are separate evidence.

The [failure/recovery lifecycle extension](probe-failure-allocation-lifecycle.md) checks diagnostic ownership, subsequent success and retained outputs after Session destruction.
