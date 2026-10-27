"""Точные байты входов, атомарный checkpoint и проверяемый журнал."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as f:
        f.write(encoded(value) + b"\n")
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def load(path: Path):
    return json.loads(path.read_bytes())


def manifest(root: Path, *, private=False) -> dict:
    """Никаких переходов по symlink; служебные каталоги не являются исходниками."""
    result = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part.startswith(".") or part == "node_modules" for part in rel.parts):
            continue
        if p.is_symlink():
            raise ValueError(f"SYMLINK_NOT_ALLOWED: {rel}")
        if p.is_file():
            result[rel.as_posix()] = {"sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
    return result


class Journal:
    """Hash chain обнаруживает повреждение; это не подпись и не защита от автора журнала."""
    def __init__(self, path: Path):
        self.path = path
        self.rows = self.verify(path)

    @staticmethod
    def verify(path: Path) -> list:
        rows, previous = [], None
        if path.exists():
            for line in path.read_bytes().splitlines():
                row = json.loads(line)
                digest = row.pop("sha256")
                if row.get("seq") != len(rows) + 1 or row.get("previous") != previous or sha(encoded(row)) != digest:
                    raise ValueError("JOURNAL_INTEGRITY")
                row["sha256"] = digest
                rows.append(row)
                previous = digest
        return rows

    @property
    def tail(self):
        return self.rows[-1]["sha256"] if self.rows else None

    def append(self, kind: str, **data):
        row = dict(seq=len(self.rows) + 1, previous=self.tail, kind=kind, **data)
        row["sha256"] = sha(encoded(row))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as f:
            f.write(encoded(row) + b"\n")
            f.flush()
            os.fsync(f.fileno())
        self.rows.append(row)
        return row
