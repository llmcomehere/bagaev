# Native build-record inspection, frozen precursor r1

Experimental data-only scope, 2026-10-06. This is deliberately a partial build record, not adoption of the broader production manifest proposal. It exposes missing provenance instead of inventing it retrospectively.

The receiver supplies an expected descriptor independently. The submitted record is not allowed to select the expected descriptor. This experiment compares data; it neither authenticates that receiver nor checks the truth of descriptive compiler/dependency statements.

## Exact record and external bytes

Record is one UTF-8 JSON object, at most 65,536 bytes, with exactly schema, profile, source, module, harness, artifact, build, dependencies, provenance. Duplicate decoded keys, BOM, malformed UTF-8, floats, constants, extra/missing fields and trailing values refuse. Transport failure is `FORMAT`; oversize is `BOUND`, checked first. SHA pins are exactly 64 lowercase hexadecimal digits (no prefix).

- schema is `bagaev-build-record-inspection/1`; profile is exactly integer 8 (Boolean is not integer).
- source, module, harness and artifact are digest strings.
- build has exactly target, llvm_opt, rust_opt, clang, rustc. target is `x86_64-unknown-linux-gnu`; llvm_opt is O0 or O2; rust_opt is `default-unspecified` for the current harness recipe. clang and rustc are digest strings supplied as descriptive executable identities. They do not claim the linker, sysroot or transitive tool closure was pinned.
- dependencies has exactly needed, interpreter, search_path, versions. needed and versions are sorted unique arrays of at most 32 strings; each string is 1..128 ASCII printable bytes. interpreter is 1..256 ASCII printable bytes. search_path is exactly an empty array. Paths and names are inert data and are never opened or resolved by this API.
- provenance is exactly `retrospective-association` or `observed-build`. An observed-build label is an unverified assertion here, not promoted evidence.

The external expected descriptor has this exact same shape and limits. Validate it first after record transport, returning `EXPECTED` when absent or malformed. Validate the record second (`SHAPE`). Compare profile, build, dependencies and provenance in that order, returning `CONTEXT` on any mismatch. Compare source, module, harness and artifact pins in that order with the expected record (`PIN`). Schema has already been checked independently, not accepted via the expectation.

The caller then supplies exactly four immutable byte strings named source, module, harness, artifact. Bounds are 1 MiB, 8 MiB, 1 MiB and 32 MiB respectively, checked in this order before any hash. Invalid/missing byte objects refuse `BYTES`; oversize refuses `BOUND`. SHA256 must match the submitted record, in the same order, otherwise `CONTENT`. The API does not canonicalize source or parse LLVM/Rust/ELF: validity of source/module/artifact remains separate from byte association. Even arbitrary non-executable artifact bytes can match this inspection.

Success is exactly `{status:"matched-data",execution_admission:false,build_verified:false,dependencies_resolved:false}`. No file, process, network, authority, cache promotion, secret or public write is performed. No mutation of any caller input. Exceptions not explicitly classified are not successful inspection.

## Frozen literal test plan

Use four different tiny byte strings and manually selected descriptor values, unrelated to any real compiler installation. Literal expected status/code must be fixed before implementation. Include: valid association; observed-build assertion still grants nothing; missing expectation; record unknown schema; Boolean profile; extra top-level field; unknown build field; duplicate/unsorted dependency; search path nonempty; invalid pin spelling; wrong target/optimization/tool identity; provenance mismatch; each of four expected pin mismatches; each of four content substitutions; wrong/missing byte object; source/module/artifact bound; duplicate escaped JSON key; malformed UTF-8; trailing value; oversize transport; record-shape and context/content ordering collisions. No data-valid success is called a successful build.

