"""ContextPack LINKS-1 (spec/links/08-bagaev-extraction.md §6; 04-agent-tooling §5 boundedContext; OUT-06, D28).

Обязательная оболочка (сводка отчёта и все обязательства) входит всегда; если она больше бюджета —
MANDATORY_ENVELOPE_TOO_LARGE. Остальное раскрывается в стабильном порядке (приоритет, расстояние, EntityId)
до бюджета; не поместившееся — pending с курсором следующей страницы. Измеритель — utf8-bytes/4@1.
"""
from __future__ import annotations

from bagaev_ref.kernel import canonical as C

MEASURE = "utf8-bytes/4@1"
RANKING = "links-1-context@1"


def tokens(obj) -> int:
    data = obj.encode("utf-8") if isinstance(obj, str) else C.encode(obj)
    return (len(data) + 3) // 4


def text_of(files: dict, node: dict) -> str:
    s, e = int(node["span"][0]), int(node["span"][1])
    return files[node["file"]][s:e].decode("utf-8")


def head_of(files: dict, node: dict) -> str:
    """Интерфейс сущности: у функций и точек входа — текст до тела (сигнатура, ряд, связи); у типов, событий,
    хранилищ и правил тела нет — весь текст объявления."""
    if "head" in node:
        s, e = int(node["head"][0]), int(node["head"][1])
        return files[node["file"]][s:e].decode("utf-8").rstrip()
    return text_of(files, node)


def envelope(report: dict) -> dict:
    return {"impact_status": report["status"], "readiness": report["readiness"], "base": report["base"],
            "candidate": report["candidate"], "seeds": [[s["id"], s["seed"]] for s in report["seeds"]],
            "obligations": [[o["target"], o["source"], o["kind"], o["status"]] for o in report["obligations"]
                            if o["status"] != "excluded_with_basis"],
            "unknown": [[u["id"], u["cause"]] for u in report["unknown"]],
            "frontier": [f["id"] for f in report["frontier"]]}


def candidates(report, base_g, cand_g):
    """(приоритет, расстояние, EntityId, вид элемента) — полный ключ порядка раскрытия (T11-C05)."""
    seeds = {s["id"] for s in report["seeds"]}
    out = []
    for x in report["in_scope"]:
        out.append((0 if x["id"] in seeds else 2, x["distance"], x["id"], "expanded"))
    rules = sorted({o["target"] for o in report["obligations"] if o["status"] == "open"})
    out += [(1, 0, r, "expanded") for r in rules]
    in_scope = {x["id"] for x in report["in_scope"]}
    excluded = {x["id"]: x for x in report["excluded_with_basis"]}
    boundary = set()
    for x in in_scope:
        for g in (base_g, cand_g):
            for d in g.dependencies(x):
                if d in excluded:
                    boundary.add(d)
    out += [(3, 1, b, "boundary") for b in sorted(boundary)]
    out += [(4, 0, u["id"], "blocked" if u["cause"] == "ACCESS_BLOCKED" else "pending") for u in report["unknown"]
            if u["cause"] != "ANALYSIS_INCOMPLETE"]
    out += [(4, f["distance"], f["id"], "pending") for f in report["frontier"]]
    seen, uniq = set(), []
    for c in sorted(out):
        if c[2] not in seen:
            seen.add(c[2])
            uniq.append(c)
    return uniq


def context_pack(report: dict, base_g, cand_g, base_files: dict, cand_files: dict, budget: int,
                 cursor: int = 0) -> dict:
    env = envelope(report)
    used = tokens(env)
    if used > budget:
        return {"outcome": "REFUSED", "code": "MANDATORY_ENVELOPE_TOO_LARGE",
                "data": {"envelope_tokens": used, "budget": budget, "measure": MEASURE}}
    excluded = {x["id"]: x for x in report["excluded_with_basis"]}
    items, coverage, next_cursor = [], [], None
    order = candidates(report, base_g, cand_g)
    reserve = tokens({"coverage": "pending", "reason": "BUDGET", "from": "99999", "remaining": "99999",
                      "action": "следующая страница: cursor 99999"})          # место под сводку обрыва
    if used + 2 * reserve > budget:                      # оболочка и место под отметку обрыва — обязательны
        return {"outcome": "REFUSED", "code": "MANDATORY_ENVELOPE_TOO_LARGE",
                "data": {"envelope_tokens": used, "reserve_tokens": 2 * reserve, "budget": budget, "measure": MEASURE}}
    for i, (prio, dist, eid, kind) in enumerate(order):
        if i < cursor:
            continue
        g, files = (cand_g, cand_files) if eid in cand_g.nodes else (base_g, base_files)
        node = g.nodes[eid]
        if kind in ("pending", "blocked"):
            reason = "ACCESS_BLOCKED" if kind == "blocked" else (
                "ANALYSIS_FRONTIER" if any(f["id"] == eid for f in report["frontier"]) else "UNKNOWN")
            cov = {"id": eid, "name": node["name"], "coverage": kind, "reason": reason,
                   "action": "доступ к сущности" if kind == "blocked" else "продолжить анализ с большим бюджетом"}
            options = [(None, cov)]
        else:
            boundary = {"id": eid, "name": node["name"], "kind": node["kind"], "interface": head_of(files, node),
                        "basis": excluded[eid]["basis"] if eid in excluded else []}
            options = []
            if kind == "expanded":
                options.append(({"id": eid, "name": node["name"], "kind": node["kind"], "rev": node["rev"],
                                 "side": "candidate" if g is cand_g else "base", "text": text_of(files, node)},
                                {"id": eid, "name": node["name"], "coverage": "expanded"}))
            options.append((boundary, {"id": eid, "name": node["name"], "coverage": "boundary"}
                            if kind == "boundary" else
                            {"id": eid, "name": node["name"], "coverage": "boundary", "reason": "ITEM_TOO_LARGE"}))
        cost = lambda opt: (tokens(opt[0]) if opt[0] is not None else 0) + tokens(opt[1])
        fit = next((o for o in options if used + cost(o) + reserve <= budget), None)
        if fit is None and (items or kind in ("pending", "blocked")):
            next_cursor = i                              # дальше — следующая страница
            coverage.append({"coverage": "pending", "reason": "BUDGET", "from": str(i),
                             "remaining": str(len(order) - i), "action": f"следующая страница: cursor {i}"})
            used += tokens(coverage[-1])
            break
        if fit is None:                                  # элемент больше страницы: отметить и идти дальше (M3)
            fit = (None, {"id": eid, "name": node["name"], "coverage": "pending", "reason": "ITEM_TOO_LARGE",
                          "action": "увеличить бюджет контекста"})
            if used + cost(fit) + reserve > budget:      # и отметка не помещается — следующая страница с него же
                next_cursor = i if coverage else i + 1
                coverage.append({"coverage": "pending", "reason": "BUDGET", "from": str(next_cursor),
                                 "remaining": str(len(order) - next_cursor),
                                 "action": f"следующая страница: cursor {next_cursor}"})
                used += tokens(coverage[-1])
                break

        used += cost(fit)
        if fit[0] is not None:
            items.append(fit[0])
        coverage.append(fit[1])
    must = [c for c in coverage if c["coverage"] in ("pending", "blocked")]
    ready = report["status"] == "COMPLETE" and not report["unknown"] and not must and cursor == 0
    blockers = []
    if report["status"] != "COMPLETE":
        blockers.append("ANALYSIS_SCOPE_INCOMPLETE")
    if any(c["coverage"] == "blocked" for c in coverage):
        blockers.append("ACCESS_BLOCKED")
    if any(c.get("reason") in ("BUDGET", "ITEM_TOO_LARGE") for c in coverage):
        blockers.append("CONTEXT_INCOMPLETE")
    return {"outcome": "CONTEXT", "measure": MEASURE, "ranking": RANKING, "budget": budget, "used": used,
            "envelope": env, "items": items, "coverage": coverage, "next_cursor": next_cursor,
            "ready_for_step": ready and not blockers, "blockers": blockers}
