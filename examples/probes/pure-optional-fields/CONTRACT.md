# Explicit optional omitted record fields

record-form/3 adds `field: OptionInt64 omit_none` declarations over the existing
{type:OptionInt64,omit_none:true} typed-record/10 field metadata. Only record
fields accept the modifier; plain fields and variants retain their old shape.
Constructors still require every declared initializer: none.int() explicitly
produces omission in output. Existing input semantics distinguish missing,
present integer zero, and forbidden explicit null on an omit_none field.
No runtime/type/owned-state boundary changes. Old forms1/2 remain unchanged.
Freeze full identity, clearing and defaulting results plus explicit null refusal,
wrong modifier type refusal and exact codec roundtrip before execution.
