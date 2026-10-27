# W10. Запрос к хранилищу

В модуле `shop.api` напишите точку входа-запрос `price`: цена товара по имени из таблицы `Shop.items` модуля `shop.db`; если товара нет — отсутствие значения.

## bagaev

Файл: `shop/api.bag`.

```bagaev
module shop.api
pub query price(name: String) -> Option<Int64>
```

## TypeScript

Файл: `shop/api.ts`.

```ts
import { ShopDb } from "./db";
export function price(db: ShopDb, name: string): number | undefined
```
