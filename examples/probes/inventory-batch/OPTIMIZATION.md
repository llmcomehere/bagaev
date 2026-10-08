# Observed resource refusal and invariant-preserving correction

The first reference run stopped at frozen case sixteen-long-four with RR_WORK,
work 65520, in unique_at. Nineteen preceding cases matched; later cases were
NOT_RUN in that attempt. No successful result is claimed for the first design.
The four-request/16-stock oracle and work budget remain unchanged.

Cause: calling the original reserve four times repeats quadratic stock validation
with long SKU comparisons. Once the first reservation succeeds, stock validity
is preserved: it changes no SKU or order, changes exactly one nonnegative
available count by a positive amount no greater than that count, and leaves all
other items unchanged. Therefore later steps reached from BatchCommitted may
reuse that invariant. A prior rejection never reaches another reserve call.

Keep original reserve and the other ten predecessor functions unchanged. Add a
separate helper with a valid-stock precondition, identical request/cap/find/
availability behavior but without redundant stock_ok. The batch loop uses the
original reserve for index zero and the helper only after a preceding success.
Empty-batch validation remains explicit. Never increase the work budget or
silently weaken/replace the frozen full-value expectations. Rerun all 32 cases
from a new result directory and retain the failed attempt.
