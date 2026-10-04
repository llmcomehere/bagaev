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
are preserved. The original codec tests did not directly observe the semantic step counter.
The additional step observations below do not measure tokenizer cost, model
behavior or native/L3 parity.

The modules remain experimental. Broader model/representation measurements
and acceptance outside the bounded observations below remain open.

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
complete the mutation protocol or establish model performance or cost. Checking used a separate same-maintainer pass.

## Direct semantic-charge observations

An additional test on October 4, 2026 observed the existing evaluator's nested
charge counter without changing its source or semantics. All 99 observations
matched frozen literals: 33 cases across the three source forms. This includes
the successful 95,267-step case, the first forbidden step at 100,001, and the
quadratic-charge refusal at attempted work 131,076. Values and errors were also
checked against the frozen oracle. The codec suite now has 13 passing methods.

The process-local Python trace is restricted to the exact nested charge code
object and reads only its numeric step total. It restores the previous trace
after each evaluation. Tracing adds overhead: these are semantic work-counter
observations, not wall-clock timings or comparative performance measurements.
These observations do not establish model benefit or comparative cost.

## Concrete mutation observations

The [recorded source edits and observations](../examples/probes/form-mutation-results.json)
cover all 16 named frozen form mutation obligations. Each declared witness
detected its concrete source edit in all three forms. Both unmodified witness
suites passed first. Only an assertion mismatch on the declared witness or its
declared wrong L2 semantic error counted; unrelated interpreter exceptions did
not qualify. The JSON records exact old/new source edits and source identities.

These results cover the 57 frozen form cases, their specified ordered edit
after-stages, the 99 counter observations above and 16 concrete source edits in
the documented CPython profile. They are not a proof against arbitrary mutations,
an independently reviewed release, a model/tokenizer study or native L2 parity.
The experiment's initial recorder handling and early-base recipe correction are
retained in the result metadata; frozen inputs and expectations did not change.
