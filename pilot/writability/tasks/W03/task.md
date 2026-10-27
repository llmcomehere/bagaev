# W03. Фигуры

Определите типы и функцию площади:
- запись `Size` с целыми полями `w` и `h`;
- перечисление `Shape` с вариантами `Circle` (радиус, целое) и `Rect` (размер `Size`);
- функция `area`: для круга `3 * r * r`, для прямоугольника `w * h`.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub type Size = record { w: Int64, h: Int64 }
pub type Shape = enum { Circle(Int64), Rect(Size) }
pub fn area(s: Shape) -> Int64
```

## TypeScript

Файл: `main.ts`.

```ts
export interface Size { readonly w: number; readonly h: number }
export type Shape = { readonly kind: "circle"; readonly r: number } | { readonly kind: "rect"; readonly size: Size }
export function area(s: Shape): number
```
