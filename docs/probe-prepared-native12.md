# Candidate source-once Json native12 boundary

This additive experimental API combines the accepted prepared reference12
calling convention with the separately qualified native12 input/adapter path.
It does not upgrade old profiles or admit arbitrary native code.

`prepared_json_native_v12::prepare` owns checked12 Json source and its exact
binding/result graph. `evaluate` accepts a raw JSON argument array, actual
per-call scratch slices, the source binding and a separately admitted unsafe
kernel. Source is checked once; arguments retain conceptual-frame/value/depth
bounds and Boolean-preserving input12 ownership. Binding and actual slice checks
precede dispatch. Per-call arenas/output start fresh. Result bytes are owned
before releasing temporary inputs and scratch. No allocation/speed claim follows.

## Actual bounded evidence, 2026-10-11

Four Rust test functions passed with warnings denied, including the inherited
SHA test. A fixed reviewed Boolean callback preserves true/false, repeats with
fresh work and retains output after handle release. Wrong source version,
non-Json signature, Json result, wrong binding, malformed/nonarray/wrong-arity
arguments and short scratch refuse; the six per-call refusals dispatch zero times.
These fixed callbacks are distinct from emitted native execution.

Five already reviewed exact kernels,47 existing Boolean/application cases,
O0/O2, two fills and two calls per prepared source produced376 complete matching
native outputs. Both repeats matched byte-for-byte. Input snapshots, scratch
guards and unused tails held. These repeat the same47 semantic cases, not376
independent cases. [Observations](../examples/probes/record-json-bool/prepared-native12-observations.json)
retain full expected results and all replay identities.

Preparation corrections: one initial old-version refusal fixture accidentally
used valid version12; only its version was corrected. The first native replay
normalized raw arguments through JSON reserialization, turning -0 into0 and
changing logical work418 versus420. That mismatch was rejected. The corrected
preparation retains exact argument lexemes; expected outputs and runtime code
were unchanged. The reported376 matches are from the corrected full replay.

Same-maintainer evidence, not independent reproduction, general backend proof,
hostile-pointer isolation, model benefit or production acceptance. Separate
exact-head review and passing CI remain required. Old APIs are unchanged.

## Focused form6 change/export experiment

The candidate from the separate focused form6 change/export slice was also
compiled and checked through this boundary. Its main body is wrapped by
if true then B else B. The23-case oracle was already frozen before the earlier
reference replay: same business values/helper overflow locations, exactly+2work.
The reviewed changed module matched all184 complete native outputs atO0/O2,
two fills and two repeats. Raw argument lexemes and the oracle hash were
preserved. Input/scratch guards and repeated wire equality held.

The public observations include source/module/oracle identities and complete
results. This cross-PR experiment does not accept the pending authoring PRs,
add new semantic cases or establish unchanged-work equivalence.
