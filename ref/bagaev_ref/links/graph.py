"""Граф связей (spec/links/08-bagaev-extraction.md §3–4): индексы, направление зависимости, запросы, хранение.

Граф — неизменяемая запись BAG-CJSON-1; прямой и обратный индексы — представления одного списка рёбер.
GraphRef = digest("graph", "1", граф). Хранение вне снимка (D84): `.bagaev/graph/<source>/<extractor_rev>.json`.
"""
from __future__ import annotations

from pathlib import Path

from bagaev_ref.kernel import canonical as C

# Кто от кого зависит (LNK-08-12): "src" — источник ребра зависит от цели; "dst" — цель от источника.
DEPENDS = {"calls": "src", "references": "src", "uses_type": "src", "reads": "src", "consumes": "src",
           "writes": "dst", "emits": "dst", "migrates": "dst", "defines": "src"}
DECLARED = ("implements", "requires", "checks", "about", "derived_from")


class Graph:
    def __init__(self, data: dict, side: str = ""):
        self.data, self.side = data, side
        self.nodes = {n["id"]: n for n in data["nodes"]}
        self.coverage = data["coverage"]
        self.out, self.inc = {}, {}
        for e in data["edges"]:
            self.out.setdefault(e["src"], []).append(e)
            self.inc.setdefault(e["dst"], []).append(e)

    @property
    def ref(self) -> str:
        return C.digest("graph", "1", self.data)

    def propagates(self, e) -> bool:
        """Переносит ли ребро влияние (LNK-08-12). Не переносят: defines модуля (модуль — пространство имён) и
        эффекты хранилища теста — он работает на своей копии хранилища (HST-18), рабочие таблицы не связывает."""
        if e["kind"] not in DEPENDS:
            return False
        src_kind = self.nodes.get(e["src"], {}).get("kind")
        if e["kind"] == "defines" and src_kind == "module":
            return False
        return not (src_kind == "test" and e["kind"] in ("reads", "writes", "emits"))

    def dependents(self, x: str):
        """Сущности, которые зависят от x, с ребром основания."""
        for e in self.inc.get(x, []):
            if self.propagates(e) and DEPENDS[e["kind"]] == "src":
                yield e["src"], e
        for e in self.out.get(x, []):
            if self.propagates(e) and DEPENDS[e["kind"]] == "dst":
                yield e["dst"], e

    def dependencies(self, x: str):
        for e in self.out.get(x, []):
            if self.propagates(e) and DEPENDS[e["kind"]] == "src":
                yield e["dst"]
        for e in self.inc.get(x, []):
            if self.propagates(e) and DEPENDS[e["kind"]] == "dst":
                yield e["src"]

    def linked(self, src: str, kind: str) -> set:
        return {e["dst"] for e in self.out.get(src, []) if e["kind"] == kind}

    def implementers(self, rule: str) -> set:
        return {e["src"] for e in self.inc.get(rule, []) if e["kind"] == "implements"}

    def checkers(self, rule: str) -> set:
        return {e["src"] for e in self.inc.get(rule, []) if e["kind"] == "checks"}

    def declared_pairs(self):
        """Пары обязательств: (цель смысла, декларация, вид связи) — LNK-08-17."""
        return {(e["dst"], e["src"], e["kind"]) for e in self.data["edges"] if e["kind"] in DECLARED and e["dst"]}


def relations(g: Graph, entity: str, direction: str = "both", kinds=None) -> dict:
    """Точные отношения сущности с provenance и покрытием (links/03 §8 relations)."""
    def keep(e):
        return kinds is None or e["kind"] in kinds
    out = {"graph": g.ref, "entity": entity, "name": g.nodes.get(entity, {}).get("name")}
    if direction in ("out", "both"):
        out["outgoing"] = [e for e in g.out.get(entity, []) if keep(e)]
    if direction in ("in", "both"):
        out["incoming"] = [e for e in g.inc.get(entity, []) if keep(e)]
    out["coverage"] = {k: v["status"] for k, v in g.coverage["kinds"].items() if kinds is None or k in kinds}
    out["gaps"] = [x for x in g.data["gaps"] if x["entity"] == entity]
    return out


def resolve(g: Graph, ref: str) -> str | None:
    """EntityId по самому ID или полному имени."""
    if ref in g.nodes:
        return ref
    hits = [n["id"] for n in g.nodes.values() if n["name"] == ref]
    return hits[0] if len(hits) == 1 else None


def save(root: Path, data: dict) -> Path:
    p = Path(root) / ".bagaev" / "graph" / data["source"] / f"{data['extractor_rev']}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(C.encode(data))
    return p
