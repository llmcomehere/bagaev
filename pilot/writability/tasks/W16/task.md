# W16. Новый эффект

Пусть `final_price` вычитает из базовой цены скидку товара из таблицы `Catalog.discounts` (нет записи — скидка 0). Запрос `quote` должен продолжать работать.

## bagaev

Файл: `main.bag`.

```bagaev
module main
pub fn final_price(name: String, base: Int64) -> Int64 (с нужным рядом uses)
pub query quote(name: String, base: Int64) -> Int64
```

## TypeScript

Файл: `main.ts`.

```ts
export function finalPrice(db: CatalogDb, name: string, base: number): number
export function quote(db: CatalogDb, name: string, base: number): number
```
