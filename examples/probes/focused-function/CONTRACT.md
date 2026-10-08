# Focused detached function replacement

Fixed form4 API exports one named function plus the existing complete type graph
as a readable fragment. Fragment entry names the selected function; other function
bodies are excluded, so the fragment may intentionally reference external helpers
and is not a standalone executable. Export reports canonical base/function pins.

Replacement requires exact current base and selected-function pins, exactly one
fragment function matching entry and an existing function name, unchanged type
graph and parameter/result signature. Replace only its body in a detached deep
copy; reject no-op and extra functions. Preserve original program entry and all
other functions. Report computed candidate target pin; semantic_check/admission
remain false. No storage, application or evaluator. Target is a result identity,
not an independently approved desired target or a guarantee of business behavior.

Use full catalogue id_ok for a behavior-preserving redundant if and compare all99
old literal responses. Freeze source graph change and refusal expectations before
execution. No model cost/performance claim from fragment byte reduction.
