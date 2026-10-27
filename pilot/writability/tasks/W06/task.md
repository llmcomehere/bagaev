# W06. Обобщённое отображение с эффектами

Напишите `map_all`: применить `f` к каждому элементу и вернуть результаты в том же порядке. Функция `f` может иметь эффекты (например, читать таблицу) — `map_all` должна быть полиморфна по ним. Не используйте `seq.map`: напишите обход сами.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub fn map_all<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e) -> Seq<U> uses e
```

## TypeScript

Файл: `main.ts`.

```ts
export function mapAll<T, U>(xs: readonly T[], f: (x: T) => U): U[]
```
