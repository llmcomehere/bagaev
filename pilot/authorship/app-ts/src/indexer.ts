/** Обработчик события пересчитывает сохранённый индекс «человек → статьи». */
import type { Db } from "./db.ts";
import { authorIndex } from "./db.ts";
import type { AppEvent } from "./events.ts";

/** @implements AttributionComplete.complete */
export function indexAuthorship(db: Db, ev: AppEvent): void {
  const index = authorIndex.all(db);
  for (const [p, ids] of index) index.set(p, ids.filter((a) => a !== ev.article));
  index.set(ev.author, [...(index.get(ev.author) ?? []), ev.article]);
  authorIndex.replaceAll(db, index);
}
