# Pinned named-callee fragments, form6 library

`src/bagaev_record_json_bool_callee.py` adds the explicit data-only
`replace_in_context(source, replacement, base_sha256=..., function_sha256=...)`
library route. The complete base graph pin is checked before reading the
fragment in that context. Only declared parameter names are supplied to named
call lowering; helper bodies are not copied into the fragment.

For helper(a:Json,fallback:Bool), a fragment call
`helper(fallback:true,a:x)` lowers arguments in declaration order: x, then true.
The unchanged focused receiver reconstructs the detached draft, checks the
old function pin, single-body scope, signatures and no-op refusal. Changes to
helper parameter order invalidate an old base pin. This is syntax/lowering and
draft consistency, not semantic checking or programme execution.

The ordinary standalone form6 replacement still refuses named calls whose
callee declaration is absent. Old form5 behavior remains unchanged.

The explicit command is `tools/record_function.py replace SOURCE --form 6
--callee-context --replacement FRAGMENT --base BASE --function-pin FUNCTION
--output NEW_FILE`. Both pins are mandatory. The receipt records
`callee_context_base`; semantic checking and execution admission remain false.
Inputs must be bounded regular files and output must be a fresh path. Invalid
context/extract selectors refuse before input reads. Stale pins and malformed
named calls create no output. Discovery revisions are historical snapshots and
are not extended by this command change. Contextual fragment export is outside
this route.

Three new tests passed on2026-10-11: literal declaration-order lowering with an
unchanged helper, base/function pin and scope/signature/no-op refusals, and five
mixed/unknown/duplicate/missing-argument or unknown-callee refusals. Four existing
form5 contextual-fragment tests also passed. No runtime, native or model calls
were made; these finite checks do not establish model benefit or admission.
