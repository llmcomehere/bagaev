# Ordinary native Rust batch baseline, conformance stage only

Implement ordinary imperative Rust business logic for both accepted batch
policies (original and total10), using Vec/String and a running total. Do not
translate or invoke the bagaev programme graph or evaluator. Before code, pin
the existing 32 and 40 complete literal cases; preserve them unchanged.

Reuse only the existing bounded JSON transport parser, explicitly disclosing
that common input dependency. This is not an independent JSON parser. The
baseline accepts a request JSON file and an explicit original/total10 selector,
not a bagaev invocation/programme or native ABI. Its output is the complete
business Outcome JSON value. Therefore passing conformance is not an equal-ABI
or end-to-end performance comparison. No measurement in this slice.

Input profile: existing 1 MiB transport limit and parser bounds; all decoded
strings must be scalar UTF8 and at most 256 bytes. Refuse out-of-profile text
before business processing. This admits all frozen 32/40 cases, including
invalid business names and malformed shapes. Integer projection accepts only
lexical Integer values fitting Int64; fraction/exponent Number is not Int64.
Preserve shape-before-business, individual-policy-before-total, first failure,
original-stock rollback, receipts and empty-batch validity. Use checked integers
where applicable and no unsafe code. No network/state/durable effects.

Freeze verification: 32 original + 40 total10 full values at Rust O0 and O2, input file
preservation, deterministic repeated output for representative multistep case;
malformed JSON, oversized frame, non-scalar/oversized text and unknown selector
refuse with no success stdout. Existing approved offline build/test profiles
only. No extra packages, credentials, model calls or control changes. Native
baseline calls must be distinguished from bagaev native calls and measurements.
