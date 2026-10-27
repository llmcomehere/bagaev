"""Поиск по смыслу PROTO-1 (spec/protocol/agent-protocol.md §7.3; T11-C01, T11-C02, D15).

Поиск возвращает **кандидатов** с основаниями совпадения, а не выбор: сходство текста не доказывает, что
сущность — нужная (T11-C01). Совпадение запроса с `not_about` сущности — отрицательное основание; кандидаты
с равным счётом или с отрицательным основанием делают запрос неоднозначным (`ambiguous`), выбор остаётся за
явным решением — областью контракта (`scope`). Порядок — счёт по убыванию, затем EntityId.
"""
from __future__ import annotations

import re

from bagaev_ref.change import workstate as W

WORD = re.compile(r"\w+", re.U)


def words(s: str) -> set:
    return {w.lower() for w in WORD.findall(s)}


def search(store, sid: str, query: str) -> dict:
    if not isinstance(query, str) or not words(query):
        return {"query": query, "candidates": [], "ambiguous": False, "selection": "none"}
    q = words(query)
    g, files, _ = W.graph_of(store, sid, "head")
    from bagaev_ref.change import lang as L
    meanings = L.of(store).meanings(files)
    out = []
    for n in g.nodes.values():
        basis, score = [], 0
        name_words = words(n["name"].replace("_", " ").replace(".", " "))
        if q & name_words:
            basis.append({"kind": "name", "words": sorted(q & name_words)})
            score += len(q & name_words)
        ent = meanings.get(n["name"])
        if ent is not None:
            purpose, terms, not_about = ent
            pw = words(purpose or "") | {w for t in terms for w in words(t)}
            if q & pw:
                basis.append({"kind": "purpose_or_terms", "words": sorted(q & pw)})
                score += len(q & pw)
            neg = [t for t in not_about if words(t) & q]
            if neg:
                basis.append({"kind": "not_about", "terms": neg})
                score -= len(neg)
        if basis:
            out.append({"id": n["id"], "name": n["name"], "kind": n["kind"], "score": score, "basis": basis})
    out.sort(key=lambda c: (-c["score"], c["id"]))
    top = [c for c in out if out and c["score"] == out[0]["score"]]
    ambiguous = len(top) > 1 or any(b["kind"] == "not_about" for c in out[:3] for b in c["basis"])
    return {"query": query, "candidates": out[:20], "ambiguous": ambiguous, "selection": "none",
            "note": "кандидаты, а не выбор: выбор фиксирует область контракта (scope)"}
