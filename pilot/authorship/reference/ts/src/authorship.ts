/**
 * Авторская атрибуция статьи и её контракты.
 *
 * @entity Authorship — авторская атрибуция статьи: непустой упорядоченный список существующих людей без повторов.
 *   Термины: автор, подпись, byline, атрибуция. Не о: совместное редактирование, права редактора, автор комментария.
 * @contract AuthorshipShape about Authorship
 *   @rule nonempty — у статьи хотя бы один автор
 *   @rule existing — каждый автор — существующий человек
 *   @rule unique — повторов нет
 *   @rule ordered — порядок задаёт редактор и он сохраняется
 * @contract AttributionComplete about Authorship
 *   @rule complete — потребитель передаёт атрибуцию полностью
 */
import type { Person, PersonId } from "./people.ts";

export type AuthorError =
  | { kind: "Empty" }
  | { kind: "Duplicate"; person: PersonId }
  | { kind: "UnknownPerson"; person: PersonId };

export type Checked<T> = { ok: true; value: T } | { ok: false; error: AuthorError };

/**
 * Проверка запрошенного списка: непустой упорядоченный список существующих людей без повторов.
 * @implements AuthorshipShape.nonempty, AuthorshipShape.existing, AuthorshipShape.unique, AuthorshipShape.ordered
 */
export function checkAuthors(ids: PersonId[], people: Map<PersonId, Person>): Checked<PersonId[]> {
  if (ids.length === 0) return { ok: false, error: { kind: "Empty" } };
  const seen: PersonId[] = [];
  for (const p of ids) {
    if (seen.includes(p)) return { ok: false, error: { kind: "Duplicate", person: p } };
    if (!people.has(p)) return { ok: false, error: { kind: "UnknownPerson", person: p } };
    seen.push(p);
  }
  return { ok: true, value: seen };
}

/** Имена авторов через разделитель в порядке атрибуции. */
export function names(ids: PersonId[], all: Map<PersonId, Person>, sep: string): string {
  return ids.map((p) => all.get(p)?.displayName ?? p).join(sep);
}
