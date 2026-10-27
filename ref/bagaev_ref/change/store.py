"""Проектное хранилище CHANGE-1 (spec/protocol/agent-protocol.md §1; D85, D84, HST-01).

`.bagaev/objects/<sha256>` — неизменяемые объекты по содержимому (исходники, манифесты снимков, контракты,
SourceEdit, свидетельства, записи приёмки). `.bagaev/project.db` — SQLite (WAL, synchronous=FULL): head, работы,
квитанции операций, свидетельства, приёмки, журнал. Все записи — в транзакциях BEGIN IMMEDIATE.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

from bagaev_ref.kernel import canonical as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, manifest TEXT NOT NULL, accepted INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS works (
  change_id TEXT PRIMARY KEY, base TEXT NOT NULL, candidate TEXT NOT NULL, work_revision INTEGER NOT NULL,
  contract TEXT NOT NULL, contract_revision INTEGER NOT NULL, status TEXT NOT NULL, intent TEXT NOT NULL,
  evidence TEXT NOT NULL, edits TEXT NOT NULL, lineage TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS receipts (
  principal TEXT NOT NULL, namespace TEXT NOT NULL, key TEXT NOT NULL, digest TEXT NOT NULL, operation TEXT NOT NULL,
  response BLOB NOT NULL, PRIMARY KEY (principal, namespace, key));
CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, record BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS acceptance (id TEXT PRIMARY KEY, record BLOB NOT NULL, head_revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS journal (seq INTEGER PRIMARY KEY, operation TEXT NOT NULL, ref TEXT NOT NULL, body BLOB NOT NULL);
"""

SIMULATED_CRASH = None


class Crashed(BaseException):
    pass


def crash_point(name: str):
    """Точка сбоя (CHG-16): как kill -9 — без отката и без ответа."""
    if os.environ.get("BAG_CRASH_AT") == name:
        os._exit(137)
    if SIMULATED_CRASH == name:
        raise Crashed(name)


def object_ref(data: bytes, kind: str, fmt: str) -> dict:
    """ObjectRef CANON-09: вид, формат, sha256, размер."""
    return {"kind": kind, "format": fmt, "sha256": hashlib.sha256(data).hexdigest(), "size": str(len(data))}


class ProjectStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.dir = self.root / ".bagaev"
        self.objects = self.dir / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "project.db", isolation_level=None, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)
        for name, default in (("head", ""), ("head_revision", "0"), ("language", "")):
            self.db.execute("INSERT OR IGNORE INTO meta VALUES (?, ?)", (name, default))

    # ------------------------------------------------------------ объекты
    def put_object(self, data: bytes) -> str:
        h = hashlib.sha256(data).hexdigest()
        p = self.objects / h
        if not p.exists():
            tmp = p.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, p)                            # объект появляется целиком или не появляется
        return h

    def get_object(self, h: str) -> bytes:
        data = (self.objects / h).read_bytes()
        if hashlib.sha256(data).hexdigest() != h:
            raise ValueError(f"объект {h} повреждён")
        return data

    def put_json(self, obj) -> str:
        return self.put_object(C.encode(obj))

    def get_json(self, h: str):
        return C.decode(self.get_object(h))

    # ------------------------------------------------------------ снимки
    def snapshot(self, files: dict, parents: list) -> str:
        """Снимок — манифест исходников (CHG-02); ID — digest("snapshot", "1", манифест). Свидетельства, граф,
        приёмка в манифест не входят: их добавление ID не меняет (T02-C04)."""
        sources = {}
        for path, data in sorted(files.items()):
            self.put_object(data)
            sources[path] = object_ref(data, "source", "bag-utf8")
        manifest = {"format": "bagaev-snapshot/1", "parents": list(parents), "sources": sources}   # порядок значим (CHG-18)
        sid = C.digest("snapshot", "1", manifest)
        self.db.execute("INSERT OR IGNORE INTO snapshots VALUES (?, ?, 0)", (sid, C.encode(manifest).decode()))
        return sid

    def manifest(self, sid: str) -> dict:
        row = self.db.execute("SELECT manifest FROM snapshots WHERE id = ?", (sid,)).fetchone()
        if row is None:
            raise KeyError(sid)
        return C.decode(row[0].encode())

    def files(self, sid: str) -> dict:
        return {p: self.get_object(r["sha256"]) for p, r in self.manifest(sid)["sources"].items()}

    def meta(self, name: str) -> str:
        return self.db.execute("SELECT value FROM meta WHERE name = ?", (name,)).fetchone()[0]

    def set_meta(self, name: str, value):
        self.db.execute("UPDATE meta SET value = ? WHERE name = ?", (str(value), name))

    def accepted_snapshots(self) -> list:
        return [r[0] for r in self.db.execute("SELECT id FROM snapshots WHERE accepted = 1 ORDER BY rowid")]

    def journal(self, operation: str, ref: str, body) -> None:
        self.db.execute("INSERT INTO journal (operation, ref, body) VALUES (?, ?, ?)", (operation, ref, C.encode(body)))

    def close(self):
        self.db.close()
