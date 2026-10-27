"""Анализ влияния LINKS-1 (spec/links/08-bagaev-extraction.md §5; упрощённый LNK-I01, D12, D83, OUT-05).

Рабочий граф — объединение base и candidate с метками сторон: удалённое ребро продолжает переносить влияние.
Worklist детерминирован (расстояние, режим, EntityId); каждое извлечение из очереди — шаг бюджета.
Исключение только по сертификату D83, иначе сущность в области или unknown.
"""
from __future__ import annotations

import heapq
import itertools

from bagaev_ref.links import certs
from bagaev_ref.links.graph import DEPENDS, Graph

AFFECTED, UNKNOWN = 0, 1                                  # режимы: известно затронута / TOP


def seeds(base: Graph, cand: Graph) -> dict:
    """Семена (LNK-08-13): добавленные, удалённые и изменённые сущности; источники добавленных и снятых рёбер."""
    out = {}
    for eid in sorted(set(base.nodes) | set(cand.nodes)):
        b, c = base.nodes.get(eid), cand.nodes.get(eid)
        if b is None:
            out[eid] = "added"
        elif c is None:
            out[eid] = "removed"
        elif b["rev"] != c["rev"]:
            out[eid] = "changed"
    key = lambda g: {(e["kind"], e["src"], e["dst"]) for e in g.data["edges"] if g.propagates(e)}
    kb, kc = key(base), key(cand)
    for kind, src, dst in sorted(kb ^ kc):
        holder = src if DEPENDS[kind] == "src" else dst      # чьё поведение меняет ребро
        out.setdefault(holder, "edge-added" if (kind, src, dst) in kc else "edge-removed")
    return out


def name_of(base: Graph, cand: Graph, eid: str) -> str:
    return (cand.nodes.get(eid) or base.nodes.get(eid) or {}).get("name", eid)


def impact(base: Graph, cand: Graph, budget: int | None = None, unavailable=(), evidence: dict | None = None) -> dict:
    sd = seeds(base, cand)
    coverage_gaps = [{"side": g.side, "kind": k, "basis": g.coverage["kinds"].get(k, {}).get("basis", "нет покрытия")}
                     for g in (base, cand) for k in certs.incomplete_coverage(g)]
    blocked = set(unavailable)
    state, via, dist = {}, {}, {}                        # eid → AFFECTED | UNKNOWN; основание; расстояние
    tick = itertools.count()                             # порядок вставки — последний ключ, без сравнения оснований
    known = set(base.nodes) | set(cand.nodes)
    # недоступные сущности — TOP с самого начала (C12): их содержимое нельзя читать, даже если обход до них не дойдёт
    heap = [(0, UNKNOWN, eid, next(tick), {"from": None, "kind": "unavailable"}) for eid in sorted(blocked & known)]
    heap += [(0, AFFECTED, eid, next(tick), None) for eid in sorted(set(sd) - blocked)]
    heapq.heapify(heap)
    steps = 0
    while heap:
        if budget is not None and steps >= budget:
            break
        d, mode, eid, _, why = heapq.heappop(heap)
        if eid in state and (state[eid] <= mode or eid in blocked):
            continue                                     # монотонность: AFFECTED сильнее UNKNOWN; блок — навсегда TOP
        steps += 1
        if eid in blocked:
            mode = UNKNOWN
        state[eid], via[eid], dist[eid] = mode, why, d
        for g in (base, cand):
            for y, e in g.dependents(eid):
                heapq.heappush(heap, (d + 1, mode, y, next(tick), {"from": eid, "kind": e["kind"], "side": g.side,
                                                       "edge": e["id"]}))
    pending = {}
    for d, mode, eid, _, why in sorted(heap):                       # бюджет кончился: достигнутые, но не обработанные
        if eid not in state or state[eid] > mode:
            pending.setdefault(eid, (d, mode, why))
    complete = not pending and not coverage_gaps
    all_ids = sorted(set(base.nodes) | set(cand.nodes))
    g_for = lambda eid: cand if eid in cand.nodes else base
    in_scope = [{"id": e, "name": name_of(base, cand, e), "distance": dist[e], "seed": sd.get(e), "via": via[e]}
                for e in all_ids if state.get(e) == AFFECTED]
    unknown = [{"id": e, "name": name_of(base, cand, e),
                "cause": "ACCESS_BLOCKED" if e in blocked else "DEPENDS_ON_UNKNOWN", "via": via[e]}
               for e in all_ids if state.get(e) == UNKNOWN]
    frontier = [{"id": e, "name": name_of(base, cand, e), "distance": pending[e][0], "via": pending[e][2]}
                for e in sorted(pending)]
    rest = [e for e in all_ids if e not in state and e not in pending]
    excluded = []
    if complete:
        for e in rest:
            excluded.append({"id": e, "name": name_of(base, cand, e), "basis": [certs.no_dependency_path(g_for(e), e)]})
    else:
        unknown += [{"id": e, "name": name_of(base, cand, e),
                     "cause": "COVERAGE_PARTIAL" if coverage_gaps else "ANALYSIS_INCOMPLETE",
                     **({"coverage": coverage_gaps} if coverage_gaps else {})} for e in rest]
        unknown.sort(key=lambda u: u["id"])
    obligations = obligation_status(base, cand, sd, state, pending, complete, evidence)
    tests = sorted({name_of(base, cand, t) for t in state if state[t] == AFFECTED and g_for(t).nodes[t]["kind"] == "test"}
                   | {name_of(base, cand, o["source"]) for o in obligations if o["kind"] == "checks" and o["status"] == "open"}
                   | {name_of(base, cand, t) for o in obligations if o["status"] == "open"
                      for t in cand.checkers(o["target"])})
    gaps = [dict(x, name=name_of(base, cand, x["entity"])) for g in (base, cand) for x in g.data["gaps"]
            if state.get(x["entity"]) == AFFECTED]
    gaps = [dict(t) for t in sorted({tuple(sorted(x.items())) for x in gaps})]
    if not complete or unknown:
        readiness = "BLOCKED"
    elif any(o["status"] == "open" for o in obligations):
        readiness = "ELIGIBLE_IF_ALL_OBLIGATIONS_PASS"
    else:
        readiness = "NO_OPEN_OBLIGATIONS"
    return {"status": "COMPLETE" if complete else "INCOMPLETE", "base": base.ref, "candidate": cand.ref,
            "steps": steps, "budget": budget, "seeds": [{"id": e, "name": name_of(base, cand, e), "seed": s}
                                                        for e, s in sorted(sd.items())],
            "in_scope": in_scope, "excluded_with_basis": excluded, "unknown": unknown, "frontier": frontier,
            "obligations": obligations, "tests_to_run": tests, "gaps": gaps, "readiness": readiness,
            "coverage_gaps": coverage_gaps}


def obligation_status(base, cand, sd, state, pending, complete, evidence=None) -> list:
    """Обязательства по декларированным связям (LNK-08-17): пара (смысл, декларация, вид) — open, если изменился
    смысл или декларация в области; unknown — если декларация unknown или во frontier; иначе excluded_with_basis.
    Пару requires в области может закрыть D83(a) (LNK-08-15)."""
    out = []
    pairs = base.declared_pairs() | cand.declared_pairs()
    affected = {e for e, m in state.items() if m == 0}
    for target, source, kind in sorted(pairs):
        sides = [g.side for g in (base, cand) if (target, source, kind) in g.declared_pairs()]
        cert = None
        if kind == "requires" and complete and state.get(source) == 0 and not sd.get(target):
            cert = certs.interface_contract(base, cand, target, source, affected, sd, evidence)
        if cert is not None:
            out.append({"target": target, "target_name": name_of(base, cand, target), "source": source,
                        "source_name": name_of(base, cand, source), "kind": kind, "status": "excluded_with_basis",
                        "reason": "D83a-interface-contract", "sides": sides, "basis": cert})
            continue
        if sd.get(target) or state.get(source) == 0:
            status = "open"
            reason = "target-" + sd[target] if sd.get(target) else "source-in-scope"
        elif state.get(source) == 1 or source in pending or not complete:
            status, reason = "unknown", "source-unknown" if state.get(source) == 1 else "analysis-incomplete"
        else:
            status, reason = "excluded_with_basis", "D83b-no-dependency-path"
        out.append({"target": target, "target_name": name_of(base, cand, target), "source": source,
                    "source_name": name_of(base, cand, source), "kind": kind, "status": status, "reason": reason,
                    "sides": sides})
    return out


def why_affected(report: dict, eid: str) -> dict:
    """Путь от семени до сущности по рёбрам объединения (links/03 §8 whyAffected)."""
    by = {x["id"]: x for x in report["in_scope"] + report["unknown"] + report["frontier"]}
    if eid not in by:
        return {"outcome": "NOT_AFFECTED", "id": eid}
    path, cur, seen = [], eid, set()
    while cur is not None and cur not in seen:
        seen.add(cur)
        x = by.get(cur)
        path.append({"id": cur, "name": x["name"] if x else cur, "seed": (x or {}).get("seed"),
                     "via": (x or {}).get("via")})
        cur = ((x or {}).get("via") or {}).get("from")
    status = ("in_scope" if any(i["id"] == eid for i in report["in_scope"]) else
              "frontier" if any(i["id"] == eid for i in report["frontier"]) else "unknown")
    return {"outcome": "AFFECTED", "status": status, "id": eid, "path": path[::-1]}


def why_not(report: dict, eid: str) -> dict:
    for x in report["excluded_with_basis"]:
        if x["id"] == eid:
            return {"outcome": "EXCLUDED", "id": eid, "name": x["name"], "basis": x["basis"]}
    for x in report["unknown"]:
        if x["id"] == eid:
            return {"outcome": "UNKNOWN", "id": eid, "cause": x["cause"]}
    return {"outcome": "NOT_EXCLUDED", "id": eid, "detail": "сущность в области или во frontier"}
