/** Тесты программы: форма списка авторов, полнота атрибуции у потребителей, масштабирование. */
import { test } from "node:test";
import { deepEqual, equal } from "node:assert/strict";
import { checkAuthors } from "../src/authorship.ts";
import type { Person } from "../src/people.ts";
import type { Article } from "../src/articles.ts";
import { byline } from "../src/byline.ts";
import { exportArticle } from "../src/export.ts";
import { resize } from "../src/image.ts";

const people = new Map<string, Person>([
  ["p_alina", { id: "p_alina", displayName: "Алина Петрова", email: "alina@blog.test" }],
  ["p_boris", { id: "p_boris", displayName: "Борис Соколов", email: "boris@blog.test" }],
]);
const sample: Article = { id: "a_101", title: "Типы и связи", authors: ["p_boris", "p_alina"], editors: ["u_editor"], revision: 2 };

/** @checks AuthorshipShape.nonempty, AuthorshipShape.existing, AuthorshipShape.unique, AuthorshipShape.ordered */
test("authors_accepted_in_order", () => {
  deepEqual(checkAuthors(["p_boris", "p_alina"], people), { ok: true, value: ["p_boris", "p_alina"] });
});

/** @checks AuthorshipShape.nonempty */
test("empty_rejected", () => {
  deepEqual(checkAuthors([], people), { ok: false, error: { kind: "Empty" } });
});

/** @checks AuthorshipShape.unique */
test("duplicate_rejected", () => {
  deepEqual(checkAuthors(["p_alina", "p_alina"], people), { ok: false, error: { kind: "Duplicate", person: "p_alina" } });
});

/** @checks AuthorshipShape.existing */
test("unknown_author_rejected", () => {
  deepEqual(checkAuthors(["p_missing"], people), { ok: false, error: { kind: "UnknownPerson", person: "p_missing" } });
});

/** @checks AttributionComplete.complete */
test("byline_lists_all_authors", () => {
  equal(byline(sample, people), "Борис Соколов · Алина Петрова");
});

/** @checks AttributionComplete.complete */
test("export_keeps_all_authors", () => {
  deepEqual(JSON.parse(exportArticle(sample, people)), {
    article_id: "a_101",
    authors: [{ display_name: "Борис Соколов", person_id: "p_boris" }, { display_name: "Алина Петрова", person_id: "p_alina" }],
    title: "Типы и связи",
  });
});

test("resize_nearest", () => {
  const img = { width: 2, height: 2, pixels: [[255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255], [255, 255, 255, 255]] };
  deepEqual(resize(img, 1, 1).pixels, [[255, 0, 0, 255]]);
});
