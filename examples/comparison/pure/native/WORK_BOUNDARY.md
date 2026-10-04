# Handwritten work-boundary programs

This source extends the finite native comparison with two fixed literal
`bagaev-probe-ir/1` programs. `work_boundary.c` uses ordinary C11 loops and
scalar bindings with explicit source-expression ticks. It shares the existing
`abi.h` and `checked.h` primitives and links to the independent `observe.c`
byte observer. The existing 23-variant `baseline.c` is a separate entry source;
link exactly one entry implementation into each artifact.

The [bounded observations](../../../../docs/native-probe-results.md) include
these two variants at O0/O2/Os. Performance remains unmeasured. No expected output,
precomputed work total, result table, interpreter or generated backend is
included. The following programs are input descriptions.

## Explicit program selection

Compilation must define `BAGAEV_WORK_COUNT` as exactly `1019` or `1020`.
Missing or other values cause a preprocessing error. There is no default,
runtime selector, implicit argument or environment lookup.

For `BAGAEV_WORK_COUNT=1019`, the complete program is:

```json
{
  "schema": "bagaev-probe-ir/1",
  "entry": "main",
  "functions": {
    "main": {
      "params": [],
      "result": "Int64",
      "body": [
        "let", "v", "Int64",
        ["loop", 1024, "i", "a", "Int64", ["int", 0],
          ["loop", 61, "j", "b", "Int64", ["int", 0], ["int", 0]]],
        ["loop", 1019, "k", "c", "Int64", ["int", 0], ["use", "c"]]
      ]
    }
  }
}
```

For `BAGAEV_WORK_COUNT=1020`, the complete program is:

```json
{
  "schema": "bagaev-probe-ir/1",
  "entry": "main",
  "functions": {
    "main": {
      "params": [],
      "result": "Int64",
      "body": [
        "let", "v", "Int64",
        ["loop", 1024, "i", "a", "Int64", ["int", 0],
          ["loop", 61, "j", "b", "Int64", ["int", 0], ["int", 0]]],
        ["loop", 1020, "k", "c", "Int64", ["int", 0], ["use", "c"]]
      ]
    }
  }
}
```

The entry signature is empty in both programs. `v` is visible only in the let
body after its value succeeds. Each outer-loop body evaluates a fresh inner
loop with its own `j` and `b`; these bindings do not escape. The second loop
binds fresh `k` and `c` and reads its previous accumulator in each body.
The loop indices are bookkeeping values even though these literal bodies do
not reference them. Index increments, accumulator assignments and binding
operations add no semantic ticks.

## Complete source node map

Both programs have the same nine structural expression occurrences. Numbering
is complete body preorder for the sole function `main`. Metadata (operation
names, counts, binder names, types and literal scalars) is not an expression.
The shared `$` prefix below is `/program/functions/main/body`.

| Node | JSON Pointer | Expression |
| --- | --- | --- |
| 1 | `$` | let |
| 2 | `$/3` | outer loop |
| 3 | `$/3/5` | outer initial int |
| 4 | `$/3/6` | inner loop |
| 5 | `$/3/6/5` | inner initial int |
| 6 | `$/3/6/6` | inner body int |
| 7 | `$/4` | second loop |
| 8 | `$/4/5` | second initial int |
| 9 | `$/4/6` | second body use |

Each `BAGAEV_TICK` is a separate sequenced statement immediately before its
expression's value or children. Loop ticks precede their initial value; the
initial expression occurs once per evaluated loop, while body expressions
occur in actual loop iterations. The inner-loop expression is evaluated for
each outer iteration. The let body starts only after the entire outer loop
finishes. There is no early aggregate-bound decision, work multiplication,
constant-work shortcut or artificial boundary refusal.

The unchanged `bagaev_tick` checks the frozen work ceiling before incrementing
and records the current source node if it refuses. Its work field is volatile.
`BAGAEV_TICK` immediately returns from the handwritten function on refusal;
no later expression, assignment or loop is reached, and the recorded failure
is not replaced. The entry serializes that state once through the unchanged
output primitive, which suppresses partial values on failure. This describes
the required mechanism, not an observed outcome for either program.

## Target, ABI and observation

The target is x86_64 Linux, baseline x86-64 CPU, system C calling convention,
little-endian layout, eight-bit bytes and two's-complement Int64. The accepted
headers require C11 and the selected Clang checked-arithmetic interface;
unsupported compiler or target settings must fail without substitution.

The symbol is `bagaev_probe_entry`, with signature
`void bagaev_probe_entry(const int64_t arguments[8], void *output)`.
Caller-owned input and output must be non-null, valid for 64 and 32 bytes,
eight-byte aligned, and disjoint; output is writable. These memory
preconditions are outside the callable language-refusal domain. Pointers are
not retained, input is never written, and the entry exposes no allocation,
callback or dynamic-loading API.

The entry performs all eight volatile slot reads before validation or output.
Both signatures have zero parameters, so every slot must be zero. Validation
uses a separate increasing-index pass before any expression tick; the first
bad unused slot keeps work zero and uses the frozen argument-refusal fields
and slot-location encoding. This introduces no deep validation of language
JSON or host memory-precondition repair.

`bagaev_output` overwrites all 32 bytes using the existing field offsets and
little-endian stores: status at 0, type at 4, scalar bits at 8, work at 16,
reason at 24 and node/slot location at 28. Failure fields retain the existing
absent type/value rule. Native C struct layout is never used as the wire ABI.

The unchanged observer requires an explicit 64-byte input file and explicit
`--prefill 00` or `--prefill ff`. It invokes the linked fixed entry, observes
input after the call through volatile reads, and emits raw before/after,
prefill and output bytes without a language parser or expected-value checker.
Both prefills and input preservation remain future independent observations.

## Artifact and future verification obligations

Each future artifact must bind the complete literal program identity,
`BAGAEV_WORK_COUNT`, all entry/header/observer source hashes, target, exact
toolchain/closure identity, flags, optimization mode and resulting bytes.
The two counts identify different programs; neither artifact may be rebound
to arbitrary other source input. No semantic program hash, expectation or
execution result is generated here.

Future separately admitted compilation must cover each explicit count in
O0, O2 and Os, link `work_boundary.c` with the unchanged observer and headers,
and preserve baseline CPU and tick/first-failure semantics across optimization.
It must not also link `baseline.c`, execute a produced binary during build,
replace unsupported settings, or borrow mutable outputs between admissions.
The previously prepared build profiles are not amended by this source slice;
new source and exact command provenance need separate review and activation.

The source contract defines work and node behavior; a compiler/runtime result
must be compared with independently frozen expectations under a separate
execution admission. Source inspection and source hashes do not establish
native conformance, resource control, measurements or wider probe-family
coverage.
