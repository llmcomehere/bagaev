/** Письма об изменении атрибуции статьи. */
import type { Db } from "./db.ts";
import { notifications, people } from "./db.ts";
import type { AppEvent } from "./events.ts";
import { emailOf } from "./people.ts";

export function notifyEdit(db: Db, ev: AppEvent): void {
  const all = people.all(db);
  for (const p of ev.authors) {
    const to = emailOf(all, p);
    if (to === undefined) continue;
    notifications.put(db, { key: `${ev.eventId}:${p}`, to, articleId: ev.article, subject: "Атрибуция статьи изменена" });
  }
}
