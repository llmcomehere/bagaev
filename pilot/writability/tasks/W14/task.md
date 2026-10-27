# W14. Новый вариант перечисления

Добавьте в `Status` вариант `Archived`: подпись `"архив"`, не виден. Остальное поведение не меняется.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub type Status = enum { Draft, Published, Archived }
```

## TypeScript

Файл: `main.ts`.

```ts
export type Status = "draft" | "published" | "archived"
```
