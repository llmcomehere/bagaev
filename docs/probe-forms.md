# Exact source-form codecs

`src/bagaev_forms.py` is a pure implementation slice of
[probe-forms/1](probes.md#three-exact-encodings): JSON, compact S-expressions
and restricted familiar-code constructors reconstruct data for the existing
L2 checker. It does not execute host-language source, use a Python AST/eval,
read files, launch tools, resolve dependencies, call models, or grant admission.
The L2 language, frozen fixtures and program pins are unchanged.

## Library surface

- `decode(source, form='json', mode='program')` returns reconstructed data.
- `encode(value, form='json', mode='program')` returns canonical UTF-8 bytes.
- `check(source, form='json')` delegates the reconstructed program to L2.
- `evaluate(source, argument, form='json')` passes the argument directly to
  the unchanged L2 evaluator; there is no argument traversal/copy/hash here.

The optional `mode='patch'` only selects familiar constructor positions for
patch data. This module does **not** yet implement the outer edit-frame gates,
candidate-map binding, draft creation or the complete form experiment.

A reconstructed root string remains data and is refused as `L2_PROGRAM`;
it is never treated as a second source document. Syntax reconstruction finishes
before L2 semantics, so generic malformed program/definition shapes remain L2
errors. Neither constructors nor encoding repair fields, schema, references or
pins. Unknown operation arrays have a generic representation in every form.

JSON retains the original L2 transport/parser error gate. For long integer
lexemes, a subsequent iterative, source-order pass restores the exact integers
instead of exposing the checker's out-of-range representatives as codec data.
This does not change the L2 parser or its semantic refusal priority. Decimal
conversion uses bounded chunks without changing Python's global conversion
limit. JSON floats retain their tag and reach L2 checking. Escaped isolated
surrogate code units are retained for contextual semantic rejection.

S-expression/familiar sources have the specified 1 MiB, depth 256 and 32,768
source-value bounds. Depth/count applies to grammar values, excluding object
keys and constructor/operation names; synthetic fields introduced by shorthand
are checked later under unchanged L2 bounds. Byte, syntax and form bounds are
not runtime semantic-work counters. Encoding also bounds representation size,
occurrences and nesting and rejects cycles and non-JSON object types.

Canonical familiar output uses `l2_program` only for the exact four-field
program shape and matching schema, and `l2_def` only for exact params/body
objects in allowed positions. Generic negative shapes are preserved. All
constructors outside their permitted positions and all host-language operations
are syntax failures. There are no imports, interpolation, comments or fallbacks.

## Verification scope

The source tests cover canonical bytes, every operation shorthand, positional
constructors, generic negative shapes, duplicate decoded keys, transport errors,
bounds, surrogate/float tags, exact large integer reconstruction, cycle/type
refusal, and prevention of recursive interpretation of root strings.

They also use all 42 non-edit cases from the frozen form oracle in all three
forms: 126 value/error/pin observations, including shallow borrowed inputs,
short circuit, L2 work limits, quadratic charges, field order, stale pins,
references and cycles. Expectations and identity pins come from the existing
oracle, not from a candidate evaluator. Shared SHA identities and program data
are preserved. These tests do not directly observe the semantic step counter,
complete edit traces, tokenizer cost, model behavior, or native/L3 parity.

The modules remain experimental. Broader model/representation measurements,
semantic-step observations and full 57-case/16-mutation form acceptance remain open.

## Recorded local checks

On October 4, 2026, the 12 codec test methods passed on CPython 3.12.
This includes the 126 frozen non-edit form/value/error/pin observations.
All 17 existing L2 regression methods also passed. No test was skipped.
A separate same-maintainer checking pass corrected a root-string double-parse
problem and added explicit regressions for it, long integers and resource
bounds. This is self-review, not an independent review or the full form study.

## Pure structural edit receiver

`bagaev_form_edit.draft(original, frame, candidate_map=None)` validates the
original L2 snapshot first, then all nine outer gates in the frozen order.
Patch decoding preserves form errors. The existing pre-CAS patch envelope/map
checks precede frame-base and optional candidate binding; ordinary L2 CAS,
combined definition validation and target checking then create the candidate.
Reconstructed patch strings are data and never reparsed as another patch.

The optional candidate map is a caller-owned dictionary from ID to a record
with `kind: "patch"` and the exact canonical content `pin`. The caller must keep
it immutable during the call. The receiver checks the selected binding and
confers no authority. A null candidate ID needs no map. Canonical hashing is
iterative and includes the entire patch, not selected fields or source spelling.

Success returns exactly schema/status/base/target/program/patch/admission,
with schema `probe-draft/1`, status `draft`, and admission false. Both program
and patch are detached. Failure produces an exception with no partial draft;
original and retained snapshots remain unchanged. There is no write, shared
transaction, candidate-ID allocation or automatic commit. L2 errors retain their
code and have no enclosing location; wrapper errors carry the specified frame
JSON Pointer.

Six edit test methods passed on October 4, 2026, including 51 frozen edit
trace/form observations: all 15 edit cases in three forms plus both ordered
after-stages of the CAS case. Extra checks cover candidate binding before CAS,
original-first validation, syntax/field priority, surrogate escape boundaries,
root-string non-reinterpretation and detached ownership. These results do not
complete the mutation protocol, observe semantic step counts or establish model
performance or cost. Checking used a separate same-maintainer pass.
