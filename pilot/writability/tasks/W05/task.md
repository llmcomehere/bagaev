# W05. Подсчёт по условию

Напишите обобщённую `count_if`: сколько элементов последовательности удовлетворяют предикату `p`.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub fn count_if<T>(xs: Seq<T>, p: fn(T) -> Bool) -> Int64
```

## TypeScript

Файл: `main.ts`.

```ts
export function countIf<T>(xs: readonly T[], p: (x: T) => boolean): number
```
