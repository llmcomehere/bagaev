"""Сертификаты D83 (spec/links/08-bagaev-extraction.md §5, LNK-08-15, LNK-08-16; links/03 §3).

(a) интерфейсный контракт закрывает **обязательство** «Y полагается на правило R» (пару requires), когда R
    реализуют изменённые провайдеры: интерфейсы и текст R те же, а проверки R — прежние тесты базы, они
    достигают каждого затронутого провайдера и на кандидате проходят. Отношение он не закрывает: выходы Y
    по-прежнему в области (links/03 §3 — закрытие обязательства не закрывает выходной delta);
(b) нет пути зависимости: при полном покрытии видов рёбер (EFF-13) сущность, до которой от изменения нет пути,
    не затронута. Предпосылки (ревизия и замыкание зависимостей) записываются и перепроверяются.
"""
from __future__ import annotations

from bagaev_ref.kernel import canonical as C
from bagaev_ref.links.graph import DEPENDS, Graph

# Явный профиль TS-1: migration не является декларацией TypeScript; слой migrations — обычный TS-код.
# Остальные и неизвестные профили обязаны сообщать покрытие всех переносящих видов LINKS-1.
DEPENDENCY_PROFILES = {"links-ts@1": frozenset(DEPENDS) - {"migrates"}}


def closure(g: Graph, eid: str) -> set:
    seen, stack = set(), [eid]
    while stack:
        n = stack.pop()
        if n in seen or n not in g.nodes:
            continue
        seen.add(n)
        stack.extend(g.dependencies(n))
    return seen


def incomplete_coverage(g: Graph) -> list[str]:
    """Неполные обязательные виды профиля извлекателя; отсутствие записи не доказывает отсутствие рёбер.

    Запись PARTIAL относится ко всему проекту: локализовать неизвестные рёбра по её тексту нельзя.
    """
    kinds = g.coverage["kinds"]
    profile = g.data["extractor_rev"].split("+", 1)[0]
    required = (DEPENDENCY_PROFILES.get(profile, frozenset(DEPENDS))
                | ((set(kinds) | {e["kind"] for e in g.data["edges"]}) & DEPENDS.keys()))
    return sorted(k for k in required if kinds.get(k, {}).get("status") != "COMPLETE")


def interface_contract(base: Graph, cand: Graph, rule: str, y: str, affected: set, seeds: dict,
                       evidence: dict | None):
    """D83(a) для пары (R, Y, requires). Возвращает основание или None (тогда пара открыта)."""
    if evidence is None or rule in seeds or y in seeds or incomplete_coverage(base) or incomplete_coverage(cand):
        return None
    if not (rule in base.linked(y, "requires") and rule in cand.linked(y, "requires")):
        return None
    providers = sorted({x for g in (base, cand) for x in g.implementers(rule)} & affected)
    if not providers:
        return None                                      # Y в области не из-за провайдеров R
    for x in providers:
        bx, cx = base.nodes.get(x), cand.nodes.get(x)
        if bx is None or cx is None or bx.get("sig") != cx.get("sig") or rule not in cand.linked(x, "implements") \
                or rule not in base.linked(x, "implements"):
            return None
    tests = sorted(base.checkers(rule))
    if not tests:
        return None
    reach = set()
    for t in tests:                                      # свидетельства — прежние тесты, не ослабленные кандидатом
        bt, ct = base.nodes[t], cand.nodes.get(t)
        if ct is None or ct["rev"] != bt["rev"] or t in seeds or rule not in cand.linked(t, "checks"):
            return None
        if evidence.get(ct["name"]) != "PASS":
            return None
        reach |= closure(cand, t)
    if not set(providers) <= reach:
        return None                                      # тест должен исполнять каждого затронутого провайдера
    return {"certificate": "D83a-interface-contract", "rule": rule, "dependent": y,
            "premises": {"dependent_rev": cand.nodes[y]["rev"], "rule_rev": cand.nodes[rule]["rev"],
                         "providers": [{"id": x, "sig": cand.nodes[x]["sig"], "rev": cand.nodes[x]["rev"]}
                                       for x in providers],
                         "tests": [{"id": t, "rev": cand.nodes[t]["rev"], "result": "PASS"} for t in tests]}}


def closure_premises(g: Graph, eid: str) -> dict:
    """Предпосылки исключения (b): ревизия сущности и дайджест её замыкания зависимостей в графе g."""
    cl = sorted([n, g.nodes[n]["rev"]] for n in closure(g, eid))
    return {"rev": g.nodes[eid]["rev"], "closure": C.digest("dependency-closure", "1", cl), "closure_size": str(len(cl)),
            "extractor_rev": g.data["extractor_rev"]}


def no_dependency_path(g: Graph, eid: str) -> dict | None:
    if incomplete_coverage(g):
        return None
    return {"certificate": "D83b-no-dependency-path", "premises": closure_premises(g, eid),
            "coverage": sorted(k for k, v in g.coverage["kinds"].items() if v["status"] == "COMPLETE" and k in DEPENDS)}


def revalidate(basis: dict, g: Graph, eid: str) -> dict:
    """Применимость прежнего основания к графу g (C08): applicable — все предпосылки те же; иначе stale."""
    if eid not in g.nodes:
        return {"applicability": "stale", "reason": "сущности нет в графе"}
    if basis.get("certificate") == "D83b-no-dependency-path":
        now = closure_premises(g, eid)
        changed = sorted(k for k in ("rev", "closure", "extractor_rev") if basis["premises"].get(k) != now[k])
        covered = sorted(k for k, v in g.coverage["kinds"].items() if v["status"] == "COMPLETE" and k in DEPENDS)
        if incomplete_coverage(g) or basis.get("coverage") != covered:
            changed.append("coverage")
        return {"applicability": "stale" if changed else "applicable", "changed": changed}
    if basis.get("certificate") == "D83a-interface-contract":
        p, r, changed = basis["premises"], basis["rule"], []
        if incomplete_coverage(g):
            changed.append("coverage")
        if g.nodes[eid]["rev"] != p["dependent_rev"] or r not in g.linked(eid, "requires"):
            changed.append("dependent")
        if g.nodes.get(r, {}).get("rev") != p["rule_rev"]:
            changed.append("rule")
        for x in p["providers"]:
            n = g.nodes.get(x["id"], {})
            if n.get("rev") != x["rev"] or r not in g.linked(x["id"], "implements"):
                changed.append("provider")            # новая ревизия провайдера требует новых свидетельств
        for t in p["tests"]:
            if g.nodes.get(t["id"], {}).get("rev") != t["rev"] or r not in g.linked(t["id"], "checks"):
                changed.append("tests")
        if sorted(g.checkers(r)) != sorted(t["id"] for t in p["tests"]):
            changed.append("tests")
        return {"applicability": "stale" if changed else "applicable", "changed": sorted(set(changed))}
    return {"applicability": "stale", "reason": "неизвестный сертификат"}
