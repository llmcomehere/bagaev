# W15. Переименование поля

Переименуйте поле `title` записи `Article` в `name` во всём модуле. Поведение не меняется.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub type Article = record { name: String, words: Int64 }
```

## TypeScript

Файл: `main.ts`.

```ts
export interface Article { readonly name: string; readonly words: number }
```
