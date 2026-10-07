# Explicit expectation correction, not a changed implementation

Original r1 source, literal oracle and failed run remain unchanged. All five value/
refusal observations matched their intended semantics; complete wires matched3/5.
The two decline expectations incorrectly counted a Text literal as only one node.

Pre-existing docs/probe-typed-text.md, Work section, states that a Text literal
reserves its UTF-8 byte length after its entry tick. The unchanged typed_record
NodeKind::Text implementation charges that same amount. negative-quantity is17
ASCII/UTF-8 bytes. Independent derivation: condition4 + if1 + variant1 + record1
+ text-entry1 + text-bytes17 =25. The old expectation8 omitted those17bytes.

This new r2 oracle corrects only those two work fields under the pre-existing
rule. It does not derive business values from a run, alter any source/evaluator,
weaken old source/1 refusal, or erase the failed original. A fresh run against this
explicitly revised oracle can establish the corrected finite observations only.
