import { reprice, onPriceChanged } from "./api";
import { ShopDb, Outbox } from "./db";
declare const db: ShopDb;
declare const out: Outbox;
const r = reprice(db, out, "x", 1);
onPriceChanged(db, { name: "x", old: 1, new: 2 });
void r;
