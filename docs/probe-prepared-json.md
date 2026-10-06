# Experimental source-once JSON calls

This separate calling convention reuses a checked /8 source program across
calls. It does not change the old full-invocation interface, language semantics,
logical work limit or [native JSON](probe-native-json.md) unsafe obligations.
It is an experimental library API, not a new serialized authority token.

## Ownership and admission

`typed_record::prepare_json_program_v8` returns an immutable owned
`PreparedJsonProgram`. Its entry parameters must all be Json. Arguments are
admitted separately by `prepare_json_arguments_v8`; the resulting
`PreparedJsonInvocation` borrows the program and owns per-call JSON values.
`evaluate_prepared_json_v8` creates a fresh evaluator with work zero and returns
an owned result buffer. Earlier checked-source entry points are unchanged.

`prepared_json_native::prepare` additionally owns result-graph metadata. Its
unsafe `evaluate` takes the prepared object, raw argument-array bytes, current
caller-owned Text and cell scratch slices, source binding and exact kernel.
Graph and actual scratch capacities are rechecked for each call. Preparation
neither captures scratch pointers nor certifies later storage. Each invocation
owns its input descriptor graph until output export finishes. Work and used
counters start fresh; outputs detach before owners are released.

The caller must separately admit the exact compiled kernel and uphold all
pointer, lifetime, disjointness, immutability and no-unwind requirements in the
native JSON contract. A digest, a prepared handle or passed data check does not
establish those properties or authorize native execution. This API does not
provide a shared workspace pool or concurrent mutation protocol.

## Conceptual envelope budget

Let P be the checker's canonical program bytes and A the raw argument-array
bytes, including surrounding whitespace. The explicit conceptual envelope is:

`{"schema":"bagaev-typed-record-invocation/8","program":` + P +
`,"arguments":` + A + `}`.

Its constant fragments total 69 bytes. Checked arithmetic enforces
`69 + len(P) + len(A) <= 1048576` before parsing arguments. Count actual parsed
JSON values, not executable nodes: `source_values + argument_values + 2 <= 16384`.
The argument array includes its own root. Argument-array depth is at most 131,
so an individual argument subtree is at most 130. Zero through eight entry
arguments still have to match the exact checked signature.

Integer token spelling, overflow/fraction distinctions and isolated surrogate
data are retained by the existing JSON transport; do not normalize arguments
with the source-only canonicalizer. Duplicate decoded keys refuse. This
conceptual envelope differs from arbitrary whitespace-heavy old envelopes:
matching behavior is claimed only for the explicitly admitted shared domain.
Source preparation and argument admission failures are distinct phases.

## Portable reproduction surfaces

Compilation and execution still require a separately approved bounded profile.
These templates are source, not a launcher or CI permission change.

- [Reference harness](../tests/probes/backend/prepared_reference_harness.rs.in):
  substitute `{{BACKEND}}` with the reviewed backend folder. Arguments are
  source file, raw argument-array file, and `run` or `admit`.
- [Native admission tests](../tests/probes/backend/prepared_native_adapter_tests.rs.in):
  substitute `{{BACKEND}}`; compile as Rust tests. They use fixed marker functions,
  test pre-dispatch refusals, output metadata and detached repeated results.
- [Catalogue harness](../tests/probes/backend/prepared_catalog_harness.rs.in):
  substitute `{{BACKEND}}` and `{{CATALOG_SOURCE}}`, the latter pointing to the
  existing [catalogue source](../examples/probes/catalog-source/program.json).
  Link only its separately admitted exact kernel. Arguments are argument-array
  file, fill 90 or 165, and expected logical work.
- [Fixed vectors](../examples/probes/prepared-json/catalog-cases.json) contain
  103 existing inputs and complete expected reference/native bytes. Four chain
  input copies here do not constitute actual predecessor-fed chaining.
- [Data helper](../tests/probes/prepared_catalog_wire.py) supports `list`,
  `request CASE` and `check CASE --mode reference|native --output FILE`. It checks
  the source identity and never compiles or executes code. Feed `request` bytes
  to the relevant separately admitted harness and compare its entire output.

## Existing observations and limits

Local source-once conformance previously matched the 103 fixed inputs at O0/O2
and two scratch fills: 412 native observations. Actual four-step chaining and
25 promoted smaller JSON scenarios were checked separately. Repeated mixed
success/refusal calls and owned-result lifetimes have additional finite checks.
These are repeated observations, not independent application families.

The exact portable packet was separately qualified locally: its reference and
native O2/fill165 harnesses each matched all 103 complete fixed outputs, three
marker tests passed, and two wrong-output data checks refused. Four additional
harness mode/fill/read-limit controls refused without result output. These are
206 replay observations, not 103 new cases or actual chaining. A separate
same-maintainer review was performed; it is not independent review.
Exact-head documentation CI does not execute native tests.
No broad native safety, production, general memory, elapsed-time or model-cost
claim follows from this API or from finite conformance.
