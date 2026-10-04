# Handwritten native kernel comparison

This finite experimental C11 baseline implements 23 literal native variants of
`bagaev-probe-ir/1`. Each variant is ordinary handwritten functions and control
flow, with source expression ticks and checked arithmetic. It has no AST
interpreter, generated source, parser, runtime compiler, registry, dynamic
loading or expected-result table. Static-invalid, transport and declarative
recipe cases are outside this slice. Their absence is not a successful result.
The [bounded observations](../../../../docs/native-probe-results.md) record
selected O0/O2/Os ABI execution. They do not establish performance, other probe
families or a general external-library interface.

## Files and explicit selection

`baseline.c` implements the entry; `checked.h` owns work, checked arithmetic and
byte output; `abi.h` declares the ABI and target requirements. `observe.c` is an
independent direct-ABI byte observer that must link statically to one selected entry.
It does not share a language parser, evaluator or result checker.

Compilation must explicitly define `BAGAEV_NATIVE_CASE` as one integer from the
selector table. Missing or unsupported selections have a preprocessing error;
there is no default program or runtime case dispatch. One selected entry is
compiled per object/executable. An artifact's identity must bind the complete
program hash, all source hashes, case selector and optimization mode. A later
caller must not bind that entry to an arbitrary different program. Source
selection and artifact identity do not supply execution authority.

The target is x86_64 Linux, baseline x86-64, system C calling convention and
little-endian byte layout. C11 plus the explicit Clang `__builtin_add_overflow`,
`__builtin_sub_overflow`, `__builtin_mul_overflow` extensions is required.
`checked.h` refuses other compilers or missing builtin feature detection;
unsupported settings must not be silently substituted. The builtins are
documented as defined for all inputs in the official
[Clang checked arithmetic documentation](https://clang.llvm.org/docs/LanguageExtensions.html#checked-arithmetic-builtins).
That documentation does not prove support in an installed compiler.

## Exact source programs

Every complete program has `schema:"bagaev-probe-ir/1"`, `entry:"main"` and the
specified `functions` map. Unless a signature is listed below, the map contains
only `main`, with `params:[]`, `result:"Int64"` and the listed body. These are
fixed literal program descriptions, not defaults accepted at callable ingress.
In bodies below, `MIN` means the JSON integer -9223372036854775808 and `MAX`
means 9223372036854775807; neither is a language symbol. Boolean tokens are JSON
Booleans. The C implementation uses exact Int64 constants for these literals.

| Selector | Literal case | Complete main body (or function map) |
| --- | --- | --- |
| 1 | K-MIN | `["int",MIN]` |
| 2 | K-MAX | `["int",MAX]` |
| 3 | K-ADD | `["add",["int",2],["int",3]]` |
| 4 | K-SUB | `["sub",["int",2],["int",3]]` |
| 5 | K-MUL | `["mul",["int",-3],["int",4]]` |
| 6 | K-EQ | `["eq",["bool",true],["bool",false]]`; result Bool |
| 7 | K-LT | `["lt",["int",MIN],["int",MAX]]`; result Bool |
| 8 | K-LE | `["le",["int",2],["int",2]]`; result Bool |
| 9 | K-NOT | `["not",["bool",true]]`; result Bool |
| 10 | K-LET | `["let","v","Int64",["int",7],["use","v"]]` |
| 11 | K-CALL | `a:{params:[["v","Int64"]],result:"Int64",body:["arg","v"]}`, `main:{params:[],result:"Int64",body:["call","a",["int",9]]}` |
| 12 | K-LOOP-ZERO | `["loop",0,"i","a","Int64",["int",8],["add",["int",MAX],["int",1]]]` |
| 13 | K-LOOP-MAX | `["loop",1024,"i","a","Int64",["int",0],["add",["use","a"],["use","i"]]]` |
| 14 | K-LAZY before | `["if",["bool",false],["add",["int",MAX],["int",1]],["int",4]]` |
| 15 | K-LAZY literal after[0] | `["if",["bool",true],["int",0],["loop",1024,"i","a","Int64",["int",0],["loop",1024,"j","b","Int64",["int",0],["int",0]]]]` |
| 16 | K-OVER-ADD | `["add",["int",MAX],["int",1]]` |
| 17 | K-OVER-SUB | `["sub",["int",MIN],["int",1]]` |
| 18 | K-OVER-MUL | `["mul",["int",MIN],["int",-1]]` |
| 19 | K-LEFT-FAIL | `["add",["sub",["int",MIN],["int",1]],["mul",["int",MAX],["int",2]]]` |
| 20 | K-LOOP-FAIL | `["loop",1024,"i","a","Int64",["int",MAX],["add",["use","a"],["int",1]]]` |
| 21 | K-ABI-BOOL | `["arg","b"]`; params `[["b","Bool"]]`, result Bool |
| 22 | K-ABI-UNUSED | `["int",0]` |
| 23 | K-ABI-VALID | `["if",["arg","b"],["arg","v"],["int",0]]`; params `[["v","Int64"],["b","Bool"]]`, result Int64 |

The after variant changes only the original K-LAZY body; the remaining program
fields are unchanged. Overflow, lazy and loop-failure programs are statically
valid callable programs. Native parameter binding is separate from a callee's
lexical scope: selector 11 calls `native_a(s, argument)`, whose only language
parameter is its own `v`.

## Complete node and pointer map

Numbering is complete body preorder across function IDs in sorted order.
It includes untaken arms and zero-count loop bodies. Except selector 11, `$`
below is `/program/functions/main/body`; each following suffix is appended to
that pointer. The listed order gives nodes 1, 2, ... without gaps. These are
source locations, not expected output records. Binding metadata, literal
metadata, signatures and loop counts are not expression nodes.

| Selectors | Ordered expression pointers |
| --- | --- |
| 1, 2, 21, 22 | `$` |
| 3, 4, 5, 6, 7, 8, 16, 17, 18 | `$`, `$/1`, `$/2` |
| 9 | `$`, `$/1` |
| 10 | `$`, `$/3`, `$/4` |
| 11 | `/program/functions/a/body`, `/program/functions/main/body`, `/program/functions/main/body/2` |
| 12, 13, 20 | `$`, `$/5`, `$/6`, `$/6/1`, `$/6/2` |
| 14 | `$`, `$/1`, `$/2`, `$/2/1`, `$/2/2`, `$/3` |
| 15 | `$`, `$/1`, `$/2`, `$/3`, `$/3/5`, `$/3/6`, `$/3/6/5`, `$/3/6/6` |
| 19 | `$`, `$/1`, `$/1/1`, `$/1/2`, `$/2`, `$/2/1`, `$/2/2` |
| 23 | `$`, `$/1`, `$/2`, `$/3` |

Each reached expression has an explicit sequenced `BAGAEV_TICK` before its
children. Work begins at zero; at 65536 the next tick refuses at its own node
without incrementing. Volatile work accesses preserve the semantic accounting
even if arithmetic or unreachable machine branches are optimized away. All
operands and call arguments are sequenced left to right. Overflow is checked
only after both operands succeed; failure returns immediately through the
handwritten functions. `if` evaluates one arm; loops evaluate initial once and
body for the literal count. Index increments, bindings, assignment and return
have no extra ticks. Signed loop indices only traverse 0..1024. Checked
arithmetic never performs an unchecked overflowing signed C operation and
failure exposes no partial arithmetic value.

## ABI protocol

The entry is `void bagaev_probe_entry(const int64_t arguments[8], void *output)`.
Both caller regions must be non-null, eight-byte aligned, valid for 64/32 bytes
respectively and disjoint; output must be writable. Invalid memory conditions
are outside the callable domain. The entry neither allocates nor retains
pointers. All eight slots are copied through sequenced volatile-qualified
reads before validation or any output write. Validation is one increasing-index
pass: active Bool slots must be 0/1, unused slots zero, active Int64 unrestricted.
Selector 21 has one active Bool; selector 23 has Int64 then Bool; all others
have no active slots. First bad slot returns status 3/reason 8/location
`0x80000001+i`, work zero, absent type and zero value.

Every complete outcome overwrites all 32 output bytes explicitly in
little-endian widths; there is no C struct padding or uninitialized byte:

| Offset / width | Field |
| --- | --- |
| 0 / 4 | status: 0 success, 1 integer-overflow, 2 work-limit, 3 invalid-ir |
| 4 / 4 | type: 0 absent, 1 Int64, 2 Bool |
| 8 / 8 | signed Int64 success value (Bool 0/1); zero on failure |
| 16 / 8 | unsigned semantic work |
| 24 / 4 | reason: 0 success, 8 argument, 9 overflow, 10 work |
| 28 / 4 | zero on success, source node on runtime failure, slot location on argument failure |

The baseline does not accept malformed programs, so it emits no static checker
errors. Node and slot maps supply the later independent driver's pointer
translation; this source does not fabricate language JSON results.

## Direct-ABI observer transport

The exact observer CLI is `--input PATH --prefill 00` or
`--input PATH --prefill ff`, in that order. Both arguments are mandatory; no
stdin or ambient file lookup is used. The named file is opened read-only and
must contain exactly 64 bytes: eight little-endian Int64 slot representations.
An open/read/close failure, short input or extra byte is a nonzero environment
failure before the entry call. Integer decoding avoids out-of-range unsigned
to signed casts. The observer owns separately aligned, disjoint argument and
output arrays and calls the statically linked entry exactly once.

Success emits one bounded ASCII JSON observation, at most 639 bytes including
one LF, with fields in this exact order:

1. `schema`: `bagaev-direct-abi-observation/1`.
2. `input_before_hex`: all 64 supplied bytes as 128 lowercase hex characters.
3. `input_after_hex`: all 64 argument bytes after the call, in the same encoding.
4. `prefill_hex`: the 32 original output bytes as 64 lowercase hex characters.
5. `output_hex`: all 32 actual output bytes as 64 lowercase hex characters.

The two prefills are complementary repeated byte patterns; separate future
calls must select each explicitly. No comparison with an expected value or
language observation is performed. Input mutation and incomplete output
overwrite remain observable in raw bytes. This observer alone cannot prove
the entry's all-eight-slot read order; source review must supply that evidence.
Emission failure is nonzero, with no complete observation claim. Diagnostics
go to stderr. No input file is written, and no subprocess, network, model or
dynamic library is used by the observer source. Execution and resource policy
require a separately reviewed complete tool/runtime closure and recipe.
