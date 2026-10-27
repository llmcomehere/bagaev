/** Поиск статей по человеку: читает сохранённый индекс, порядок — по ID статьи. */
import type { Db } from "./db.ts";
import { authorIndex } from "./db.ts";
import type { ArticleId } from "./articles.ts";
import type { PersonId } from "./people.ts";

/** @requires AttributionComplete.complete */
export function articlesBy(db: Db, person: PersonId): ArticleId[] {
  return [...new Set(authorIndex.all(db).get(person) ?? [])].sort();
}
