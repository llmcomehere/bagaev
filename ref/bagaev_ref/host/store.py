"""Хранилище хоста на SQLite (spec/runtime/host.md §2): таблицы программы, outbox, inbox, receipts, журнал,
активная привязка схемы.

Таблица программы хранится в `t_<EntityId таблицы>`: переименование таблицы не трогает данные (D67).
Ключ и значение — наблюдаемая форма CANON-11 в BAG-CJSON-1 (VALUE-CODEC-V1 ещё не закрыт, BD07).
"""
from __future__ import annotations

import sqlite3

from bagaev_ref.kernel import canonical as C
from bagaev_ref.machine.observe import observe, type_text
from bagaev_ref.machine.values import key_of

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (
  seq INTEGER PRIMARY KEY, event TEXT NOT NULL, payload BLOB NOT NULL,
  origin TEXT NOT NULL, state_version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS inbox (
  handler TEXT NOT NULL, seq INTEGER NOT NULL, outcome TEXT NOT NULL, detail BLOB,
  PRIMARY KEY (handler, seq));
CREATE TABLE IF NOT EXISTS receipts (
  namespace TEXT NOT NULL, key TEXT NOT NULL, request TEXT NOT NULL, outcome TEXT NOT NULL,
  result BLOB NOT NULL, state_version INTEGER NOT NULL, PRIMARY KEY (namespace, key));
CREATE TABLE IF NOT EXISTS journal (
  seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, ref TEXT NOT NULL, body BLOB NOT NULL);
"""


def entity_id(node) -> str:
    """EntityId узла с атрибутами (SURF-07): таблица или элемент верхнего уровня."""
    return [a.args[0][1] for a in node.attrs if a.name.text == "id"][0]


def type_id(t) -> str:
    """EntityId типа верхнего уровня: атрибуты у элемента модуля, а не у самой декларации."""
    return entity_id(next(it for it in t.module.tree.items if it.decl is t.decl))


def table_id(tbl) -> str:
    return entity_id(tbl.decl)


def shape(t, seen: tuple = (), *, nominal: bool = False):
    """Строение типа для привязки (HST-04): встроенный тип — имя и строение аргументов; пользовательский — строение
    записи, суммы или opaque без имени. Структурная совместимость не зависит от переименования типа.
    Регулярная рекурсия — ссылка на охватывающий тип.
    nominal=True сохраняет также имена всех вложенных типов для кодирования ключа CANON-11."""
    from bagaev_ref.sema import types as T
    t = T.prune(t)
    if isinstance(t, T.TCon):
        return [t.name, *[shape(a, seen, nominal=nominal) for a in t.args]]
    if isinstance(t, T.TNom):
        key = type_text(t)
        if key in seen:
            return ["recursive", str(seen.index(key))]       # десятичная строка: CANON-02 запрещает числа JSON
        seen = seen + (key,)
        info, m = t.info, t.info.mapping(t.args)
        if info.kind in ("record", "event"):
            out = ["record", [[f, shape(T.subst(ft, m), seen, nominal=nominal)] for f, ft in info.fields]]
        elif info.kind == "opaque":
            out = ["opaque", shape(T.subst(info.rep, m), seen, nominal=nominal)]
        else:
            out = ["enum", [[tag, None if pt is None else shape(T.subst(pt, m), seen, nominal=nominal)]
                            for tag, pt in info.variants]]
        return ["nominal", key, out] if nominal else out
    return ["fn"]


def event_shape(ev) -> dict:
    return {"name": ev.qname, "fields": {f: type_text(t) for f, t in ev.fields},
            "shape": [[f, shape(t)] for f, t in ev.fields]}


def schema_of(project) -> dict:
    """Схема данных программы (HST-04): EntityId таблицы → {name, key, value, key_shape, value_shape, key_encoding}; EntityId
    события → {name, fields, shape} в разделе events (полезная нагрузка outbox — данные хранилища)."""
    tables, events = {}, {}
    for m in project.user:
        for info in m.values.values():
            if getattr(info, "kind", None) == "store" and info.module is m:
                for tbl in info.tables.values():
                    tables[table_id(tbl)] = {"name": tbl.qname, "key": type_text(tbl.key), "value": type_text(tbl.value),
                                             "key_shape": shape(tbl.key), "value_shape": shape(tbl.value),
                                             "key_encoding": shape(tbl.key, nominal=True)}
        for t in m.types.values():
            if t.kind == "event" and t.module is m:
                events[type_id(t)] = event_shape(t)
    return {"tables": tables, "events": events}


def subscriptions(project) -> list:
    """Обработчики программы и их события: по ним считается очередь при дренаже миграции (HST-11)."""
    out = []
    for m in project.user:
        for info in m.values.values():
            if getattr(info, "kind", None) == "handler" and info.module is m:
                out.append([info.qname, type_text(info.params[0])])
    return sorted(out)


def schema_digest(project) -> str:
    return C.digest("data-schema", "1", schema_of(project))


class Store:
    def __init__(self, path: str):
        self.path = path
        self.db = sqlite3.connect(path, isolation_level=None, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)
        for name, default in (("state_version", "0"), ("epoch", "0"), ("schema", ""), ("schema_json", "{}"),
                              ("subscriptions", "[]"), ("writer_lock", "")):
            self.db.execute("INSERT OR IGNORE INTO meta VALUES (?, ?)", (name, default))

    # ------------------------------------------------------------ meta
    def meta(self, name: str) -> str:
        return self.db.execute("SELECT value FROM meta WHERE name = ?", (name,)).fetchone()[0]

    def set_meta(self, name: str, value):
        self.db.execute("UPDATE meta SET value = ? WHERE name = ?", (str(value), name))

    def bind(self, project) -> str | None:
        """Активная привязка схемы (D10): первая программа привязывает пустую базу; иначе схема должна совпасть."""
        want = schema_digest(project)
        have = self.meta("schema")
        if have == "":
            self.db.execute("BEGIN IMMEDIATE")
            try:
                have = self.meta("schema")              # перепроверка под записью: другой процесс мог успеть
                if have == "":
                    for tid in schema_of(project)["tables"]:
                        self.ensure_table(tid)
                    self.activate(project)
                self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise
            if have == "":
                return None
        return None if have == want else have

    def activate(self, project):
        """Записать активную привязку (внутри транзакции вызывающего): дайджест, схема, подписки."""
        self.set_meta("schema", schema_digest(project))
        self.set_meta("schema_json", C.encode(schema_of(project)).decode("utf-8"))
        self.set_meta("subscriptions", C.encode(subscriptions(project)).decode("utf-8"))

    def backlog(self) -> list:
        """Недоставленные события по подпискам активной привязки: [(обработчик, seq)]."""
        out = []
        for handler, event in C.decode(self.meta("subscriptions").encode("utf-8")):
            out += [(handler, s) for s, _ in self.pending(handler, event)]
        return out

    def ensure_table(self, tid: str, prefix: str = "t_"):
        self.db.execute(f'CREATE TABLE IF NOT EXISTS "{prefix}{tid}" (key BLOB PRIMARY KEY, value BLOB NOT NULL)')

    # ------------------------------------------------------------ строки таблиц
    @staticmethod
    def enc(v, t) -> bytes:
        return C.encode(observe(v, t))

    @staticmethod
    def dec(b: bytes, t):
        return C.unobserve(C.decode(bytes(b)), t, nominal=False)

    def get(self, tid, tbl, k):
        row = self.db.execute(f'SELECT value FROM "t_{tid}" WHERE key = ?', (self.enc(k, tbl.key),)).fetchone()
        return None if row is None else self.dec(row[0], tbl.value)

    def put(self, tid, tbl, k, v):
        self.db.execute(f'INSERT OR REPLACE INTO "t_{tid}" VALUES (?, ?)', (self.enc(k, tbl.key), self.enc(v, tbl.value)))

    def remove(self, tid, tbl, k):
        self.db.execute(f'DELETE FROM "t_{tid}" WHERE key = ?', (self.enc(k, tbl.key),))

    def rows(self, tid, key_t, value_t, prefix: str = "t_") -> list:
        """Все строки в порядке Key (data-values §6)."""
        out = [(self.dec(k, key_t), self.dec(v, value_t))
               for k, v in self.db.execute(f'SELECT key, value FROM "{prefix}{tid}"')]
        return sorted(out, key=lambda kv: key_of(kv[0]))

    def clear(self, tid):
        self.db.execute(f'DELETE FROM "t_{tid}"')

    # ------------------------------------------------------------ outbox, inbox, receipts, журнал
    def emit(self, event: str, payload: bytes, origin: str, state_version: int) -> int:
        cur = self.db.execute("INSERT INTO outbox (event, payload, origin, state_version) VALUES (?, ?, ?, ?)",
                              (event, payload, origin, state_version))
        return cur.lastrowid

    def receipt(self, namespace: str, key: str):
        return self.db.execute("SELECT request, outcome, result, state_version FROM receipts WHERE namespace = ? AND key = ?",
                               (namespace, key)).fetchone()

    def put_receipt(self, namespace, key, request, outcome, result: bytes, state_version):
        self.db.execute("INSERT INTO receipts VALUES (?, ?, ?, ?, ?, ?)",
                        (namespace, key, request, outcome, result, state_version))

    def journal(self, kind: str, ref: str, body) -> int:
        return self.db.execute("INSERT INTO journal (kind, ref, body) VALUES (?, ?, ?)",
                               (kind, ref, C.encode(body))).lastrowid

    def journal_entries(self, ref: str) -> list:
        return [(kind, C.decode(bytes(body))) for kind, body in
                self.db.execute("SELECT kind, body FROM journal WHERE ref = ? ORDER BY seq", (ref,))]

    def pending(self, handler: str, event: str) -> list:
        """События типа event, ещё не обработанные handler (outbox без записи inbox), в порядке seq."""
        return self.db.execute(
            "SELECT seq, payload FROM outbox WHERE event = ? AND seq NOT IN (SELECT seq FROM inbox WHERE handler = ?) "
            "ORDER BY seq", (event, handler)).fetchall()

    def close(self):
        self.db.close()
