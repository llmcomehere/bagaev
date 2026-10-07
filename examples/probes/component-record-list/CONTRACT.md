# Explicit form7 pure record-list representation

Represent existing typed-record/10 named record lists without changing runtime
or component-source/2 ownership. Declaration: `list Items of Item capacity 4;`.
Capacity is a literal 0..4. Construct `records.list(Items, Item { value: 3 })`;
fixed records.len/at/push calls use existing arities and immutable semantics.
Declared list identity is preserved; no structural interchange of list types.
All prior form6 expressions remain, with new reserved declaration words.

This enables pure local/helper collections only within the existing component
boundary. State/request/error owned graphs containing record lists still receive
CS_OWNED from the unchanged actual checker. Do not imply catalog state support,
source admission, a new native ABI, dynamic capacity or implicit upgrade.

Freeze exact graphs and literal values before implementation. Include empty,
ordered construction, length, indexed field through let, immutable append and
fold sum, plus syntax arities, reference/type/index and capacity refusal cases.
