"""Инкрементальное извлечение (spec/links/08-bagaev-extraction.md §4, LNK-08-18; D38, links/02 §8–9).

Модуль переизвлекается, если изменился его штамп: байты модуля, байты всех модулей, которые он импортирует
транзитивно, и ревизия извлекателя. Рёбра и пробелы остальных модулей берутся из прежнего графа по файлу места.
Узлы всегда строятся заново (их ревизии дёшевы). Корректность — равенство с полным извлечением
(conformance/tools/incremental_vs_full.py); экономия не заявляется.
"""
from __future__ import annotations

from bagaev_ref.kernel import canonical as C
from bagaev_ref.links.extract import EXTRACTOR_REV, Extractor, source_digest


def module_stamps(project, files, scope: str = "transitive") -> dict:
    """scope: transitive (норма), direct, local — два последних только для внесения неисправностей."""
    src = dict(files)
    deps = {m.name: {t.name for _, t in m.imports if not t.is_std} for m in project.user}
    stamps = {}
    for m in project.user:
        seen, stack = set(), [m.name]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            if scope == "transitive" or (scope == "direct" and n == m.name):
                stack.extend(deps.get(n, ()))
        mods = {x.name: x.file for x in project.user}
        stamps[m.name] = C.digest("module-stamp", "1", {"extractor": EXTRACTOR_REV,
                                                         "sources": {mods[n]: src[mods[n]].hex() for n in sorted(seen)}})
    return stamps


def extract_incremental(project, prog, files, previous: dict | None, previous_stamps: dict | None,
                        scope: str = "transitive"):
    """Возвращает (граф, штампы, переизвлечённые модули)."""
    stamps = module_stamps(project, files, scope)
    if previous is None or previous_stamps is None or previous.get("extractor_rev") != EXTRACTOR_REV:
        g = Extractor(project, prog).run(source_digest(files))
        return g, stamps, sorted(stamps)
    redo = {n for n, s in stamps.items() if previous_stamps.get(n) != s}
    keep_files = {m.file for m in project.user if m.name not in redo}
    owner = {n["id"]: n["file"] for n in previous["nodes"]}
    edges = [e for e in previous["edges"] if e["site"]["file"] in keep_files]
    gaps = [x for x in previous["gaps"] if owner.get(x["entity"]) in keep_files]
    unused = [x for x in previous.get("unused_atoms", []) if owner.get(x["entity"]) in keep_files]
    g = Extractor(project, prog).run(source_digest(files), only=redo, reuse_edges=edges, reuse_gaps=gaps,
                                     reuse_unused=unused)
    return g, stamps, sorted(redo)
