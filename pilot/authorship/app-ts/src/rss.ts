/** Лента RSS для агрегаторов: заголовок и автор каждой статьи. */
import type { Db } from "./db.ts";
import { articles, people } from "./db.ts";
import { displayName } from "./people.ts";

export function feed(db: Db): string {
  const all = people.all(db);
  return articles.all(db).map((a) =>
    `<item><guid>${a.id}</guid><title>${a.title}</title><author>${displayName(all, a.author)}</author></item>\n`).join("");
}
