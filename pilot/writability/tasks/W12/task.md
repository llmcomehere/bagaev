# W12. Событие и обработчик

В модуле `shop.api`:
- команда `reprice(name, value)`: записать новую цену товара и выпустить событие `PriceChanged` (имя, старая и новая цена); если товара нет — ошибка-строка `"нет товара"`;
- обработчик `on_price_changed` события `PriceChanged`: дописать новую цену в конец истории товара в таблице `Shop.history`.

## bagaev

Файл: `shop/api.bag`.

```bagaev
module shop.api
pub command reprice(name: String, value: Int64) -> Result<(), String>
handler on_price_changed(ev: PriceChanged)
```

## TypeScript

Файл: `shop/api.ts`.

```ts
import { ShopDb, Outbox, PriceChanged } from "./db";
import { Result } from "../result";
export function reprice(db: ShopDb, out: Outbox, name: string, value: number): Result<void, string>
export function onPriceChanged(db: ShopDb, ev: PriceChanged): void
```
