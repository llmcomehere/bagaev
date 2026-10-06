# Finite evidence compatibility example

This pure [/8 JSON](probe-native-json.md) example tests descriptive metadata
agreement. It does not authenticate a producer, prove a receipt true, grant
execution/publication permission, or implement static nominal evidence types.
The caller must obtain its required assertion through a separately trusted path.
A caller choosing its own requirement cannot claim independent verification.

## Closed input contract

The two arguments are a requirement object and an array of at most 16 receipts.
Objects have exact keys. Requirement keys are domain, subject, revision, method,
binding, scope; receipt keys additionally include outcome and selected.

- domain: artifact or request; subject: synthetic A or B.
- revision: integer 0, 1 or 2; booleans and floating tokens are invalid.
- method: bytes, static or runtime; binding: fixture, consumer or detached.
- scope: partial or complete; requirement scope must be complete.
- outcome: pass, unknown, refuted or withdrawn.
- selected: integer 0, 1 or 2. Non-runtime receipts require zero.

Validate the requirement first, then every receipt before selecting any evidence.
Malformed requirement returns invalid/requirement. Non-array, excess count or
any malformed receipt returns invalid/receipts, even after an otherwise good pass.
Duplicate decoded JSON keys are refused by the JSON transport boundary.
The Python function accepts already decoded ordinary JSON values; it cannot
recover duplicate keys discarded by an earlier parser.

Matching means exact equality of all six requirement dimensions. A matching pass
is applicable only when method is non-runtime or selected is positive. A matching
refuted or withdrawn receipt conflicts with an applicable pass, including when
its runtime selected is zero. Selection restricts positive execution evidence;
it does not erase a descriptive negative. Return pending/conflicting-evidence
for this combination, accepted/matching-pass for an unconflicted applicable pass,
and pending/no-applicable-pass otherwise. Every result is a record with Text
fields decision and reason. Pending is not proof of execution failure.

There is no bytes-to-runtime promotion, revision adaptation, binding reuse,
majority vote or global revocation. Unrelated negative receipts do not veto.
This finite A/B profile is deliberately not a general trust or authorization API.

## Portable material

- [Source](../examples/probes/evidence-compatibility/program.json) uses existing
  /8 operations; no language or backend behavior changes.
- [Ordinary Python function](../examples/probes/evidence-compatibility/ordinary_reference.py)
  implements the same pure contract without framework infrastructure.
- [217 cases](../examples/probes/evidence-compatibility/cases.json) preserve
  independently specified semantic expected records. Full reference/native wire
  bytes and logical work are captured observations, not independently derived costs.
- [Data helper](../tests/probes/evidence_compatibility_wire.py): list;
  request CASE emits the full /8 invocation; check CASE with --mode reference
  or native and --output FILE compares the complete recorded wire.
- [Reference harness](../tests/probes/backend/evidence_reference_harness.rs.in):
  substitute {{BACKEND}}, then supply one invocation file.
- [Native harness](../tests/probes/backend/evidence_native_harness.rs.in):
  substitute {{BACKEND}} and link only the separately admitted exact source's
  /8 kernel. Supply invocation file, dirty fill 90 or 165, and expected work.
  The canonical source hash and two-root arity are checked before dispatch.
  It observes one call, immutable inputs, output guards and unused tails, then
  decodes and exports owned bytes after temporary input/scratch owners are gone.

Compilation and native execution need their own bounded environment admission.
These templates and a digest cannot authorize an arbitrary native artifact.
No workflow changes or auto-execution are introduced.

The native wire binding preserves the digest of the distributed source bytes.
The LLVM artifact uses a separate canonical-source digest. Neither digest proves
truth or authorizes execution; formatting changes need deliberate rebinding.

## Evidence boundaries

Earlier qualification covered 42 cases at O0/O2 and two fills (168 observations),
plus 175 additional cases at O0/O2 and fill 165 (350 observations). Thirteen
source mutations reached normal wrong outcomes on explicit witnesses. These are
finite conformance controls, not general safety, provenance, static typing,
performance or model-quality evidence. Separate same-maintainer review and
exact-head documentation CI concern source integration; CI does not run native
conformance. No elapsed-time or model-cost comparison is claimed.

The portable packet was also rebuilt against its integration base: 217 ordinary
function checks, 217 complete reference replays and 217 O2/fill-165 native
replays matched the stored cases. The emitted LLVM and binding matched the prior
artifact. Wrong-wire comparisons, invalid fill, over-limit input and a different
valid source were refused; the source guard precedes native dispatch. This is a
new replay of existing cases, not 217 new independent semantic expectations.
