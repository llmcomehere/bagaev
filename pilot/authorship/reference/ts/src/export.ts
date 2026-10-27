/** Экспорт статьи в JSON для внешних систем. */
import type { Db } from "./db.ts";
import { articles, people } from "./db.ts";
import type { Article, ArticleId } from "./articles.ts";
import type { Person, PersonId } from "./people.ts";
import { displayName } from "./people.ts";

/** @requires AttributionComplete.complete */
export function exportArticle(a: Article, all: Map<PersonId, Person>): string {
  return JSON.stringify({
    article_id: a.id,
    authors: a.authors.map((p) => ({ display_name: displayName(all, p), person_id: p })),
    title: a.title,
  });
}

export function exportOf(db: Db, id: ArticleId): string {
  const a = articles.get(db, id);
  return a === undefined ? "" : exportArticle(a, people.all(db));
}
