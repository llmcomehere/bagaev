# Explicit record-form/2 optional integers

Extend readable pure representation only, over unchanged typed-record/10, with
none.int(), some.int(expr), option.is_some(expr), option.or(option,fallback).
The core retains OptionInt64 typing and lazy fallback semantics. None differs
from Some(0). Existing record-form/1 and its fixed diagnostics/drafts remain
unchanged and refuse the new header. CLI defaults to1; explicit --form2 selects
new representation. No autodetection, native code generation or runtime change.
Freeze exact lowered graphs and values for missing/zero/minimum/presence/lazy
fallback and three syntax refusals, plus actual wrong-type refusal.
