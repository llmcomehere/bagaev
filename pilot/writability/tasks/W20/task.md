# W20. Удаление повторов

Напишите обобщённую `dedupe`: оставить первое вхождение каждого значения, сохранив порядок.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub fn dedupe<T: Key>(xs: Seq<T>) -> Seq<T>
```

## TypeScript

Файл: `main.ts`.

```ts
export function dedupe<T>(xs: readonly T[]): T[]
```
