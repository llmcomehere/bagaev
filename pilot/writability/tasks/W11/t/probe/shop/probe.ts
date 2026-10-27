import { setPrice, PriceError } from "./api";
import { ShopDb } from "./db";
import { Result } from "../result";
declare const db: ShopDb;
const r: Result<void, PriceError> = setPrice(db, "x", 1);
void r;
