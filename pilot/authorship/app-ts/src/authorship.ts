/**
 * Авторская атрибуция статьи и её контракты.
 *
 * @entity Authorship — авторская атрибуция статьи: кто указан автором статьи.
 *   Термины: автор, подпись, byline, атрибуция. Не о: совместное редактирование, права редактора, автор комментария.
 * @contract AuthorshipShape about Authorship
 *   @rule single — у статьи ровно один автор
 *   @rule existing — автор — существующий человек
 * @contract AttributionComplete about Authorship
 *   @rule complete — потребитель передаёт атрибуцию полностью
 */
import type { Person, PersonId } from "./people.ts";

export type AuthorError = { kind: "NotExactlyOne" } | { kind: "UnknownPerson"; person: PersonId };

export type Checked<T> = { ok: true; value: T } | { ok: false; error: AuthorError };

/**
 * Проверка запрошенного списка: ровно один существующий человек.
 * @implements AuthorshipShape.single, AuthorshipShape.existing
 */
export function checkAuthor(ids: PersonId[], people: Map<PersonId, Person>): Checked<PersonId> {
  const [first] = ids;
  if (ids.length !== 1 || first === undefined) return { ok: false, error: { kind: "NotExactlyOne" } };
  if (!people.has(first)) return { ok: false, error: { kind: "UnknownPerson", person: first } };
  return { ok: true, value: first };
}
