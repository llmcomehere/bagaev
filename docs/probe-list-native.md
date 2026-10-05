# Experimental native Text-list profile

This separate LLVM 21 profile implements the typed Text-list contract, including
immutable constructors, indexing, membership, ordering and sorted unique lists.
It preserves existing scalar/Text/Option emitters and schemas. List values use
invocation-lifetime descriptor storage; helper returns do not retain pointers
into dead callee frames. Dynamic storage is a caller-owned arena of 65,536 Text
descriptors, separate from input descriptors. The contract's logical charge
bounds allocation count; it is not elapsed time or a total-memory measurement.

The v3 byte decoder and explicitly unsafe admitted-kernel adapter are separate
from generated computation. Raw outer entry is not supplied. The caller must
supply valid disjoint live buffers and a checked exact-signature kernel; data
validation does not establish arbitrary-pointer safety or execution authority.

Native output uses the prior 32-byte field layout: success 0, overflow 1/reason 9,
work 2/reason 10, admission 3/reason 8, list-bound 4/reason 11, index 5/reason 12 and
internal arena invariant 6/reason 13. Source failures retain consumed work and
source node location. Admission is work 0 with a separate byte-offset domain.

The source library returns detached LLVM bytes and canonical binding records,
including source/artifact pins, exact signature and scratch capacity. It does
not execute them. The additional list_llvm_main.rs CLI offers run and emit-llvm;
the latter returns bagaev-typed-list-llvm/1 data with execution_admission=false.
The earlier run-only list_main.rs remains unchanged.

## Recorded bounded evidence

26 pre-emitter source cases matched 104 complete native outputs (O0/O2 and two
output prefills), preserving input frames and scratch red zones.51 inherited
Text/Option cases matched 204 outputs after schema/frame adaptation, retaining
old output literals. Six concrete mutations produced 24 normal-exit wrong full
outputs and were detected.26 canonical binding/source/artifact pins were
checked. These finite observations do not prove arbitrary-defect freedom.

The detached CLI matched 32 pre-wrapper library references (29 modules and three
source refusals), 32 existing run results and five environment-refusal checks.
Wrapper references are not independent semantic evidence. One negative-test
preparation warning was corrected without changing the candidate or oracle.
Review is a separate same-maintainer pass. No independent reproduction, complete
application acceptance, production isolation or performance advantage is claimed.
