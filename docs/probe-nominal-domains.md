# Existing nominal-domain protection: a parity control

Two declared records, ArtifactDigest and RequestDigest, each contain a Text
value. A function taking ArtifactDigest must reject an implicit RequestDigest
argument even though their fields have the same shape. This already works with
bagaev nominal records; ordinary Rust newtypes supply the same distinction.
No new type feature, authenticated constructor or evidence authority is added.
The names denote synthetic examples, not cryptographically verified digests.

## Seven frozen cases

- Equal and unequal values in the required domain return true and false.
- Cross-domain first and second arguments are refused statically.
- An invalid unused function and an invalid unreachable branch are also refused.
- Explicitly extracting the payload and constructing the other domain is allowed.

Four bagaev refusals require invalid-ir/RR_TYPE, the exact offending source path,
null value/type and zero work. Three successes require the declared Boolean,
with no error metadata. Positive work counts in stored full wires are observed
values, not independent cost predictions. Rust refusals require E0308 type
mismatch involving both types; an arbitrary compile failure is not acceptance.
Three positive Rust sources contain assertions which must actually execute.

This prevents accidental implicit substitution at a typed call boundary. It
does not prevent deliberate relabelling, validate raw JSON or authenticate an
external producer. Those are separate from [descriptive evidence matching](probe-evidence-compatibility.md).
Ordinary-language parity gives no novelty, security superiority or economic claim.

## Portable data and checking

[The vectors](../examples/probes/nominal-domains/cases.json) include both source
forms, prior literal semantic expectations and complete reference outputs.
[The read-only helper](../tests/probes/nominal_domain_wire.py) supports list,
request CASE --mode reference|rust, and check CASE --output FILE for complete
reference bytes. It never invokes a compiler or executes the emitted source.

Use the [reference harness](../tests/probes/backend/evidence_reference_harness.rs.in)
with the /8 invocation emitted by the helper after substituting {{BACKEND}}.
For ordinary Rust, compile the exact emitted source under a separately admitted
profile with edition 2021 and warnings denied. For negative cases inspect the
compiler's structured diagnostics: E0308 is required, unrelated errors do not
count; do not execute a refused case. For positive cases require successful
compilation and execution of its assertions. Compilation and execution still
need appropriate admission; data fixtures cannot grant it.

Earlier bounded qualification matched all seven reference expectations and the
ordinary Rust outcomes: four static refusals and three positive executions for
each alternative. This did not run bagaev native kernels, measure performance,
or establish independent review or full type-system correctness.
Exact-head CI checks documentation, not these runtime/compile observations.

The portable replay rebuilt the current reference harness and matched all seven
complete prior wires. Four ordinary Rust compiles produced exactly E0308 with
no unrelated error code; three positive assertion programs actually executed.
Three data-helper negative controls and documentation checks passed. This is
reproduction by the same maintainer of existing cases, not independent review.
