# W19. Проверка возраста

Напишите `validate_age`:
- отрицательный → ошибка `Negative`;
- больше 150 → ошибка `TooLarge` с этим значением;
- иначе — само значение.
Ошибки — перечисление `AgeError`.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub type AgeError = enum { Negative, TooLarge(Int64) }
pub fn validate_age(a: Int64) -> Result<Int64, AgeError>
```

## TypeScript

Файл: `main.ts`.

```ts
import { Result } from "./result";
export type AgeError = { readonly kind: "negative" } | { readonly kind: "too-large"; readonly value: number }
export function validateAge(a: number): Result<number, AgeError>
```
