/** Тесты исходной программы: форма авторства, полнота атрибуции у потребителей, масштабирование. */
import { test } from "node:test";
import { deepEqual, equal } from "node:assert/strict";
import { checkAuthor } from "../src/authorship.ts";
import type { Person } from "../src/people.ts";
import type { Article } from "../src/articles.ts";
import { byline } from "../src/byline.ts";
import { exportArticle } from "../src/export.ts";
import { resize } from "../src/image.ts";

const people = new Map<string, Person>([["p_alina", { id: "p_alina", displayName: "Алина Петрова", email: "alina@blog.test" }]]);
const sample: Article = { id: "a_101", title: "Типы и связи", author: "p_alina", editors: ["u_editor"], revision: 1 };

/** @checks AuthorshipShape.single, AuthorshipShape.existing */
test("single_author_accepted", () => {
  deepEqual(checkAuthor(["p_alina"], people), { ok: true, value: "p_alina" });
});

/** @checks AuthorshipShape.single */
test("two_authors_rejected", () => {
  deepEqual(checkAuthor(["p_alina", "p_alina"], people), { ok: false, error: { kind: "NotExactlyOne" } });
});

/** @checks AuthorshipShape.existing */
test("unknown_author_rejected", () => {
  deepEqual(checkAuthor(["p_missing"], people), { ok: false, error: { kind: "UnknownPerson", person: "p_missing" } });
});

/** @checks AttributionComplete.complete */
test("byline_names_author", () => {
  equal(byline(sample, people), "Алина Петрова");
});

/** @checks AttributionComplete.complete */
test("export_keeps_author", () => {
  deepEqual(JSON.parse(exportArticle(sample, people)),
    { article_id: "a_101", author: { display_name: "Алина Петрова", person_id: "p_alina" }, title: "Типы и связи" });
});

test("resize_nearest", () => {
  const img = { width: 2, height: 2, pixels: [[255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255], [255, 255, 255, 255]] };
  deepEqual(resize(img, 1, 1).pixels, [[255, 0, 0, 255]]);
});
