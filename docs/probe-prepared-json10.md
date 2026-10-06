# Experimental source-once JSON /10 calls

This is a separate prepared calling convention for the explicit /10 source
profile. It does not change language semantics or the existing [/8 API](probe-prepared-json.md).

## Ownership and budget

`typed_record::prepare_json_program_v10` returns an owned, immutable
`PreparedJsonProgramV10`. `prepare_json_arguments_v10` returns a distinct
`PreparedJsonInvocationV10` that borrows it and owns the per-call JSON data.
All entry parameters must be Json; zero through eight still require exact arity.
The /8 and /10 handle types cannot be passed to the other version's functions.
`evaluate_prepared_json_v10` starts work at zero and emits the existing complete
`bagaev-typed-record-result/10` observation, with unchanged locations and charges.

The conceptual envelope uses canonical source P and raw argument-array A:
`{"schema":"bagaev-typed-record-invocation/10","program":` + P +
`,"arguments":` + A + `}`. Its constant fragments total **70 bytes**.
Checked arithmetic enforces `70 + len(P) + len(A) <= 1048576` before parsing A.
The /8 constant of 69 must not be reused for this two-digit version.
Then enforce `source_values + argument_values + 2 <= 16384`, argument-array
depth at most 131, array shape, exact arity and existing JSON ownership bounds.
Retain integer/float/Boolean distinctions, token spelling and duplicate-key refusal.
Source preparation and per-call argument refusals remain distinct phases.

`prepared_json_native_v10::prepare` owns the source and result-graph metadata.
Its unsafe `evaluate` rechecks actual scratch capacities per call and exports
owned BCMPRES3 bytes through the existing /10 boundary. Preparation captures no
scratch pointer or native execution permission. The exact admitted kernel,
alignment, disjointness, lifetime, immutable-input and no-unwind obligations
remain those of [native JSON](probe-native-json.md). No concurrency pool or
automatic artifact admission is introduced.

## Portable source and data surfaces

Compilation/execution requires a separately admitted bounded environment.
These files are not launchers and do not change CI or execution controls.

- [Reference harness](../tests/probes/backend/prepared10_reference_harness.rs.in):
  substitute `{{BACKEND}}`; arguments are source file, mode and argument files.
  Modes are `run`, `admit`, `inspect`, or `batch`. Only batch takes multiple
  argument files and retains one prepared object; each output is a hex line.
  Other modes take exactly one argument-file slot. Admission emits ADMITTED or
  ARGUMENTS: followed by the refusal. Preparation errors have PREPARE: prefix.
- [Native marker tests](../tests/probes/backend/prepared10_native_adapter_tests.rs.in):
  substitute `{{BACKEND}}`, compile as Rust tests and run serially. Fixed marker
  functions test no-dispatch refusals, output faults and detached repeated bytes.
- [Native catalogue harness](../tests/probes/backend/prepared10_catalog_harness.rs.in):
  substitute `{{BACKEND}}` and `{{CATALOG_SOURCE}}` with the reviewed backend and
  [catalogue source](../examples/probes/record-list-push/catalog-program.json).
  Link only that source's separately admitted exact /10 kernel. Arguments are
  raw argument-array file, fill 90 or 165, and expected logical work.
- [Compile-only ownership cases](../tests/probes/backend/prepared10_ownership_cases.rs.in):
  substitute `{{BACKEND}}`, use `--emit=metadata` and exactly one `--cfg` name:
  return_local/E0515, drop_borrowed/E0505, private_field/E0616,
  unsafe_required/E0133; old_program_to10, new_program_to8,
  old_invocation_to10 and new_invocation_to8 each require E0308.
  scoped_borrow and explicit_unsafe compile. Never execute these compile fixtures;
  explicit unsafe syntax is not proof of runtime safety or permission.
- [Catalogue vectors](../examples/probes/prepared-json10/catalog-cases.json)
  contain 103 prior complete reference/native outputs; copied chain inputs do
  not by themselves establish actual predecessor feeding.
- [Boundary data](../examples/probes/prepared-json10/boundary-cases.json)
  fixes constant-7 sources, work 1 and byte/value arithmetic. Include whitespace
  in A; exactly at the ceiling accepts and one beyond refuses.
- [Data helper](../tests/probes/prepared_catalog10_wire.py): `list`, `request CASE`,
  or `check CASE --mode reference|native --output FILE`. It checks exact source
  identity and complete output bytes; it never compiles or runs code.

## Finite observations

Twenty earlier eligible zero-argument /10 cases yielded 80 prepared native
observations. The 103 catalogue cases yielded 412 full-wire matches using the
same prepared handle and scratch allocations within each batch. Sixteen extra
chain calls included twelve actual predecessor feeds. Manual arities zero/eight
added eight complete constant-result observations. Returned buffers survived
dropping input, scratch and prepared owners. These are bounded observations.

Three marker tests, eight exact compiler refusals/two positive compile controls,
and four concrete boundary faults were checked separately. The entire accepted
typed-record source remained an unchanged prefix and the old native prepared
file stayed unchanged; old /8 retained 103 reference and 103 native outputs.
No timing, broad safety, independent reproduction or production claim follows.
Exact-head CI checks documentation, not native conformance.
