# Missing record dates without confusing zero and null

Explicit `record-form/3` represents the core's existing optional omitted field:

```bagaev
bagaev record-form/3;
program {
  record Entry { id: Int64, date: OptionInt64 omit_none };
  entry date_or_default;
  fn date_or_default(e: Entry) -> Int64 = option.or(e.date, 19700101);
}
```

For `[{"id":1}]`, the date is absent and the fallback is returned.
For `[{"id":1,"date":0}]`, the result is zero. An explicit JSON null for this
omit_none field is refused RR_ARGUMENT by the existing core. This differs from a
plain OptionInt64 argument, where null represents None. An omitted date is not
an invalid calendar date; this representation adds no calendar validation.

`date: OptionInt64 omit_none` maps exactly to the typed metadata
`{"type":"OptionInt64","omit_none":true}`. Only record fields accept this
modifier, and only with OptionInt64. Constructors still need every initializer:
`Entry { id: e.id, date: none.int() }` explicitly clears the field, which is
omitted when the core encodes the returned record. Identity preserves missing
and present values without filling defaults into the record.

Select `tools/record_text.py decode|encode|prepare|inspect ... --form 3`.
Earlier codecs, default1, fixed form1 diagnostics and drafts remain unchanged.
No automatic migration or profile detection is performed. The owned component
boundary, runtime, native ABI and work budgets are not extended by this syntax.

Seven core invocations checked six full results and explicit-null refusal.
Two syntax refusals, malformed encoder metadata, four file-tool calls and five
inherited option graphs were checked, with portable repetition. These are finite
conformance observations, not full catalogue, durability or performance evidence.
