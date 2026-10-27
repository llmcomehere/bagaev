/** Письма об изменении атрибуции статьи. */
import type { Db } from "./db.ts";
import { notifications, people } from "./db.ts";
import type { AppEvent } from "./events.ts";
import { emailOf } from "./people.ts";

export function notifyEdit(db: Db, ev: AppEvent): void {
  const to = emailOf(people.all(db), ev.author);
  if (to === undefined) return;
  notifications.put(db, { key: `${ev.eventId}:${ev.author}`, to, articleId: ev.article, subject: "Атрибуция статьи изменена" });
}
