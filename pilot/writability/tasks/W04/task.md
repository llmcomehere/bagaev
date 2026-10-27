# W04. Сложение десятичных строк

Напишите `add_decimal`: разобрать две строки как десятичные целые и сложить.
- Ошибки — перечисление `AddError`: `BadNumber` со строкой, которую не удалось разобрать, и `Overflow` (переполнение суммы).
- Используйте разбор и проверяемое сложение стандартной библиотеки.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub type AddError = enum { BadNumber(String), Overflow }
pub fn add_decimal(a: String, b: String) -> Result<Int64, AddError>
```

## TypeScript

Файл: `main.ts`.

```ts
import { Result } from "./result";
export type AddError = { readonly kind: "bad-number"; readonly text: string } | { readonly kind: "overflow" }
export function addDecimal(a: string, b: string): Result<number, AddError>
```
