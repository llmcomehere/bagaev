/** Комментарии читателей. Автор комментария — не автор статьи. */
import type { Db } from "./db.ts";
import { articles, comments, tx } from "./db.ts";

export function addComment(db: Db, id: string, articleId: string, person: string, text: string): boolean {
  return tx(db, () => {
    if (articles.get(db, articleId) === undefined) return false;
    comments.put(db, { id, articleId, author: person, text });
    return true;
  });
}

export function commentsOf(db: Db, articleId: string): string[] {
  return comments.forArticle(db, articleId).map((c) => c.text);
}
