# Readable optional integers

Explicit `record-form/2` adds representations of existing typed-record/10
optional-integer operations. It does not change the core or record-form/1.

```bagaev
bagaev record-form/2;
program {
  entry date_or_default;
  fn date_or_default(date: OptionInt64) -> Int64 =
    option.or(date, 19700101);
}
```

An invocation argument `null` represents absence; an integer, including zero,
represents a present value. `none.int()` constructs absence, `some.int(0)` constructs
present zero, and `option.is_some(value)` checks presence. `option.or(value,
fallback)` evaluates the fallback only when absent. Thus a present zero can avoid
an overflowing fallback. Types and overflow remain enforced by the existing core.
This is optional integer data, not a calendar validator or an omitted record field.

Select `tools/record_text.py decode|encode|prepare|inspect ... --form 2` explicitly.
Default selection remains1; no source autodetection occurs. The existing fixed
pure diagnostics and detached-draft API remain form1-only and refuse the new
header. This slice does not silently expand those interfaces.

Five exact graphs and literal results cover missing/default, present zero/lazy
fallback, Int64 minimum and presence. A wrong-type some.int program is syntactically
convertible but refused RR_TYPE by the core. Three syntax/arity refusals, six old
version refusals and five explicit form2 file calls passed. The earlier converter
suite remains applicable to default1. No runtime, native ABI, performance or
model-choice claim follows from this representation extension.
