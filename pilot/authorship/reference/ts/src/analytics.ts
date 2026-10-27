/** Счётчик просмотров статей. */
import type { Db } from "./db.ts";
import { tx, views } from "./db.ts";

export function recordView(db: Db, articleId: string): number {
  return tx(db, () => {
    const n = views.get(db, articleId) + 1;
    views.put(db, articleId, n);
    return n;
  });
}

export function viewsOf(db: Db, articleId: string): number {
  return views.get(db, articleId);
}
