# W13. Контракт, реализация и тест

В модуле `pricing` уже объявлены сущность `Pricing` и контракт `PriceRules` с правилами `non_negative` и `rounding`.
- Напишите `round_price(p)`: отрицательная цена → 0; иначе округление вверх до кратного 10. Объявите, что функция реализует оба правила контракта.
- Напишите тест `round_price_rules`, который проверяет оба правила (не меньше трёх проверок).

## bagaev

Файл: `pricing.bag`.

```bagaev
module pricing
(сохраните entity Pricing и contract PriceRules как есть)
pub fn round_price(p: Int64) -> Int64   — implements PriceRules.non_negative, PriceRules.rounding
test round_price_rules                  — checks PriceRules.non_negative, PriceRules.rounding
```

## TypeScript

Файл: `pricing.ts`.

```ts
/** @implements PriceRules.non_negative, PriceRules.rounding */
export function roundPrice(p: number): number
export function testRoundPriceRules(): void  // бросает Error при нарушении
```
