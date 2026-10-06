# Experimental immutable nominal record-list append

The explicit `bagaev-typed-record/10` profile adds `records.push` to the
[structured source family](probe-record-source.md). Invocation and reference
result schemas also end in `/10`. Existing /1–9 refuse this new operation even
in an unselected branch. The [/9 TextList append](probe-list-push.md) stays
available in /10; no earlier profile or declared capacity is broadened.

## Contract and motivation

`["records.push", LIST, RECORD]` has exactly two operands. LIST must be a named
record list and RECORD must have its exact nominal element-record type. The
result preserves the list's nominal identity. Equal-shaped records from another
declared type are not implicitly converted.

Runtime charges the node tick, evaluates LIST, then RECORD, atomically reserves
`n + 1` descriptor work, and only then checks the declared list capacity, which
remains 0–4. Capacity overflow returns `record-list-bound` / `RR_RECORD_LIST_ITEMS`
at the append node. Operand failures precede append checks. A failed atomic work
reservation does not partially advance the counter. The global work cap remains
65536; /10 keeps /8's structural caps and all existing type-graph bounds.

The result owns a fresh vector of immutable record references. Original lists,
records and aliases remain unchanged. Native lowering similarly copies `n`
existing Cell32 descriptors into `n + 1` fresh cells, then stores the new record.
It performs no old-pointer read at length zero. Allocation/environment failure
is not reported as successful execution or ordinary language refusal.

The motivating catalogue helper `read_entries` otherwise enumerated lengths
0–4 and repeated calls to `read_entry`. The alternative catalogue source in
this directory changes only that helper and the explicit schema relative to
examples/probes/list-push/catalog-program.json. Four-iteration accumulation preserves
its bounded input policy; the operation does not increase application capacity.

## Separate native profile and wire

The exact /10 emitter accepts Json-only entry arguments, including zero arguments,
and supported primitive/composite results. Its symbol is `bagaev_json_view10_kernel`;
binding/module names are `bagaev-json-view10-llvm-binding/1` and
`bagaev-json-view10-llvm-module/1`. Older /8 and /9 emitters refuse /10 even when
no new operator occurs.

Success wire magic is `BCMPRES3`, using the prior header/node structure. A separately
named exporter and reader retain strict version acceptance. Capacity failure adds
status 8 / reason 15. Allowed language-failure pairs are (1,9), (2,10), (4,11),
(5,12), (7,14), (8,15); arena failure (6,13) remains outside those outcomes.
Failure metadata is still a 32-byte record scoped by the explicitly selected
adapter; detached failures are not self-identifying source/artifact evidence.

Existing fixed Text/Cell scratch capacities, target and unsafe exact-kernel
obligations are unchanged. The adapter rechecks storage, invokes once, checks
arena descriptors and exports owned output before owners are released. Hashes,
checked source and pointer shapes do not admit arbitrary code. The existing
[prepared-call API](probe-prepared-json.md) remains the separate /8 interface;
[distinct prepared /10 calls](probe-prepared-json10.md) are now available without
changing it.

## Portable checks

- `examples/probes/backend/rust/record_list_push_main.rs`: reference /10 CLI.
- `examples/probes/backend/rust/json_native_emit10.rs`: data-only LLVM/binding CLI.
- `examples/probes/record-list-push/cases.json`: 27 pre-frozen complete reference
  expectations, including nominal mismatch, operand priority and work boundaries.
- `examples/probes/record-list-push/native-observations.json`: 20 eligible prior
  native observations and canonical source bindings; numeric locations were
  reconciled with expected source paths through checked IR.
- `examples/probes/record-list-push/catalog-program.json`: the bounded alternative
  source, with unchanged application results on the inherited finite corpus.
- `tests/probes/record_list_push_wire.py`: data-only `request`, `check-reference`,
  `check-native` and `harness` modes with the same argument forms as the /9 checker.
- `tests/probes/backend/record_list_push_native_harness.rs.in`: exact-source,
  zero-argument template. It checks one call, dirty output, scratch guards/tails,
  expected metadata/path and complete owned wire after owner destruction.

A generated harness takes invocation path and scratch fill 90 or 165. Compilation,
linking and execution require separate authority and bounded profiles. The
fixture checker emits data/source only; it is not a kernel launcher.

## Evidence and limits

Local checks matched all 27 frozen complete reference observations, 211 prior
/8,/9 observations and 104 old literal tests plus the SHA self-test. Two old
module/binding pairs remained byte-identical; four legacy-emitter refusal checks
passed. Seven controlled reference faults were detected.

Twenty eligible zero-argument cases produced 80 native observations at O0/O2
and two fills. The typed non-Json argument case, four invalid-source cases and
two older-profile refusals were not native executions. Five controlled lowering
faults produced valid but wrong exported wires. A sixth returned raw success
with two records under declared capacity one; the output graph refused it as
`NATIVE_VALUE`. That is output-validation detection, not a wrong-wire comparison,
and the exporter was not weakened to make a negative test pass.

Four data-only wire-matrix tests plus the SHA self-test checked three success
versions, failure-pair scopes, invalid locations and inactive metadata. A malformed
reference mutant initially skipped child inference and panicked before its target
fault; it was corrected to preserve inference while omitting nominal equality.
An initial native qualifier omitted the contracted overflow mapping; all cases
were repeated after that checker correction. These failed setups were not counted
as intended negative passes, and frozen expected results were not changed.

The catalogue retained all 103 inherited complete application outcomes. Its native
replay produced 412 observations in four settings, including actual predecessor
state feeding. These reuse existing cases; reference-observed work is not an
independent work oracle. `read_entries` canonical JSON size changed from 1039 to
302 bytes including LF. Work increased by 0–19 relative to the /9 alternative,
with maximum 10360. No timing, model-token, cost or general efficiency claim follows.

Review is a separate same-maintainer pass, not independent reproduction. Existing
CI validates documentation and links, not these native probes. Finite checks do
not establish whole-domain conformance, production readiness or execution authority.
