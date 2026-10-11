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
callee declaration is absent. Old form5 behavior remains unchanged. This slice
adds no command-line flags: form6 `--callee-context` remains unsupported by the
existing CLI and discovery snapshots. Selecting this API is explicit.

Three new tests passed on2026-10-11: literal declaration-order lowering with an
unchanged helper, base/function pin and scope/signature/no-op refusals, and five
mixed/unknown/duplicate/missing-argument or unknown-callee refusals. Four existing
form5 contextual-fragment tests also passed. No runtime, native or model calls
were made; these finite checks do not establish model benefit or admission.
