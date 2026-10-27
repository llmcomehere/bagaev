# W18. Описание вложенного результата

Напишите `describe`: нет значения → `"нет"`; успех → число десятичной записью; ошибка e → `"ошибка: "` и текст e.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub fn describe(r: Option<Result<Int64, String>>) -> String
```

## TypeScript

Файл: `main.ts`.

```ts
import { Result } from "./result";
export function describe(r: Result<number, string> | undefined): string
```
