"""Подкоманды связей (spec/links/08-bagaev-extraction.md §7): `bag graph`, `bag relations`, `bag impact`,
`bag context`, `bag why`. Только чтение: программа не исполняется (кроме явного --with-tests, где тесты идут на
хранилищах в памяти, HST-18), файлы не пишутся (кроме явного `bag graph --save`)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def emit(obj, a) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=None if getattr(a, "json", False) else 2))


def load(root: str, side: str = ""):
    """(Graph, файлы, PRELAUNCH или None) для корня проекта."""
    from bagaev_ref.cli import project_files
    from bagaev_ref.links.extract import extract
    from bagaev_ref.links.graph import Graph
    from bagaev_ref.machine.runner import prepare
    files = project_files(root)
    if files is None:
        return None, None, {"outcome": "PRELAUNCH", "error": f"корень проекта {root} не каталог"}
    project, prog, pre = prepare(files)
    if pre is not None:
        return None, None, pre
    return Graph(extract(project, prog, files), side), dict(files), None


def evidence_for(root: str) -> dict:
    """Результаты тестов кандидата как свидетельства для D83(a): имя теста → PASS/FAIL/ERROR/SKIP."""
    from bagaev_ref.cli import project_files
    from bagaev_ref.machine.runner import run_tests
    obs = run_tests(project_files(root))
    return {t["test"]: t["status"] for t in obs.get("tests", [])}


def report(a):
    from bagaev_ref.links.impact import impact
    b, bf, pre = load(a.base, "base")
    if pre is not None:
        return None, None, None, None, None, dict(pre, side="base")
    c, cf, pre = load(a.candidate, "candidate")
    if pre is not None:
        return None, None, None, None, None, dict(pre, side="candidate")
    from bagaev_ref.links.graph import resolve
    unavailable = []
    for x in [x for x in (a.unavailable or "").split(",") if x]:      # EntityId или полное имя (§7)
        eid = resolve(c, x) or resolve(b, x)
        if eid is None:
            return None, None, None, None, None, {"outcome": "REFUSED", "code": "UNKNOWN_ENTITY", "data": {"entity": x}}
        unavailable.append(eid)
    ev = evidence_for(a.candidate) if getattr(a, "with_tests", False) else None
    budget = getattr(a, "analysis_budget", None)
    return impact(b, c, budget, unavailable, ev), b, c, bf, cf, None


def cmd_graph(a) -> int:
    from bagaev_ref.links.graph import save
    g, _, pre = load(a.root)
    if pre is not None:
        emit(pre, a)
        return 1
    if a.save:
        p = save(Path(a.root), g.data)
        emit({"outcome": "SAVED", "graph": g.ref, "path": str(p)}, a)
        return 0
    emit(dict(g.data, graph=g.ref), a)
    return 0


def cmd_relations(a) -> int:
    from bagaev_ref.links.graph import relations, resolve
    g, _, pre = load(a.root)
    if pre is not None:
        emit(pre, a)
        return 1
    eid = resolve(g, a.entity)
    if eid is None:
        emit({"outcome": "REFUSED", "code": "UNKNOWN_ENTITY", "data": {"entity": a.entity}}, a)
        return 1
    kinds = set(a.kinds.split(",")) if a.kinds else None
    emit(dict(relations(g, eid, a.direction, kinds), outcome="RELATIONS"), a)
    return 0


def cmd_impact(a) -> int:
    r, *_, pre = report(a)
    if pre is not None:
        emit(pre, a)
        return 1
    emit(dict(r, outcome="IMPACT"), a)
    return 0


def cmd_context(a) -> int:
    from bagaev_ref.links.context import context_pack
    r, b, c, bf, cf, pre = report(a)
    if pre is not None:
        emit(pre, a)
        return 1
    p = context_pack(r, b, c, bf, cf, a.budget, a.cursor)
    emit(p, a)
    return 0 if p["outcome"] == "CONTEXT" else 1


def cmd_why(a) -> int:
    from bagaev_ref.links.graph import resolve
    from bagaev_ref.links.impact import why_affected, why_not
    r, b, c, _, _, pre = report(a)
    if pre is not None:
        emit(pre, a)
        return 1
    eid = resolve(c, a.entity) or resolve(b, a.entity)
    if eid is None:
        emit({"outcome": "REFUSED", "code": "UNKNOWN_ENTITY", "data": {"entity": a.entity}}, a)
        return 1
    out = why_affected(r, eid) if a.affected else why_not(r, eid)
    if a.recheck and out.get("outcome") == "EXCLUDED":
        from bagaev_ref.links import certs
        g, _, pre = load(a.recheck, "recheck")
        if pre is not None:
            emit(pre, a)
            return 1
        out["recheck"] = [dict(certs.revalidate(bs, g, eid), certificate=bs["certificate"]) for bs in out["basis"]]
    emit(out, a)
    return 0


def register(sub) -> None:
    gp = sub.add_parser("graph", help="граф связей проекта (spec/links/08-bagaev-extraction.md)")
    gp.add_argument("root")
    gp.add_argument("--save", action="store_true", help="записать в <корень>/.bagaev/graph/<source>/<extractor>.json (D84)")
    gp.add_argument("--json", action="store_true")
    gp.set_defaults(fn=cmd_graph)

    rp = sub.add_parser("relations", help="точные отношения сущности: рёбра, provenance, покрытие")
    rp.add_argument("root")
    rp.add_argument("entity", help="EntityId или полное имя")
    rp.add_argument("--direction", choices=["in", "out", "both"], default="both")
    rp.add_argument("--kinds", help="виды рёбер через запятую")
    rp.add_argument("--json", action="store_true")
    rp.set_defaults(fn=cmd_relations)

    def pair(p):
        p.add_argument("base", help="корень базовой версии")
        p.add_argument("candidate", help="корень кандидата")
        p.add_argument("--analysis-budget", type=int, help="бюджет анализа: число шагов worklist")
        p.add_argument("--unavailable", help="недоступные сущности (EntityId через запятую)")
        p.add_argument("--with-tests", action="store_true",
                       help="исполнить тесты кандидата (хранилища в памяти) как свидетельства для D83(a)")
        p.add_argument("--json", action="store_true")

    ip = sub.add_parser("impact", help="анализ влияния кандидата относительно базы (OUT-05)")
    pair(ip)
    ip.set_defaults(fn=cmd_impact)

    cp = sub.add_parser("context", help="ContextPack шага: обязательная оболочка и раскрытие по бюджету (OUT-06)")
    pair(cp)
    cp.add_argument("--budget", type=int, required=True, help="бюджет контекста, единицы utf8-bytes/4@1")
    cp.add_argument("--cursor", type=int, default=0, help="продолжение со следующей страницы")
    cp.set_defaults(fn=cmd_context)

    wp = sub.add_parser("why", help="почему сущность затронута или исключена")
    pair(wp)
    wp.add_argument("entity")
    g = wp.add_mutually_exclusive_group(required=True)
    g.add_argument("--affected", action="store_true")
    g.add_argument("--not-affected", action="store_true")
    wp.add_argument("--recheck", help="перепроверить основание исключения на другом корне (применимость)")
    wp.set_defaults(fn=cmd_why)
