#!/usr/bin/env python3
"""Проверка оракула мутантами эталонного решения (Ф7): каждая заведомая ошибка изменения должна дать FAIL хотя бы
одной из ожидаемых проверок, эталон без порчи — PASS. Дефекты C04, C05, C09 — из mutant_examples фикстуры;
остальные — пропущенные потребители и ослабленные правила того же изменения.

  python3 pilot/authorship/oracle/mutants.py [--arm C]

Мутант — копия эталона варианта во временном каталоге с одной текстовой заменой; файлы репозитория не меняются.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("pilot_oracle", Path(__file__).with_name("run.py"))
oracle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oracle)

# вариант → [(имя, случай фикстуры, файл, фрагмент, замена, ожидаемые проваленные проверки — хотя бы одна)]
MUTANTS = {
    "C": [
        ("export_first_author_only", "C04", "blog/export.bag",
         '"{\\"article_id\\":" ++ json.quote(articles.id_text(a.id))',
         'let a = Article { ..a, authors: option.value_or(seq.slice(a.authors, 0, 1) |> result_to_option, a.authors) }; '
         '"{\\"article_id\\":" ++ json.quote(articles.id_text(a.id))', ["export-a_101"]),
        ("export_old_constant", "C05", "blog/export.bag",
         '"{\\"article_id\\":" ++ json.quote(articles.id_text(a.id))',
         '"{\\"article_id\\":\\"a_101\\",\\"author\\":{\\"display_name\\":\\"Алина Петрова\\",\\"person_id\\":\\"p_alina\\"},'
         '\\"title\\":\\"Типы и связи\\"}" ++ ""', ["export-a_101", "export-a_102"]),
        ("index_not_updated", "C09", "blog/indexer.bag",
         "store.replace_all(Blog.author_index, seq.fold(ev.authors, index,",
         "store.replace_all(Blog.author_index, seq.fold([], store.all(Blog.author_index),",
         ["state-d3-after-delivery", "search-p_boris"]),
        ("index_first_author_only", "C09", "blog/indexer.bag", "seq.fold(ev.authors, index,",
         "seq.fold(option.value_or(option.map(seq.get(ev.authors, 0), fn(p) => [p]), []), index,",
         ["state-d3-after-delivery", "search-p_alina"]),
        ("index_only_adds", "C09", "blog/indexer.bag",
         "let index = remove_article(store.all(Blog.author_index), ev.article);\n"
         "store.replace_all(Blog.author_index, seq.fold(ev.authors, index, fn(acc, p) => map.put(acc, p, "
         "seq.append(option.value_or(map.get(acc, p), []), ev.article))));",
         "let index = store.all(Blog.author_index);\n"
         "store.replace_all(Blog.author_index, seq.fold(ev.authors, index, fn(acc, p) => map.put(acc, p, "
         "seq.append(without(option.value_or(map.get(acc, p), []), ev.article), ev.article))));",
         ["replacement-state", "author-removed-from-index"]),
        ("byline_first_author", "C01", "blog/byline.bag", 'authorship.names(a.authors, all_people, " · ")',
         'authorship.names(option.value_or(option.map(seq.get(a.authors, 0), fn(p) => [p]), []), all_people, " · ")',
         ["byline-a_101"]),
        ("profile_first_author", "C01", "blog/profile.bag", "seq.fold(e.value.authors, false,",
         "seq.fold(option.value_or(option.map(seq.get(e.value.authors, 0), fn(p) => [p]), []), false,",
         ["profile-p_alina"]),
        ("rss_first_author", "C01", "blog/rss.bag", 'authorship.names(a.authors, all, " · ")',
         'authorship.names(option.value_or(option.map(seq.get(a.authors, 0), fn(p) => [p]), []), all, " · ")',
         ["hidden-rss-authors"]),
        ("notify_first_author", "C01", "blog/notify.bag", "seq.fold(ev.authors, (),",
         "seq.fold(option.value_or(option.map(seq.get(ev.authors, 0), fn(p) => [p]), []), (),",
         ["hidden-notify-all-authors"]),
        ("duplicates_allowed", "C02", "blog/authorship.bag",
         "Some(p) => if seq.fold(seen, false, fn(acc, q) => acc or q == p) {",
         "Some(p) => if false {", ["invalid-duplicate_author"]),
        ("authors_grant_edit", "C03", "blog/editor.bag",
         "seq.fold(a.editors, false, fn(acc, e) => acc or e == actor)",
         "seq.fold(a.editors, false, fn(acc, e) => acc or e == actor) or actors.id_text(actor) == \"u_boris\"",
         ["coauthor-not-editor"]),
        ("migration_drops_editors", "C01", "blog/migration.bag", "editors: old.editors,", "editors: [],",
         ["c01-migration-d1"]),
        ("order_lost", "C01", "blog/authorship.bag", "scan(ids, people, i + 1, seq.append(seen, p))",
         "scan(ids, people, i + 1, seq.concat([p], seen))", ["state-d2-before-delivery", "byline-a_101"]),
    ],
}

MUTANTS["A"] = [
    ("export_first_author_only", "C04", "src/export.ts", "authors: a.authors.map(", "authors: a.authors.slice(0, 1).map(",
     ["export-a_101"]),
    ("export_old_constant", "C05", "src/export.ts", "return JSON.stringify({",
     'return \'{"article_id":"a_101","author":{"display_name":"Алина Петрова","person_id":"p_alina"},"title":"Типы и связи"}\'; '
     'JSON.stringify({', ["export-a_101", "export-a_102"]),
    ("index_not_updated", "C09", "src/indexer.ts", "  authorIndex.replaceAll(db, index);", "  void index;",
     ["state-d3-after-delivery", "search-p_boris"]),
    ("index_first_author_only", "C09", "src/indexer.ts", "for (const p of ev.authors)", "for (const p of ev.authors.slice(0, 1))",
     ["state-d3-after-delivery", "search-p_alina"]),
    ("index_only_adds", "C09", "src/indexer.ts",
     "for (const [p, ids] of index) index.set(p, ids.filter((a) => a !== ev.article));\n"
     "for (const p of ev.authors) index.set(p, [...(index.get(p) ?? []), ev.article]);",
     "for (const p of ev.authors) index.set(p, [...new Set([...(index.get(p) ?? []), ev.article])]);",
     ["replacement-state", "author-removed-from-index"]),
    ("byline_first_author", "C01", "src/byline.ts", 'names(a.authors, all, " · ")', 'names(a.authors.slice(0, 1), all, " · ")',
     ["byline-a_101"]),
    ("profile_first_author", "C01", "src/profile.ts", "a.authors.includes(person)", "a.authors[0] === person",
     ["profile-p_alina"]),
    ("rss_first_author", "C01", "src/rss.ts", 'names(a.authors, all, " · ")', 'names(a.authors.slice(0, 1), all, " · ")',
     ["hidden-rss-authors"]),
    ("notify_first_author", "C01", "src/notify.ts", "for (const p of ev.authors)", "for (const p of ev.authors.slice(0, 1))",
     ["hidden-notify-all-authors"]),
    ("duplicates_allowed", "C02", "src/authorship.ts",
     'if (seen.includes(p)) return { ok: false, error: { kind: "Duplicate", person: p } };', "", ["invalid-duplicate_author"]),
    ("authors_grant_edit", "C03", "src/editor.ts", "return a.editors.includes(actor);",
     'return a.editors.includes(actor) || actor === "u_boris";', ["coauthor-not-editor"]),
    ("migration_drops_editors", "C01", "src/migrations.ts", "json_array(author_id), editor_ids, revision",
     "json_array(author_id), '[]', revision", ["c01-migration-d1"]),
    ("order_lost", "C01", "src/authorship.ts", "    seen.push(p);", "    seen.unshift(p);",
     ["state-d2-before-delivery", "byline-a_101"]),
]
MUTANTS["B"] = MUTANTS["A"]

# помощники, нужные некоторым заменам (вставляются в начало модуля после use)
HELPERS = {
    "export_first_author_only": ("blog/export.bag", "use std.seq", "use std.seq\nuse std.option\nuse std.result",
                                 "result_to_option", None),
    "index_first_author_only": None, "byline_first_author": ("blog/byline.bag", "use std.store", "use std.store\nuse std.seq\nuse std.option", None, None),
    "profile_first_author": ("blog/profile.bag", "use std.seq", "use std.seq\nuse std.option", None, None),
    "rss_first_author": ("blog/rss.bag", "use std.seq", "use std.seq\nuse std.option", None, None),
    "notify_first_author": ("blog/notify.bag", "use std.seq", "use std.seq\nuse std.option", None, None),
}


def wsub(text: str, old: str, new: str) -> str:
    rx = re.sub(r"(\\\s)+", r"\\s+", re.escape(old))
    found = re.findall(rx, text)
    assert len(found) == 1, (old[:60], len(found))
    return re.sub(rx, lambda m: new, text)


def inject(arm: str, name: str, source: Path, target: Path) -> dict:
    """Точечный дефект подготовленного приложения; несовпавший шаблон — ошибка стенда.

    Используется mechanism и харнессом. Эталоны/ожидания в результат не возвращаются.
    """
    _, case, rel, old, new, _ = next(m for m in MUTANTS[arm] if m[0] == name)
    shutil.copytree(source, target)
    f = target / rel
    before = f.read_bytes()
    text = wsub(before.decode("utf-8"), old, new)
    helper = HELPERS.get(name) if arm == "C" else None
    if helper:
        text = wsub(text, helper[1], helper[2])
    if arm == "C" and name == "export_first_author_only":
        text = text.replace("option.value_or(seq.slice(a.authors, 0, 1) |> result_to_option, a.authors)",
                            "option.value_or(option.map(seq.get(a.authors, 0), fn(p) => [p]), [])")
    f.write_text(text, encoding="utf-8")
    return {"case": case, "name": name, "path": rel, "before": hashlib.sha256(before).hexdigest(),
            "after": hashlib.sha256(f.read_bytes()).hexdigest()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="C")
    a = ap.parse_args()
    spec = json.loads((ROOT / "pilot/authorship/arms.json").read_text(encoding="utf-8"))["arms"][a.arm]
    ref = ROOT / spec["reference"]
    base = oracle.run(a.arm)
    report = {"reference": base["outcome"], "mutants": {}}
    with tempfile.TemporaryDirectory(prefix="bag-oracle-mut-") as tmp:
        for name, case, rel, old, new, expect in MUTANTS[a.arm]:
            d = Path(tmp) / name
            inject(a.arm, name, ref, d)
            out = oracle.run(a.arm, candidate=d)
            hit = sorted(set(expect) & set(out["failed"]))
            valid = out["passed"] > 0                  # мутант собирается и проходит засев: провал — от дефекта
            report["mutants"][name] = {"case": case, "caught": bool(hit) and valid, "valid": valid, "expected": expect,
                                       "failed": out["failed"][:6]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok = base["outcome"] == "PASS" and all(m["caught"] for m in report["mutants"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
