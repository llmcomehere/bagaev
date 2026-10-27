/** Подписки обработчиков на события: тип события → обработчики по порядку. */
import type { Db } from "./db.ts";
import type { AppEvent } from "./events.ts";
import { indexAuthorship } from "./indexer.ts";
import { notifyEdit } from "./notify.ts";

export interface Handler { name: string; run: (db: Db, ev: AppEvent) => void }

export const HANDLERS: Record<string, Handler[]> = {
  AuthorshipChanged: [
    { name: "indexer.indexAuthorship", run: indexAuthorship },
    { name: "notify.notifyEdit", run: notifyEdit },
  ],
};
