# Frozen P0 serial model

This supporting reference model composes the [serial receiver subset](p0-serial-receiver.md)
with the remaining frozen P0 behavior, candidate admission, handoff verification
and serial-order cases. It addresses a narrow question: do these state transitions
produce the observations specified by [p0-contract/1.0.0](p0.md)? It is neither a
new language feature nor a prerequisite for model experiments.

## Components and evidence boundaries

- [Behavior](../src/p0_behavior.py): pure list-to-set migration and add-tag,
  including atomic refusal and existing-member no-op at maximum revision.
- [Admission](../src/p0_admission.py): immutable complete-record retention,
  recomputed UTF-8 digest, current admission grant, revision and trusted-evidence
  bindings. Candidate-supplied evidence never enters the trusted fixture store.
- [Handoff](../src/p0_handoff.py): exact file and length-prefixed snapshot hashes,
  frozen input bindings, independently checked result labels, complete before/after
  observations, accounted effects/assumptions and separate current admission.
  Honest predecessor failures remain in the acceptance record.
- [Orders](../src/p0_orders.py): both orders of two transfer requests, evaluated
  serially. Each observed trace must match exactly one permitted complete
  alternative. The nonenforcing-receiver counterexample actually applies the
  late write to an independently stale receiver and must report guarantee failure.

All sessions, grants, trusted evidence and candidate observations are synthetic
initial inputs. Candidate source bytes are opaque data and are never executed.
A fixture saying that a checker passed is not a claim that it ran. The handoff
model validates supplied observations against the independent frozen oracle;
it does not perform a real implementation handoff.

## Reproduce the finite check

The [selection](../examples/probes/p0-model.json) pins the unchanged specification
and oracle hashes. The [checker](../src/p0_model.py) dispatches all 85 frozen cases
without passing expected observations into the implementations. Its 144 checked
projections include both serial transfer orders. Missing keys, wrong scalar types,
array order and invalid alternatives cannot be filled from expected values.

After reviewing the source and choosing an authorized bounded local profile:

```sh
python3 -B -m unittest discover -s tests -p 'test_p0*.py'
```

The full-model test has two test methods, distinct from the 85 case count. It
also checks six wrong-observation matcher controls and eight explicit malformed
snapshot controls. The existing subset test remains independently runnable.
Use ordinary Python assertion-enabled execution, not `-O`.

## Limits

The separate [bounded JSON ingress](p0-json-ingress.md) adds raw write/transfer
envelope validation before receiver dispatch. It leaves this frozen oracle and
the receiver's ordered semantic checks unchanged. Its transport limits and
supplemental cases are distinct from the 85 frozen model cases. Admission,
handoff and scenario-event inputs remain trusted synthetic fixtures.

This is finite synthetic model conformance, not proof of liveness or a production
implementation. It does not establish actual concurrent execution, crash-safe
storage, external authentication/enforcement, candidate-code execution, model
quality, speed or cost. Component interfaces currently assume the documented
well-shaped synthetic fixture records; the snapshot checks are not a general
untrusted-input parser. Real enforcement and the broader comparison passport
retain their own acceptance requirements.

The supplemental [sender journal model](p0-sender-journal.md) exercises explicit
save-before-send and restore-exact-intent assumptions using committed in-memory
images. Stable caller effect handles are model inputs, not inferred semantic
identity. Fresh authorization still passes through all receiver gates. This
supplement does not establish real durable storage or process-crash recovery.
