# W09. Связный список

Определите рекурсивный список целых и две функции:
- перечисление `IntList` с вариантами `Nil` и `Cons` (узел `IntNode`), запись `IntNode` с полями `head: Int64` и `tail: IntList`;
- `list_sum(l)` — сумма элементов;
- `from_seq(xs)` — список с теми же элементами в том же порядке.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub type IntList = enum { Nil, Cons(IntNode) }
pub type IntNode = record { head: Int64, tail: IntList }
pub fn list_sum(l: IntList) -> Int64
pub fn from_seq(xs: Seq<Int64>) -> IntList
```

## TypeScript

Файл: `main.ts`.

```ts
export type IntList = { readonly kind: "nil" } | { readonly kind: "cons"; readonly head: number; readonly tail: IntList }
export function listSum(l: IntList): number
export function fromArray(xs: readonly number[]): IntList
```
