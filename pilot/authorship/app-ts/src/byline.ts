/** Подпись под статьёй. */
import type { Db } from "./db.ts";
import { articles, people } from "./db.ts";
import type { Article, ArticleId } from "./articles.ts";
import type { Person, PersonId } from "./people.ts";
import { displayName } from "./people.ts";

/** @requires AttributionComplete.complete */
export function byline(a: Article, all: Map<PersonId, Person>): string {
  return displayName(all, a.author);
}

export function bylineOf(db: Db, id: ArticleId): string {
  const a = articles.get(db, id);
  return a === undefined ? "" : byline(a, people.all(db));
}
