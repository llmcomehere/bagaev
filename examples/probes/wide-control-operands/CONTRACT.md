# Form5 control-expression operands

A real encode failure blocked the independent batch-total edit: an addition
whose left operand is fold was printed without grouping that operand, so the
following addition became part of the fold body. The final roundtrip guard
correctly refused FORM_PROFILE. Never disable or weaken that guard.

Freeze literal graphs for loop/if/let/match as arithmetic/comparison operands
before changing the encoder. Parenthesize only control-expression operands
(loop, if, let, match) inside add/sub/mul/lt. Preserve codec grammar, graph,
runtime semantics, old codecs and unrelated output bytes. No execution control.
Verify exact graph roundtrip and retain the before-fix refusal/difference.
This is independent of PR169's optional context fields; keep that candidate
unchanged while its merge approval is pending.
