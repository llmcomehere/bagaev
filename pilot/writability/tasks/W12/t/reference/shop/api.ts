import { ShopDb, Outbox, PriceChanged } from "./db";
import { Result, ok, err } from "../result";
export function reprice(db: ShopDb, out: Outbox, name: string, value: number): Result<void, string> {
  const it = db.items.get(name);
  if (it === undefined) return err("нет товара");
  db.items.set(name, { ...it, price: value });
  out.emit({ name, old: it.price, new: value });
  return ok(undefined);
}
export function onPriceChanged(db: ShopDb, ev: PriceChanged): void {
  db.history.set(ev.name, [...(db.history.get(ev.name) ?? []), ev.new]);
}
