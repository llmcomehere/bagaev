"""Диагностики эталона по реестру DIAG-1 (spec/diagnostics/registry.json).

Каноническая первая диагностика — минимальная по ключу SURF-58: (фаза, путь файла, начало диапазона,
порядок кода в реестре).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / "spec" / "diagnostics" / "registry.json"


@lru_cache(maxsize=1)
def registry() -> dict:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    reg["_index"] = {c["code"]: i for i, c in enumerate(reg["codes"])}
    reg["_phase"] = {p: i for i, p in enumerate(reg["phase_order"])}
    return reg


@dataclass
class Diagnostic:
    code: str
    phase: str
    file: str
    start: int
    end: int
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.code not in registry()["_index"]:
            raise ValueError(f"код {self.code} не зарегистрирован в DIAG-1")

    def key(self):
        reg = registry()
        return (reg["_phase"].get(self.phase, 99), self.file, self.start, reg["_index"][self.code])

    def to_json(self) -> dict:
        d = {"code": self.code, "phase": self.phase, "file": self.file, "span": [self.start, self.end]}
        if self.data:
            d["data"] = self.data
        return d


def canonical_order(diags: list[Diagnostic]) -> list[Diagnostic]:
    return sorted(diags, key=Diagnostic.key)


def make(code: str, file: str, start: int, end: int, phase: str | None = None, **data) -> Diagnostic:
    """Диагностика с фазой из реестра; для кодов фазы any фаза задаётся явно."""
    if phase is None:
        phase = next(c["phase"] for c in registry()["codes"] if c["code"] == code)
    return Diagnostic(code, phase, file, start, end, data)
