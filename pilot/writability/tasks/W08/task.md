# W08. Адрес почты как непрозрачный тип

Определите непрозрачный тип `Email` поверх строки:
- `make_email(s)` возвращает значение, только если в строке есть символ `@` (код 64), иначе — отсутствие значения;
- `email_text(e)` возвращает исходную строку.
Код вне модуля не должен иметь возможности создать `Email` в обход проверки.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub type Email = opaque String
pub fn make_email(s: String) -> Option<Email>
pub fn email_text(e: Email) -> String
```

## TypeScript

Файл: `main.ts`.

```ts
export type Email = string & { readonly __brand: "Email" }
export function makeEmail(s: string): Email | undefined
export function emailText(e: Email): string
```
