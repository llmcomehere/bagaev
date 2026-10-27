# W11. Команда с проверкой

В модуле `shop.api` напишите команду `set_price(name, value)`: записать новую цену товара в `Shop.items`.
- Ошибки — перечисление `PriceError` в том же модуле: `Negative` (цена меньше нуля) и `UnknownItem` (товара нет).
- Остальные поля товара не меняются.

## bagaev

Файл: `shop/api.bag`.

```bagaev
module shop.api
pub type PriceError = enum { Negative, UnknownItem }
pub command set_price(name: String, value: Int64) -> Result<(), PriceError>
```

## TypeScript

Файл: `shop/api.ts`.

```ts
import { ShopDb } from "./db";
import { Result } from "../result";
export type PriceError = "negative" | "unknown-item"
export function setPrice(db: ShopDb, name: string, value: number): Result<void, PriceError>
```
