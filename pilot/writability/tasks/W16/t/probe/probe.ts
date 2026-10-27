import { quote, CatalogDb } from "./main";
declare const db: CatalogDb;
const n: number = quote(db, "x", 1);
void n;
