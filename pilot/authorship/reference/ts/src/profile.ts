/** Профиль человека: статьи, где он указан автором, по данным статей. */
import type { Db } from "./db.ts";
import { articles } from "./db.ts";
import type { ArticleId } from "./articles.ts";
import type { PersonId } from "./people.ts";

/** @requires AttributionComplete.complete */
export function profileArticles(db: Db, person: PersonId): ArticleId[] {
  return articles.all(db).filter((a) => a.authors.includes(person)).map((a) => a.id);
}
