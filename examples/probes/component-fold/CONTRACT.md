# Explicit readable counted fold (candidate form/6)

Scope: representation of the existing typed-record/10 loop, no runtime change.
`fold (COUNT, INITIAL) with (INDEX, ACCUMULATOR) in BODY` lowers to
`["loop", COUNT, INDEX, ACCUMULATOR, INITIAL, BODY]`.
COUNT is a decimal literal 0..1024, never a dynamic count. INITIAL is evaluated
once in outer scope. BODY sees fresh index/accumulator bindings. Index runs
0..COUNT-1; accumulator is previous result. Zero returns INITIAL but BODY
still must typecheck. Core checks freshness and invariant accumulator type.
Form parser refuses equal binding names and out-of-range counts. Other scope
conflicts remain core refusals. Encoder retains exact structural roundtrip.

A 64-step fold with lazy `index < list.len(tags)` guards list.at and computes
aggregate UTF-8 byte count using existing operations, including duplicates.
This does not change TagBox's published source or its append-before-dedup rule.
Old forms remain unchanged; diagnostics/edits/location stay version-bound.
