# Experimental immutable TextList append

The explicit `bagaev-typed-record/9` family adds `list.push` to the
[structured source profiles](probe-record-source.md). Invocation and reference
result schemas end in `/9`. Profiles /1–8 refuse this operator even in an
unselected branch. /9 retains /8's 32 functions and 2048 expression nodes; no
resource bound is increased.

## Contract

The expression `["list.push", LIST, TEXT]` has exactly two operands, of types
TextList and Text, and returns a new TextList. Static checking visits both
operands and every branch. Runtime first charges the node tick, evaluates LIST,
then TEXT, and atomically reserves `n + 1` logical work units for the resulting
descriptors. Failure to reserve does not partially increment the work counter.
Only after that reservation, it checks the 64-item bound and then the 4096-byte
aggregate bound. Individual Text limits remain 1024 UTF-8 bytes and 256 scalars.
The global logical work bound remains 65536.

Count overflow returns `list-bound` / `RR_LIST_ITEMS` at the append expression.
Aggregate bytes return the existing `list-bound` / `RR_LIST_BYTES`. An operand's
own failure takes precedence over append checks. The original list, shared text
storage and existing aliases remain unchanged. Allocation failure is an
environment failure, never a successful value or ordinary language refusal.

The reference implementation copies immutable descriptors into a new vector.
Native lowering allocates new descriptors in the existing bounded scratch only
after checks, copies the old descriptors, and appends the new Text descriptor.
It does not dereference the old list pointer when its length is zero.

## Explicit native version

`json_view9_llvm` accepts only admitted /9 source and the existing Json-only
entry-argument interface, including zero arguments. The older /8 emitter refuses
/9 source even when the program does not use append. The new kernel symbol is
`bagaev_json_view9_kernel`; binding and module schemas are
`bagaev-json-view9-llvm-binding/1` and `bagaev-json-view9-llvm-module/1`.

The /9 owned-success wire has `BCMPRES2` magic and the previous header/node
structure. Its separately named exporter and data-only reader do not broaden
/8 acceptance. Count failure adds status 7 / reason 14. Allowed language failure
pairs are (1,9), (2,10), (4,11), (5,12), (7,14). Arena/environment failure (6,13)
is not exported as a language outcome. Failure metadata is still the 32-byte
record within the explicitly selected /9 API; it is not self-identifying.

As with [native JSON /8](probe-native-json.md), data admission, source/module
bindings and pointer shapes cannot authorize arbitrary native execution. The
unsafe adapter requires a separately trusted exact kernel, live readable extents,
disjoint scratch/output, immutable inputs, no retained pointers or unwinding.
It checks the actual scratch, calls once, then exports owned bytes before owners
are released. Limits, target, execution profiles and workflows are unchanged.
The [prepared-call API](probe-prepared-json.md) remains /8 only.

## Portable surfaces

- `examples/probes/backend/rust/list_push_main.rs`: explicit reference /9 CLI.
- `examples/probes/backend/rust/json_native_emit9.rs`: data-only /9 emitter.
- `examples/probes/list-push/cases.json`: 26 original complete reference
  expectations plus two supplemental hand-derived work-boundary witnesses.
- `examples/probes/list-push/native-observations.json`: 22 qualified native
  observations with canonical source bindings. Numeric locations were reconciled
  with the expected source paths through checked IR, not independently derived.
- `tests/probes/list_push_wire.py`: `request CASE`, `check-reference CASE --output
  FILE`, `check-native CASE --output FILE`, and `harness CASE --backend DIR`.
  These operations only read/write data or emit reviewed-template source.
- `tests/probes/backend/list_push_native_harness.rs.in`: exact-source,
  zero-argument harness. It links only to the separately reviewed generated
  kernel for that case. Compilation and execution require their own authority
  and bounded profile. It is not an arbitrary-kernel launcher.

The harness takes the fixture invocation path and scratch fill 90 or 165.
It checks exact canonical source before dispatch, one call, dirty output,
scratch guards and unused tails, expected status/reason/work/source path, and
complete owned wire after input/scratch destruction. Non-Json entry arguments
are intentionally outside this native interface.

## Evidence and limits

Local reference checks passed 26 frozen complete observations, two additional
work witnesses, 104 previous literal wires plus a SHA self-test, and 183 unchanged
/8 catalogue/lease/projection outputs. Four version-boundary cases passed; three
previous /8 module/binding pairs remained byte-identical. Six controlled reference
errors produced normal-exit wrong results and were detected.

The 22 eligible zero-argument cases produced 88 native observations at O0/O2
and two fills. The non-Json argument case, three invalid sources and two old-profile
refusals were not native executions. Three wire-boundary tests plus the SHA
self-test passed. Six separately compiled native-lowering errors produced
normal-exit valid exported but wrong outputs; complete comparisons detected them.

The alternative `examples/probes/list-push/catalog-program.json` changes only
`read_tags`, `view` and the explicit schema. Four-iteration accumulation replaces
branch enumeration. All 103 inherited outcomes matched the reference, and 412
native observations matched in the four settings, including actual predecessor
state feeding. These reuse the existing catalogue cases. Reference-observed work
is a separate differential check, not an independent work oracle.

Canonical helper JSON sizes, including one LF, changed from 1045 to 294 bytes
and from 945 to 266. Observed catalogue work increased by 0–168 units, with maximum
10345. Source byte counts are not token counts, model cost or speed measurements.
No new timing measurement or general efficiency advantage is claimed. Finite
matches do not establish whole-domain conformance or production readiness.

Review is a separate same-maintainer pass, not independent review. Existing CI
validates documentation and links only; native observations are separate local
evidence. No execution authority follows from this document or its fixtures.
