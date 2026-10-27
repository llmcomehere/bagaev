import { price } from "./api";
import { ShopDb } from "./db";
declare const db: ShopDb;
const p: number | undefined = price(db, "x");
void p;
