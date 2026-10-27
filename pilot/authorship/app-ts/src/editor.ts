/**
 * Редактор авторства: одна транзакция. Успех фиксирует статью и событие в outbox; отказ не меняет данные.
 * Повтор с тем же ключом идемпотентности возвращает прежний ответ.
 */
import type { Db } from "./db.ts";
import { actors, articles, people, receipts, tx } from "./db.ts";
import type { Article } from "./articles.ts";
import type { ActorId } from "./actors.ts";
import type { AuthorError } from "./authorship.ts";
import { checkAuthor } from "./authorship.ts";
import { emit } from "./bus.ts";
import { eventId } from "./events.ts";

export interface SetAuthorsCommand {
  command_id: string;
  idempotency_key: string;
  actor_id: string;
  article_id: string;
  expected_article_revision: number;
  author_ids: string[];
}

export type SetAuthorsResult =
  | { status: "ok"; article_revision: number }
  | { status: "rejected"; code: string };

/** Право правки даёт только список редакторов статьи, а не авторство. */
export function canEdit(a: Article, actor: ActorId): boolean {
  return a.editors.includes(actor);
}

/** Код отказа по общему CLI-контракту пилота. */
export function authorErrorCode(e: AuthorError): string {
  switch (e.kind) {
    case "NotExactlyOne":
      return "EXACTLY_ONE_AUTHOR";
    case "UnknownPerson":
      return "UNKNOWN_PERSON";
  }
}

function apply(db: Db, cmd: SetAuthorsCommand): SetAuthorsResult {
  const old = articles.get(db, cmd.article_id);
  if (old === undefined) return { status: "rejected", code: "NOT_FOUND" };
  if (actors.get(db, cmd.actor_id) === undefined || !canEdit(old, cmd.actor_id)) {
    return { status: "rejected", code: "PERMISSION_DENIED" };
  }
  if (old.revision !== cmd.expected_article_revision) return { status: "rejected", code: "STALE_REVISION" };
  const checked = checkAuthor(cmd.author_ids, people.all(db));
  if (!checked.ok) return { status: "rejected", code: authorErrorCode(checked.error) };
  const updated: Article = { ...old, author: checked.value, revision: old.revision + 1 };
  articles.put(db, updated);
  emit(db, { type: "AuthorshipChanged", eventId: eventId(updated.id, updated.revision), article: updated.id,
    author: updated.author, revision: updated.revision });
  return { status: "ok", article_revision: updated.revision };
}

/**
 * @requires AuthorshipShape.single, AuthorshipShape.existing
 */
export function setAuthors(db: Db, cmd: SetAuthorsCommand): SetAuthorsResult & { replayed: boolean } {
  const request = JSON.stringify(cmd);
  return tx(db, () => {
    const prior = receipts.get(db, cmd.idempotency_key);
    if (prior !== undefined) {
      if (prior.request !== request) return { status: "rejected", code: "IDEMPOTENCY_CONFLICT", replayed: false };
      return { ...(JSON.parse(prior.response) as SetAuthorsResult), replayed: true };
    }
    const result = apply(db, cmd);
    receipts.put(db, cmd.idempotency_key, { request, response: JSON.stringify(result) });
    return { ...result, replayed: false };
  });
}
