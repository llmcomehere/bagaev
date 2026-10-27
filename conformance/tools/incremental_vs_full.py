#!/usr/bin/env python3
"""Сверка инкрементального и полного извлечения графа (LNK-08-18, links/02 §8, T08-C05).

Цепочка правок примера examples/authorship. После каждой правки граф строится дважды: полностью с нуля и
инкрементально от предыдущего шага. Сравниваются байты BAG-CJSON-1 графа (узлы, рёбра с местами, provenance,
покрытие, пробелы) и ответы прямых и обратных запросов для каждой сущности. Внесение неисправностей: штампы
без импортов (local) и без транзитивных импортов (direct) должны давать расхождение хотя бы на одной правке.

  python3 conformance/tools/incremental_vs_full.py [--json]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))
sys.setrecursionlimit(100000)

from bagaev_ref.kernel import canonical as C  # noqa: E402
from bagaev_ref.links.extract import extract  # noqa: E402
from bagaev_ref.links.graph import Graph, relations  # noqa: E402
from bagaev_ref.links.incremental import extract_incremental  # noqa: E402
from bagaev_ref.machine.runner import prepare  # noqa: E402

APP = ROOT / "examples" / "authorship"


def sub(rel, old, new):
    def edit(root: Path):
        f = root / rel
        s = f.read_text(encoding="utf-8")
        assert s.count(old) >= 1, (rel, old)
        f.write_text(s.replace(old, new), encoding="utf-8")
    return edit


# (имя, правка) — шаги применяются последовательно
EDITS = [
    ("body", sub("blog/byline.bag", '" · "', '" / "')),
    ("rename-same-id", sub("blog/export.bag", "authors_json", "authors_list")),
    ("callee-new-id", sub("blog/people.bag", '@id("kr652t")', '@id("kr652z")')),
    ("type-new-id", sub("blog/authorship.bag", '@id("pcc6s6")', '@id("pcc6s7")')),
    ("add-import-and-call", sub("blog/image.bag", "use std.bytes\n",
                                "use std.bytes\nuse blog.people\n")),
    ("remove-requires", sub("blog/search.bag", "  requires AttributionComplete.complete\n", "")),
    ("remove-handler-call", sub("blog/indexer.bag", "authorship.ids(ev.authors)", "[]")),
    # тип Authors виден в image только через поле Article: модуль authorship image не импортирует
    ("use-through-field", sub("blog/image.bag", "use blog.people\n",
                              'use blog.people\nuse blog.articles\n\n@id("mgx001")\n'
                              'pub fn has_authors(a: articles.Article) -> Bool {\n  let x = a.authors;\n  true\n}\n')),
    ("transitive-type-new-id", sub("blog/authorship.bag", '@id("pcc6s7")', '@id("pcc6s8")')),
]


def load(root: Path):
    files = [(f.relative_to(root).as_posix(), f.read_bytes()) for f in sorted(root.rglob("*.bag"))]
    project, prog, pre = prepare(files)
    assert pre is None, pre
    return project, prog, files


def answers(g: dict) -> dict:
    gr = Graph(g)
    return {n: relations(gr, n) for n in sorted(gr.nodes)}


def run(scope: str) -> list:
    tmp = Path(tempfile.mkdtemp(prefix="bag-inc-"))
    try:
        root = tmp / "app"
        shutil.copytree(APP, root)
        project, prog, files = load(root)
        prev, stamps, _ = extract_incremental(project, prog, files, None, None, scope)
        rows = []
        for name, edit in EDITS + [("extractor-rev-changed", None)]:
            if edit is not None:
                edit(root)
            else:                                        # прежний граф построен другой ревизией извлекателя
                prev = dict(prev, extractor_rev=prev["extractor_rev"] + "-old")
            project, prog, files = load(root)
            full = extract(project, prog, files)
            inc, stamps, redo = extract_incremental(project, prog, files, prev, stamps, scope)
            if edit is None and len(redo) != len({m.name for m in project.user}):
                rows.append({"edit": name, "graph_equal": False, "queries_equal": False, "reextracted": redo})
                continue
            same = C.encode(full) == C.encode(inc)
            same_q = same or answers(full) == answers(inc)
            rows.append({"edit": name, "graph_equal": same, "queries_equal": same_q, "reextracted": redo})
            prev = inc
        return rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    norm = run("transitive")
    faults = {s: run(s) for s in ("local", "direct")}
    rep = {"transitive": norm,
           "faults": {s: {"detected": any(not r["graph_equal"] for r in rows),
                          "first": next((r["edit"] for r in rows if not r["graph_equal"]), None)} for s, rows in faults.items()}}
    ok = all(r["graph_equal"] for r in norm) and all(f["detected"] for f in rep["faults"].values())
    rep["ok"] = ok
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"steps": len(norm), "equal": sum(r["graph_equal"] for r in norm),
                          "faults": rep["faults"], "ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
