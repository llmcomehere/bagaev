import { ShopDb } from "./db";
import { Result, ok, err } from "../result";
export type PriceError = "negative" | "unknown-item";
export function setPrice(db: ShopDb, name: string, value: number): Result<void, PriceError> {
  if (value < 0) return err("negative");
  const it = db.items.get(name);
  if (it === undefined) return err("unknown-item");
  db.items.set(name, { ...it, price: value });
  return ok(undefined);
}
