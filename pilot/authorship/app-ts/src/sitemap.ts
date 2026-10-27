/** Карта сайта: адреса статей. */
import type { Db } from "./db.ts";
import { articles } from "./db.ts";

export function sitemap(db: Db): string {
  return articles.all(db).map((a) => `/articles/${a.id}\n`).join("");
}
