# Fixed native kernel caller

This source implements the explicit-file driver for one statically linked LLVM
kernel object under [the probe contract](../../../../docs/probes.md). It consumes
the existing complete Rust checker and read-only IR. It does not evaluate an AST,
emit LLVM, load libraries, invoke subprocesses, discover symbols or select a
different program at runtime. It adds no generic external-library mechanism.
Source preparation is not compilation, artifact admission or conformance evidence.

`native_main.rs` is the separate Rust2021/std-only binary root. A later authorized
build must link exactly one object exporting these immutable data and C symbols:

- `bagaev_probe_entry`: `void(const int64_t arguments[8], void *output)`.
- `bagaev_probe_binding`: the producer's contiguous canonical embedded descriptor
  bytes, without a terminating LF or NUL. This is data, not the outer LLVM module
  record emitted on the emitter CLI's stdout.
- `bagaev_probe_binding_length`: the producer's aligned immutable 64-bit length.

The binary is restricted to little-endian x86_64 Linux, baseline x86-64 CPU and
system C ABI. The source has a target compile guard. Actual compiler/linker
versions, machine features, symbol definitions, dependency closure and object
correspondence require independent artifact admission. This source does not
certify them or run a build tool.

## Invocation and effects

The only argument sequence, excluding the executable name, is:

```
invoke --input INVOCATION_FILE --witness /out/WITNESS_FILE --prefill 00|ff
```

There is no stdin/default input, alternate command, option reordering, automatic
directory creation, output discovery, overwrite, deletion or retry. The witness
path must be absolute under `/out` with a file component and no parent traversal.
Its existing parent must resolve to that same direct path. `create_new` prevents
ordinary replacement of an existing destination. Input is opened read-only after
regular-file pathname and descriptor checks. The reader captures at most1MiB plus
one overrun byte; that overrun goes to the checker's transport-bound refusal
before JSON parsing. For a complete bounded frame, length and modification
metadata are compared around reading. These checks do not establish a hostile
filesystem race boundary: admitted input, parents and output allocation must
remain stable under an external owner until the command finishes.

The existing checker completes transport, outer shape/version, JSON bounds,
complete program structure/reference/cycle/type checks and argument validation
before even reading the linked foreign globals. Static refusal constructs the
existing exact seven-field `C(result)+LF`, a witness with count0, null native
byte fields, and unavailable identities represented as null. It never calls the
entry. A valid different program, malformed descriptor, input read failure,
unsupported CLI or protocol failure produces a nonzero environment failure.

For a valid bound invocation, the caller prepares regions, calls the single fixed
entry exactly once, captures and decodes its bytes, and constructs the entire
witness before opening its output file. The file is written, flushed and synced
before stdout receives the result. All four complete language observations have
exit0. Write/flush/sync/stdout failure is nonzero; a new partial or complete file
and any partial stdout remain unadmitted evidence. No attempt removes or replaces
such evidence. Stderr carries only a fixed failure message. Native traps, crashes,
unwind or inability to finish are not translated into language outcomes.

The external finite recorder owns whole-file and source/artifact before/after
identity, exact command identity, completion and resource evidence. Witness
fields are observations and cannot grant any authority. No caller boolean claims
conformance, complete output overwriting, artifact identity or input-file stability.

## Complete binding comparison

`native::expected_binding` reconstructs only the canonical embedded data record
from `CheckedProgram` accessors, then `bind` compares the entire raw byte slice
with that reconstruction. It does not parse an unchecked artifact into checked
types or call the LLVM emitter. The compared fields include:

- Schema `bagaev-probe-llvm-binding/1`, semantic `bagaev-probe-ir/1`, LLVM data
  edition21.1, target, baseline CPU, work bound and the complete ABI description.
- All ABI field offsets/widths/types, status/type/reason codes, calling convention,
  signature, symbol, disjointness, alignment and argument slot-location base.
- The complete canonical program bytes and `H(program)`.
- Every sorted function's index/name, signature, body, parameters and local slots,
  and ordered callee map; every structural node's number, function, operation,
  ordered children, type and pointer, including unused code and lazy arms.

Hash equality alone cannot bind. Any extra whitespace/LF/NUL, reordered field,
missing field, changed schema/ABI/map or different canonical program fails before
entry. A successful comparison names the descriptor with SHA-256 of its exact
bytes (`binding_pin`); this is not the LLVM module/object/executable artifact pin.

The accepted producer constructs the same embedded descriptor from the same
read-only accessors, in the same canonical field order, with the same2MiB bound.
The caller uses a2MiB bounded writer and a raw equality comparison over at most
that many bytes. It never routes a descriptor through the transport parser's
smaller1MiB limit. Thus every producer-supported checked program is supported:
there is no reduced function/node/depth limit, unchecked IR constructor, loader,
second program evaluator or test-only widening in production. The independent
source review must check serializer parity; the authored tests alone do not prove
cross-module parity or descriptor-to-machine-code correspondence.

## Memory and unsafe boundary

The safe library owns `#[repr(C, align(8))]` single-array types for64B input and32B
output. All8 input slots are initialized: Int64 uses explicit two's-complement
little-endian bytes, Bool uses exactly0/1 and unused slots are zero. Output is
initialized wholly to the requested `00` or `ff`. Separate nonzero-sized live
local objects give disjoint storage. No Rust struct is overlaid on foreign data;
all decoding is by explicit little-endian offsets. Copies capture64B input
before/after and all32B output. The requested prefill is recorded, without an
unsupported claim that equal-valued bytes prove overwriting.

All unsafe operations are isolated in `native_main::fixed`, excluded by `cfg(test)`
from the source test harness. External artifact admission must establish these
actual prerequisites, which neither a numeric length nor matching JSON proves:

1. The foreign length symbol is initialized immutable u64-compatible storage
   at its required alignment. The binding symbol is non-null, in one readable
   allocation of at least that actual length, immutable for the process lifetime.
   They are data from the admitted fixed producer object, with no colliding or
   substituted definitions. The length read itself already requires that region
   admission. Only then does the caller reject zero, >2MiB or >`isize::MAX` before
   constructing the raw-parts slice. Its returned `'static` lifetime is justified
   by that external lifetime prerequisite, not inferred from descriptor content.
2. The linked entry implements the admitted C ABI, receives those live aligned
   disjoint64/32B regions, returns normally without unwinding, never retains the
   pointers, never accesses outside the regions and introduces no concurrent
   accesses. Foreign out-of-bounds access cannot be made safe by post-call checks.
3. Raw pointers derive from mutable byte-array borrows before casting the input
   pointer to `const int64_t*`. No shared input/output reference survives the call.
   This allows in-bounds accidental input modification to be observed and rejected
   without first violating a live Rust shared borrow. Such mutation remains an
   environment failure. Const in the C signature is not a mutation detector.

The Rust1.93 [type-layout reference](https://doc.rust-lang.org/1.93.0/reference/type-layout.html)
describes array, representation and alignment rules. The unsafe prerequisites
above remain explicit source-review and artifact-admission requirements;
no compiler version, linked symbol region or runtime behavior is certified by
the reference or by matching descriptor data.

## Decoding observed ABI bytes

The decoder reads status0..3 at0, type0..2 at4, signed value at8, unsigned work
at16, reason at24 and location at28. It checks consumed work<=65536. Success
requires reason/location0 and the entry's declared value type; Bool must be0/1.
Int64 accepts every signed64-bit value. Runtime failure requires absent type,
zero stored value, reason9 or10 and a node in the complete checked map. Work-limit
requires work65536. Node location is rendered with `/program` plus its pointer.
Overflow accepts any consumed work within the stated range. The decoder does not
predict a failing operation, reached node or minimum work from the AST.

A complete status3/reason8/type0/value0/work0 with slot0x80000001..0x80000008 is
rendered as invalid-ir at `/arguments/0`..`/arguments/7`, count1 and exit0 even
though JSON validation supplied legal slots. This preserves an incorrect but
well-formed native observation for independent conformance. It does not invent
an additional raw bad-slot call. All failures have null result value/type, and
success has null reason/location. Unknown fields/combinations, invalid node/slot
encodings or changed input bytes are environment failures. The caller never
re-evaluates a failed result or substitutes an expected result.

## Witness format and size proof

`bagaev-probe-native-witness/1` is a distinct canonical record plus LF. It contains
`binding_pin`, `entry_call_count`, `input_after_hex`, `input_before_hex`,
`output_hex`, `prefill`, `program_pin`, `result_wire_bytes`, `result_wire_hex` and
`schema`, in that order. Hex is lowercase, two digits per byte, without prefixes.
The result field encodes the exact result wire including its terminal LF; its
byte count checks decoding. There is no duplicate result/location field, expected
value or conformance verdict. Static refusal uses count0, null identities and
null input/output; native observation uses count1 and complete64/64/32B hex.

The8MiB limit covers the entire <=1MiB invocation domain, including long arbitrary
object keys visited before argument-shape refusal:

1. In the accepted checker's bounds walk, a refused location has at most132 path
   segments: depth133 is rejected before its children are visited. Program bounds
   and later semantic checks are no deeper. Object keys on one path occupy
   disjoint spans in the original frame. For each key, its contribution after
   JSON Pointer escaping and canonical result-string quoting is at most twice its
   original encoded key-content byte count. Raw slash/tilde expand to2; quote and
   backslash already require>=2 input bytes; controls require original2 or6-byte
   escapes and serialize to2 or6; UTF-8 scalars serialize directly. Unicode
   escapes and surrogate pairs cannot increase this ratio. Non-scalar keys use
   the containing path. No key is duplicated within the chosen path.
2. Each array index has at most7 decimal digits because a <=1MiB frame cannot
   contain more than1,048,576 elements. With one slash per segment, the maximum
   added index/separator contribution is132*8=1056. Fixed prefixes, schema/reason/
   status text, quoting, null fields, work0 and LF fit in the conservative4096B
   allowance. Schema/envelope and transport refusals have shorter fixed paths.
   Therefore static `C(result)+LF` <=2*1MiB+4096. Native checked pointers/results
   fit the same bound. An overrun frame has a fixed empty-pointer refusal.
3. Hex doubles those exact wire bytes without JSON re-escaping them. The remaining
   witness keys, two71-byte pins or nulls, call count, prefill, byte-count digits,
   320 native hex digits, quotes, punctuation and LF fit in4096B. The total is
   <=4*1MiB+3*4096=4,206,592B, below8,388,608B. Construction is checked against8MiB
   before any output open. No pointer truncation, result repinning or fallback
   semantic refusal is used to meet the bound.

## Verification boundary

`native_source_tests.rs` authors binding/schema/map mismatches, complete512-node
unused-code mapping, all result statuses and malformed encodings, signed/bool
decoding, both prefills, input mutation, exact CLI/static priorities, long
pointer/hex preservation, bounded input reading and synthetic write/flush errors.
Tests do not link or call a real object, import an oracle, or emit LLVM. The future
frame test creates and removes only a uniquely named temporary regular input;
it does not create `/out` files or launch processes. The [bounded observations](../../../../docs/native-probe-results.md) record
10 passing harness tests. The real linked Rust caller, sync failure,
native memory behavior and process-level result/witness completeness require
later admitted observations and cannot be supplied by source assertions.
