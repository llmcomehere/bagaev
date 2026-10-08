# Profile11 owned-state handoff and failure edges

This follows the [two-kernel qualification](probe-native-wide-qualification.md)
without changing runtime semantics, ABI, control profiles or execution authority.

## Fresh-process owned-value handoff

Five complete business outcomes were frozen before execution:
normalize sixteen entries, reindex the last entry, clear the first entry,
refuse a target-origin collision, then resume from the last successful state.
Each kernel call occurred in a fresh process. After its exit, the checked owned
wire was decoded and only the prior successful state became the next request.
The refusal did not replace that state.

Twenty native calls (O0/O2 and fills 90/165) and five reference calls agreed on
complete values and work. Each step's wire was identical across all four native
variants. Work was respectively 40,212; 37,665; 37,191; 24,869; and 36,614.
The [literal cases](../examples/probes/native-wide-followthrough/continuation-cases.json)
and [observations](../examples/probes/native-wide-followthrough/continuation-observations.json)
are separate: observations do not define business expectations.

This is pure value handoff across fresh processes. It does not establish durable
storage, transaction recovery, effects, exactly-once behavior or a general
language continuation mechanism.

## Literal language failures

Five separate exact sources exercised:
- Int64 addition overflow and subtraction underflow: work 3, RR_OVERFLOW.
- Index zero of an empty nominal record list: work 3, RR_INDEX.
- Pushing a seventeenth record into capacity sixteen: work 53, RR_RECORD_LIST_ITEMS.
- Four nested loops of sixteen: work 65,536, RR_WORK at the innermost loop root.

Work expectations were frozen from the semantics before execution. For push,
one tick for push, one for the list, 32 for sixteen records and their integers,
two for the new record and integer, plus seventeen copy-charge units give 53.
Nested-loop costs from inside out are 18, 290, 4,642 and 74,274. The consumed
prefix 2 + 14×4,642 + 2 + 290 + 2 + 14×18 equals 65,536. The next expression
at /program/functions/main/body/5/5/5, preorder node 7, refuses before charging.
The other four cases fail at their root, node 1.

Ten data-only emitter calls and five reference calls passed. Five exact LLVM
modules were compiled at O0/O2 using the compiler identity recorded in the
preceding qualification. Twenty actual native calls across those builds and
two fills matched all frozen 32 metadata bytes, including inactive zeros,
work, reason and location. The harness retained source/embedded-binding checks,
one-call accounting, immutable inputs, scratch guards/tails and owned export.
No elapsed-time, cost, model or adoption measurement was made.

These 32-byte failure records have no BCMPRES4 magic or authenticated source
binding. They are meaningful only under the separately admitted exact source,
kernel and adapter contract. Equal failure bytes from two different sources
do not identify the source or authorize another call.

## Portable data-only checks

[The helper](../tests/probes/native_wide_followthrough.py) supplies:
- continuation-request CASE, with --previous for a declared predecessor.
- continuation-check CASE --output FILE.
- failure-request CASE.
- failure-harness CASE --backend ABSOLUTE_BACKEND_SOURCE_PATH.
- failure-check CASE --output FILE.

The request helper verifies the complete declared predecessor response, work,
wire length and digest, then checks its state against the frozen next request.
An initial request refuses an extraneous predecessor. Recovery after refusal
requires the saved clear-first success, not the refusal output.

Failure expectations and invocation/binding files are in the
[packet directory](../examples/probes/native-wide-followthrough).
Rendered harnesses are unadmitted source, not an execution facility.
The tools never install, compile, load a kernel or launch a process.
A separately authorized reproduction uses the same exact-source procedure as
the preceding qualification, then checks its complete output files here.

The portable check pass inspected forty existing native captures, ten requests,
five byte-identical harness renderings and six intentional refusals through
61 data-only CLI calls. Four additional packet tests passed. These checks did
not perform another native run. Broader profile coverage and independent
reproduction remain open.
