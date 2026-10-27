import { ShopDb } from "./db";
export function price(db: ShopDb, name: string): number | undefined {
  return db.items.get(name)?.price;
}
