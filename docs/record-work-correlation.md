# Conditional work without mixing mutually exclusive list shapes

This optional data-only analysis addresses the bounded OE17 case in
[operational semantics](operational-semantics.md). It leaves the existing
`bagaev_record_work.analyze` API and its conservative results unchanged.

`bagaev_record_work_correlation.analyze` takes the same expression, argument
shape bounds and optional definitions. It first runs the original analyzer.
Any original UNKNOWN result stays UNKNOWN, including unsupported arms beneath
a literal condition. A successful result retains `semantic_check: false`,
`execution_admission: false` and `requires_checked_program: true`.

For one selected root shape, `U(if c a b)`, where U is list.unique,
list.increasing or list.len, the analyzer also checks `if c U(a) U(b)` as an
analysis tree. It never changes the user's program or executes that tree.
Purity and the existing logical charge rules allow the condition to be charged
once and the branch-specific list charge to remain with its own branch.
Both arms are analyzed; there is no constant folding or predicate inference.

For example, let xs have at most64 items and0 aggregate UTF-8 bytes, and ys at
most1 item and1024 aggregate bytes. With a Bool condition, the original bound
for list.unique(if c xs ys) is135172: it combines64 items with1024 bytes.
The refined bound is4100, from4 entered expressions plus the greater of4096
and2049 branch charges. This is a derived conditional bound, not a measured
execution result or proof that arbitrary supplied arguments fit these maxima.

Supported results use schema `bagaev-record-work-correlation/1`, include
`baseline_upper_work`, and identify `refinement` as `root-unary-if` or `none`.
UNKNOWN results have no numeric bound. An unselected root retains the baseline.
If analysis of the distributed tree fails its unchanged budgets or produces a
larger bound, the result retains the original supported bound. Distribution
adds one statically visited node; no analysis limit is increased to accommodate
it. This wrapper performs at most two bounded analyzer calls, not one, and no
performance or total-memory improvement is claimed.

The refinement does not propagate correlations through arbitrary operators,
helpers, multiple branches or loops. The original source must still be checked,
and actual arguments must satisfy the declared bounds. A bound below65536
concerns logical work only; it grants no execution admission and establishes
neither successful value computation nor latency, RSS or model-cost benefit.
An ordinary-language baseline may use the same refinement.

Literal regression expectations are in
[test_record_work_correlation.py](../tests/probes/test_record_work_correlation.py).
Their presence is not execution evidence. The controls cover differing shapes,
unchanged bounds, nonzero branch computation, original refusals, input
preservation and fallback when refinement cannot improve the supported bound.
