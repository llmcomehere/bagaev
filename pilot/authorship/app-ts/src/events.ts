/** Событие изменения авторства несёт полный снимок атрибуции. */
import type { ArticleId } from "./articles.ts";
import type { PersonId } from "./people.ts";

export interface AuthorshipChanged {
  type: "AuthorshipChanged";
  eventId: string;
  article: ArticleId;
  author: PersonId;
  revision: number;
}

export type AppEvent = AuthorshipChanged;

/** ID события: `ev_` + ID статьи без подчёркиваний + `_r` + ревизия. */
export function eventId(article: ArticleId, revision: number): string {
  return `ev_${article.replaceAll("_", "")}_r${revision}`;
}
