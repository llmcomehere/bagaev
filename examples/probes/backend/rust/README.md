# Kernel frontend source

This dependency-free Rust1.93 source uses the Rust2021 edition and implements
the transport and static gates
in [the probe contract](../../../../docs/probes.md). It produces checked IR;
it does not evaluate kernels, emit LLVM, implement a native entry, launch a
compiler, or provide execution authority. Compilation and conformance evidence
must be established separately; source and tests alone supply neither.

The explicit file interface is:

```
probe-front check-invocation --input /source/invocation.json
```

The file is opened read-only and must be regular. There is no default path,
stdin mode, discovery, subprocess, output file, cache, dependency resolver or
network operation. Reading stops at EOF or the 1048577th byte (the overrun
witness); an oversize frame refuses without parsing a prefix. Interrupted reads
are retried; other I/O errors, changing file size/modification metadata, wrong
CLI shape and output failure are environment failures with nonzero exit and
path-free stderr. The source owner must provide immutable admitted input files;
metadata checks are not protection against a hostile concurrent host writer.

Malformed payloads produce exactly canonical `bagaev-probe-result/1`
`invalid-ir` JSON followed by one LF and exit0. Every field is present, values
and type are null, work is0, and locations are invocation JSON Pointers.
No host error, panic or allocation failure becomes a language observation.

## Ordered and bounded checking

`transport.rs` parses the complete UTF-8/JSON frame with an explicit container
stack and a flat value arena. Duplicate decoded keys, including escaped/raw
equivalents, fail anywhere in the document before semantic checking. Integer
and fractional/exponent number tokens retain their lexemes and disjoint tags;
booleans never become integers. Valid escaped surrogate pairs decode to one
code point; isolated escaped surrogates remain code units until semantic shape
checking. Arena/container storage is bounded by the transport byte budget,
not an early semantic depth shortcut. Flat arena drop does not recurse.

`check.rs` completes outer exact fields/version/depth132/occurrences16384;
then program exact fields/version/depth128/occurrences8192; then all structure
and scopes, all references (entry first), sorted call-graph DFS, immediate-child
type checks, and finally argument shape/count/values. Bound walks use explicit
stacks and sorted decoded object keys. Structural expression recursion checks
depth32 and total512 nodes before descent, so it reaches at most33 calls;
type recursion is at most32, cycle recursion at most8 functions. All bodies
and both lazy arms are checked. No runtime overflow or work is evaluated.

Function IDs are ASCII-sorted; occurrence IDs are1..512 in complete body
preorder. Parameters and lexical slots have separate zero-based namespaces
per function; lexical slots are allocated once per binder occurrence in
structural order and never reused. Scope checks reject active shadowing but
permit the same spelling in disjoint scopes. Calls resolve to function indices
with a sorted acyclic direct-callee list; node pointers remain program-relative.

## Reusable interface

`check::check_program_bytes` and `check::check_invocation_bytes` consume borrowed
whole-frame bytes and return owned, immutable `CheckedProgram` or
`CheckedInvocation`, or `FrontendError::{Refusal,Environment}`. `ir` reexports
the checked types and exposes `Type`, `Scalar`, `NodeKind`, `BinaryOp`, `Node`,
`Parameter`, `Local`, `Function` and one-based `NodeId`. All checked-type
construction is private to the checker; consumers receive shared slices and
accessors, including canonical bytes, H(program), entry, full node map, resolved
children, declared/inferred types and parameter/lexical/function indices.
There is no unchecked constructor or serialized-artifact loader.

## Intermediate output

A valid invocation produces canonical JSON plus LF with exactly:

| Field | Meaning |
|---|---|
| schema | `bagaev-probe-checked-invocation/1`, distinct from a language result |
| arguments | Checked entry arguments, Int64 JSON integers or JSON booleans |
| entry | Zero-based index in the sorted functions list |
| functions | Sorted complete signature/body/local/callee records |
| nodes | All occurrences, in increasing one-based ID order |
| program | Complete canonical checked semantic program |
| program_pin | `sha256:` plus lowercase SHA-256 of C(program) |

Each function has exactly `body`, `callees`, `index`, `locals`, `name`,
`parameters`, `result`. Parameter/local records have exactly `name`, `slot`,
`type`; callees are sorted unique indices. Each node has exactly `children`,
`data`, `function`, `id`, `op`, `pointer`, `type`. Children retain source order:
binary left/right; not operand; let value/body; if condition/yes/no; call
arguments; loop initial/body. `data` is an exact op-specific record: int/bool
`value`; arg `parameter`; use `slot`; call `function`; let `declared`,`slot`;
loop `accumulator_slot`,`count`,`declared`,`index_slot`; other ops empty object.
Pointers are full program-relative paths, including unused functions/arms.

The intermediate output is capped at4MiB including LF; exceeding that cap is
environment failure. It contains no execution result, ABI buffer, measured
work, authorization or backend choice. It must never be accepted as checked
construction from another process: later consumers must call the checker on
the complete program and verify exact identity/binding independently.

`canonical.rs` implements Unicode-code-point key ordering, minimal integers,
required escapes and exact refusal wire bytes. `sha256.rs` includes independent
known-answer test source for empty, abc, the standard multi-block message and
one million a bytes. The frontend test source covers simultaneous failure
priority, deep transport, complete node numbering and scope/type boundaries.
These tests are not a substitute for the independently frozen conformance
oracle or actual admitted compilation/runtime verification.
