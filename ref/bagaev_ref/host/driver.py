"""Хост исполнения (spec/runtime/host.md): команды, запросы, обработчики событий, квитанции, журнал, replay.

Порядок обработки команды (HST-05, D44, R16 §7): форма → полномочие → digest → замок и привязка схемы →
в одной транзакции: повторная проверка замка и привязки → поиск receipt → guard версии → исполнение →
атомарная фиксация данных, outbox, receipt и журнала.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from bagaev_ref.kernel import canonical as C
from bagaev_ref.machine import cek
from bagaev_ref.machine.observe import observe, type_text
from bagaev_ref.machine.runner import observation
from bagaev_ref.machine.values import NONE, MapV, some
from bagaev_ref.sema import types as T
from bagaev_ref.sema.project import FnInfo
from bagaev_ref.host.store import Store, schema_digest, schema_of, table_id

KEY_RE = re.compile(r"[A-Za-z0-9_-]{16,128}")
NS_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
MAX_VERSION = 2**63 - 1                          # Counter — Int64 без переполнения (CANON-07)


SIMULATED_CRASH = None


class Crashed(BaseException):
    """Сбой внутри процесса (сценарии conformance): соединение бросается без фиксации, как при kill -9."""


def crash_point(name: str):
    """Точка сбоя (HST-16): процесс завершается как при kill -9, без отката и без ответа."""
    if os.environ.get("BAG_CRASH_AT") == name:
        os._exit(137)
    if SIMULATED_CRASH == name:
        raise Crashed(name)


def refused(code: str, **data) -> dict:
    """Отказ до допуска команды (HST-05): ключ не резервируется, данные не меняются."""
    return {"outcome": "REFUSED", "code": code, **({"data": data} if data else {})}


RESOURCE_LIMIT = {"termination": "IMPLEMENTATION_STOP", "code": "RESOURCE_LIMIT"}


class Program:
    """Проверенная и понижённая программа плюс её таблицы и события по полным именам."""

    def __init__(self, project, prog):
        self.project, self.prog = project, prog
        self.tables, self.events, self.handlers = {}, {}, []
        for m in project.user:
            for info in m.values.values():
                if getattr(info, "kind", None) == "store" and info.module is m:
                    for tbl in info.tables.values():
                        self.tables[tbl.qname] = tbl
                if isinstance(info, FnInfo) and info.kind == "handler" and info.module is m:
                    self.handlers.append(info)
            for t in m.types.values():
                if t.kind == "event":
                    self.events[t.qname] = t
        self.handlers.sort(key=lambda h: h.qname)
        self.schema = schema_digest(project)

    def entry(self, qname: str):
        mod, _, name = qname.rpartition(".")
        m = self.project.modules.get(mod)
        info = m.values.get(name) if m is not None and not m.is_std else None
        return info if isinstance(info, FnInfo) else None


def gate(store: Store, program: Program) -> dict | None:
    """Замок миграции и привязка схемы (HST-05 шаг 5, HST-04). Вызывается до транзакции (пустое хранилище при этом
    привязывается) и повторно внутри неё: миграция могла переключить привязку, пока транзакция ждала записи."""
    lock = store.meta("writer_lock")
    if lock:
        return refused("MIGRATION_IN_PROGRESS", lock=lock)
    if store.db.in_transaction:
        have = store.meta("schema")
        return None if have == program.schema else refused("SCHEMA_BINDING_MISMATCH")
    return None if store.bind(program.project) is None else refused("SCHEMA_BINDING_MISMATCH")


def next_version(store: Store) -> int | None:
    sv = int(store.meta("state_version"))
    return None if sv >= MAX_VERSION else sv + 1


def store_arg_types(name: str, tbl) -> list:
    return {"std.store.get": [tbl.key], "std.store.contains": [tbl.key], "std.store.all": [],
            "std.store.put": [tbl.key, tbl.value], "std.store.remove": [tbl.key],
            "std.store.replace_all": [T.TCon("Map", [tbl.key, tbl.value])]}[name]


def store_result_type(name: str, tbl):
    return {"std.store.get": T.TCon("Option", [tbl.value]), "std.store.contains": T.BOOL,
            "std.store.all": T.TCon("Map", [tbl.key, tbl.value])}.get(name, T.UNIT)


def enc(v, t) -> str:
    return C.encode(observe(v, t)).decode("utf-8")


class TxHost:
    """Исполнитель Perform внутри транзакции точки входа (HST-08): проверка атома (EFF-11), чтение и запись
    таблиц, outbox; каждая операция с аргументами и результатом пишется в журнал (HST-12)."""

    def __init__(self, store: Store, program: Program, granted: frozenset, read_only: bool = False):
        self.store, self.program, self.granted, self.read_only = store, program, granted, read_only
        self.ops: list = []
        self.events: list = []

    def perform(self, op: str, resource: str, args: tuple, node):
        name = op[:-2]
        if name == "event.emit":
            if ("emits", resource) not in self.granted or self.read_only:
                raise cek.HostStop("ACCESS_DENIED", atom=f"emits {resource}")
            payload = enc(args[0], T.TNom(self.program.events[resource], []))
            self.events.append((resource, payload.encode("utf-8")))
            self.ops.append({"op": "emit", "resource": resource, "payload": payload})
            return None
        tbl = self.program.tables[resource]
        tid = table_id(tbl)
        kind = "reads" if name in ("std.store.get", "std.store.contains", "std.store.all") else "writes"
        if (kind, resource) not in self.granted or (self.read_only and kind == "writes"):
            raise cek.HostStop("ACCESS_DENIED", atom=f"{kind} {resource}")
        if name == "std.store.get":
            v = self.store.get(tid, tbl, args[0])
            result = NONE if v is None else some(v)
        elif name == "std.store.contains":
            result = self.store.get(tid, tbl, args[0]) is not None
        elif name == "std.store.all":
            result = MapV(dict(self.store.rows(tid, tbl.key, tbl.value)))
        elif name == "std.store.put":
            self.store.put(tid, tbl, args[0], args[1])
            result = None
        elif name == "std.store.remove":
            self.store.remove(tid, tbl, args[0])
            result = None
        elif name == "std.store.replace_all":
            self.store.clear(tid)
            for k, v in args[0].d.items():
                self.store.put(tid, tbl, k, v)
            result = None
        else:
            raise AssertionError(name)
        self.ops.append({"op": name, "resource": resource,
                         "args": [enc(a, t) for a, t in zip(args, store_arg_types(name, tbl))],
                         "result": enc(result, store_result_type(name, tbl))})
        return result


class ReplayHost:
    """Replay по журналу (HST-13): ответы чтения берутся из журнала; операции, их аргументы, записи и события
    только сверяются. Хранилище не читается и не меняется; внешний мир не вызывается."""

    def __init__(self, program: Program, ops: list):
        self.program, self.ops, self.i = program, ops, 0

    def perform(self, op: str, resource: str, args: tuple, node):
        name = op[:-2]
        if self.i >= len(self.ops):
            raise cek.HostStop("REPLAY_DIVERGENCE", detail="операций больше, чем в журнале")
        rec = self.ops[self.i]
        self.i += 1
        want = "emit" if name == "event.emit" else name
        if rec["op"] != want or rec["resource"] != resource:
            raise cek.HostStop("REPLAY_DIVERGENCE", detail=f"шаг {self.i}: {want} {resource} вместо {rec['op']} {rec['resource']}")
        if name == "event.emit":
            if enc(args[0], T.TNom(self.program.events[resource], [])) != rec["payload"]:
                raise cek.HostStop("REPLAY_DIVERGENCE", detail=f"шаг {self.i}: другое событие")
            return None
        tbl = self.program.tables[resource]
        if [enc(a, t) for a, t in zip(args, store_arg_types(name, tbl))] != rec.get("args"):
            raise cek.HostStop("REPLAY_DIVERGENCE", detail=f"шаг {self.i}: другие аргументы {want}")
        return C.unobserve(C.decode(rec["result"].encode("utf-8")), store_result_type(name, tbl), nominal=False)


# ------------------------------------------------------------ команды и запросы
def parse_args(info: FnInfo, args_json) -> tuple:
    if not isinstance(args_json, list) or len(args_json) != len(info.params):
        raise C.BadValue(f"нужно {len(info.params)} аргументов")
    return tuple(C.unobserve(a, t) for a, t in zip(args_json, info.params))


def allowed(policy: dict | None, caller: str, entry: str) -> bool:
    """Политика хоста (HST-09): какие точки входа вызывает какой вызывающий. Нет раздела callers — разрешено всё."""
    if policy is None or "callers" not in policy:
        return True
    grants = policy.get("callers", {}).get(caller, [])
    return entry in grants or "*" in grants


def request_digest(info: FnInfo, entry: str, args: tuple) -> str:
    """Дайджест запроса (HST-05): точка входа и аргументы в канонической форме CANON-11. Guard StateVersion —
    условие одной попытки, а не часть запроса; вызывающий и полномочия тоже не входят."""
    return C.digest("command-request", "1", {"entry": entry, "args": [observe(a, t) for a, t in zip(args, info.params)]})


def granted(policy: dict | None, info: FnInfo) -> frozenset:
    """Атомы, выданные исполнению (EFF-11): объявленный ряд точки входа без отозванных политикой хоста."""
    revoked = set((policy or {}).get("revoke", []))
    return frozenset(a for a in info.row.atoms if T.show_atom(a) not in revoked)


def run_command(store: Store, program: Program, entry: str, args_json, keyref: dict, caller: str = "anonymous",
                expected_state=None, policy: dict | None = None, fuel: int = 10_000_000) -> dict:
    info = program.entry(entry)
    if info is None or info.kind != "command":
        return refused("UNKNOWN_ENTRYPOINT", name=entry)
    if not info.pub:
        return refused("ENTRYPOINT_NOT_EXPORTED", name=entry)
    try:
        args = parse_args(info, args_json)
    except C.BadValue as e:
        return refused("REQUEST_INVALID", detail=str(e))
    ns, key = keyref.get("namespace", ""), keyref.get("key", "")
    if not (isinstance(ns, str) and isinstance(key, str) and NS_RE.fullmatch(ns) and KEY_RE.fullmatch(key)):
        return refused("REQUEST_INVALID", detail="KeyRef: namespace — Id, key — 16…128 [A-Za-z0-9_-] (CANON-10)")
    if not allowed(policy, caller, entry):
        return refused("ACCESS_DENIED", entry=entry, caller=caller)
    request = request_digest(info, entry, args)
    g = gate(store, program)
    if g is not None:
        return g
    crash_point("before_begin")
    store.db.execute("BEGIN IMMEDIATE")
    try:
        g = gate(store, program)                        # перепроверка под записью (HST-05)
        if g is not None:
            store.db.execute("ROLLBACK")
            return g
        r = store.receipt(ns, key)
        if r is not None:                               # квитанция ищется до guard версии (D44)
            store.db.execute("ROLLBACK")
            if r[0] != request:
                return refused("IDEMPOTENCY_CONFLICT", namespace=ns, key=key)
            return dict(C.decode(bytes(r[2])), outcome=r[1], final=True, replayed=True, state_version=r[3])
        sv = int(store.meta("state_version"))
        if expected_state is not None and int(expected_state) != sv:
            store.db.execute("ROLLBACK")
            return refused("STALE_STATE", expected=int(expected_state), actual=sv)
        new_sv = next_version(store)
        if new_sv is None:
            store.db.execute("ROLLBACK")
            return refused("STATE_VERSION_EXHAUSTED")
        host = TxHost(store, program, granted(policy, info))
        store.db.execute("SAVEPOINT body")
        try:
            ex = run_entry(program, info, args, fuel, host)
            obs = observation(ex, info.ret, False)
        except RecursionError:                          # предел реализации (HST-19)
            store.db.execute("ROLLBACK")
            return dict(RESOURCE_LIMIT, outcome="ABORTED", final=False, replayed=False)
        obs.pop("effects", None)
        if ex.termination == "RETURNED" and ex.value.tag == "Ok":
            outcome = "COMMITTED"
            store.db.execute("RELEASE body")
        elif ex.termination == "RETURNED":
            outcome = "ABORTED"                         # Err: квитанция отказа без изменений данных (HST-06)
            store.db.execute("ROLLBACK TO body")
            store.db.execute("RELEASE body")
            host.events = []
        else:
            store.db.execute("ROLLBACK")                # FAULT и остановки: ничего не фиксируется, квитанции нет
            return dict(obs, outcome="ABORTED", final=False, termination=ex.termination, replayed=False)
        store.set_meta("state_version", new_sv)
        if outcome == "COMMITTED":
            for ev, payload in host.events:
                store.emit(ev, payload, f"{ns}:{key}", new_sv)
        result = {"value": obs["value"]}
        store.put_receipt(ns, key, request, outcome, C.encode(result), new_sv)
        store.journal("command", f"{ns}:{key}", {"entry": entry, "args": [observe(a, t) for a, t in zip(args, info.params)],
                                                  "ops": host.ops, "outcome": outcome, "value": obs["value"]})
        crash_point("before_commit")
        store.db.execute("COMMIT")
    except BaseException:
        if store.db.in_transaction:
            store.db.execute("ROLLBACK")
        raise
    crash_point("after_commit")
    return dict(result, outcome=outcome, final=True, replayed=False, state_version=new_sv)


def run_entry(program: Program, info: FnInfo, args: tuple, fuel: int, host):
    """Тело точки входа в окружении параметров (как после CALL_BODY: последний параметр — индекс 0, BIR-04)."""
    env = None
    for a in args:
        env = (a, env)
    return cek.run(program.prog.functions[info].body, env, fuel, host=host)


def run_query(store: Store, program: Program, entry: str, args_json, caller: str = "anonymous",
              policy: dict | None = None, fuel: int = 10_000_000) -> dict:
    """query — чтение согласованного снимка (HST-10): отдельная транзакция чтения, без квитанции."""
    info = program.entry(entry)
    if info is None or info.kind != "query":
        return refused("UNKNOWN_ENTRYPOINT", name=entry)
    if not info.pub:
        return refused("ENTRYPOINT_NOT_EXPORTED", name=entry)
    try:
        args = parse_args(info, args_json)
    except C.BadValue as e:
        return refused("REQUEST_INVALID", detail=str(e))
    if not allowed(policy, caller, entry):
        return refused("ACCESS_DENIED", entry=entry, caller=caller)
    if store.bind(program.project) is not None:
        return refused("SCHEMA_BINDING_MISMATCH")
    store.db.execute("BEGIN")
    try:
        if store.meta("schema") != program.schema:      # снимок мог смениться миграцией после проверки
            return refused("SCHEMA_BINDING_MISMATCH")
        ex = run_entry(program, info, args, fuel, TxHost(store, program, granted(policy, info), read_only=True))
        obs = observation(ex, info.ret, False)
    except RecursionError:
        return dict(RESOURCE_LIMIT, outcome="IMPLEMENTATION_STOP")
    finally:
        store.db.execute("ROLLBACK")
    obs.pop("effects", None)
    return obs


def status(store: Store, keyref: dict, program: Program | None = None, entry: str | None = None,
           args_json=None) -> dict:
    """Чтение квитанции по KeyRef (HST-07): ничего не исполняет. Нет квитанции — ABSENT_AT_READ с версией.
    С запросом (точка входа и аргументы) квитанция другого запроса — IDEMPOTENCY_CONFLICT, как при повторе."""
    r = store.receipt(keyref.get("namespace", ""), keyref.get("key", ""))
    if r is None:
        return {"outcome": "ABSENT_AT_READ", "state_version": int(store.meta("state_version"))}
    if entry is not None:
        info = program.entry(entry)
        try:
            args = parse_args(info, args_json) if info is not None else None
        except C.BadValue:
            args = None
        if args is None or r[0] != request_digest(info, entry, args):
            return refused("IDEMPOTENCY_CONFLICT", namespace=keyref.get("namespace", ""), key=keyref.get("key", ""))
    return dict(C.decode(bytes(r[2])), outcome="RESULT", receipt_outcome=r[1], state_version=r[3])


def event_status(store: Store, handler: str, seq: int) -> dict:
    """Чтение квитанции обработки (HST-07): запись inbox или ABSENT_AT_READ с текущей версией."""
    row = store.db.execute("SELECT outcome FROM inbox WHERE handler = ? AND seq = ?", (handler, seq)).fetchone()
    if row is None:
        return {"outcome": "ABSENT_AT_READ", "state_version": int(store.meta("state_version"))}
    return {"outcome": "RESULT", "handler": handler, "seq": seq, "receipt_outcome": row[0]}


# ------------------------------------------------------------ события
def deliver(store: Store, program: Program, handler: str | None = None, seq: int | None = None,
            fuel: int = 10_000_000, policy: dict | None = None) -> list:
    """Доставка outbox обработчикам (HST-11): событие — отдельная транзакция обработчика; повтор дедуплицируется
    по (обработчик, seq); FAULT оставляет событие недоставленным и останавливает очередь обработчика. Явный seq —
    внеочередная доставка оператора."""
    g = gate(store, program)
    if g is not None:
        return [g]
    out = []
    for h in program.handlers:
        if handler is not None and h.qname != handler:
            continue
        ev_info = T.prune(h.params[0]).info
        if seq is not None:
            row = store.db.execute("SELECT seq, payload FROM outbox WHERE seq = ? AND event = ?",
                                   (seq, ev_info.qname)).fetchone()
            todo = [row] if row else []
        else:
            todo = store.pending(h.qname, ev_info.qname)
        for s, payload in todo:
            r = deliver_one(store, program, h, ev_info, s, payload, fuel, policy)
            out.append(r)
            if r["outcome"] != "COMMITTED":
                break                                   # порядок outbox для обработчика: дальше не идём (HST-11)
    return out


def deliver_one(store, program, h, ev_info, s, payload, fuel, policy=None) -> dict:
    crash_point("before_begin")
    store.db.execute("BEGIN IMMEDIATE")
    try:
        g = gate(store, program)
        if g is not None:
            store.db.execute("ROLLBACK")
            return g
        done = store.db.execute("SELECT outcome FROM inbox WHERE handler = ? AND seq = ?", (h.qname, s)).fetchone()
        if done is not None:
            store.db.execute("ROLLBACK")
            return {"handler": h.qname, "seq": s, "outcome": done[0], "replayed": True}
        new_sv = next_version(store)
        if new_sv is None:
            store.db.execute("ROLLBACK")
            return refused("STATE_VERSION_EXHAUSTED")
        event = C.unobserve(C.decode(bytes(payload)), T.TNom(ev_info, []), nominal=False)
        host = TxHost(store, program, granted(policy, h))
        try:
            ex = run_entry(program, h, (event,), fuel, host)
        except RecursionError:
            store.db.execute("ROLLBACK")
            return dict(RESOURCE_LIMIT, handler=h.qname, seq=s, outcome="ABORTED")
        if ex.termination != "RETURNED":
            store.db.execute("ROLLBACK")
            r = {"handler": h.qname, "seq": s, "outcome": "ABORTED", "termination": ex.termination, "code": ex.code}
            if ex.site:
                r["site"] = {"file": ex.site[0], "span": [ex.site[1], ex.site[2]]}
            return r
        store.set_meta("state_version", new_sv)
        for ev, p in host.events:
            store.emit(ev, p, f"{h.qname}:{s}", new_sv)
        store.db.execute("INSERT INTO inbox VALUES (?, ?, ?, ?)", (h.qname, s, "COMMITTED", None))
        store.journal("handler", f"{h.qname}:{s}", {"handler": h.qname, "seq": str(s), "ops": host.ops,
                                                     "outcome": "COMMITTED"})
        crash_point("before_commit")
        store.db.execute("COMMIT")
    except BaseException:
        if store.db.in_transaction:
            store.db.execute("ROLLBACK")
        raise
    crash_point("after_commit")
    return {"handler": h.qname, "seq": s, "outcome": "COMMITTED", "replayed": False, "state_version": new_sv}


# ------------------------------------------------------------ replay, засев, состояние
def replay(store: Store, program: Program, ref: str, fuel: int = 10_000_000) -> dict:
    """Перепроверка исполнения по журналу (HST-13): та же программа, ответы чтения из журнала."""
    entries = store.journal_entries(ref)
    if not entries:
        return {"outcome": "ABSENT_AT_READ", "ref": ref}
    kind, body = entries[-1]
    if kind not in ("command", "handler"):
        return refused("REQUEST_INVALID", detail="replay — только для исполнений command и handler")
    try:
        if kind == "command":
            info = program.entry(body["entry"])
            if info is None or info.kind != "command":
                return {"outcome": "REPLAY_DIVERGENCE", "ref": ref, "detail": "в программе нет этой команды"}
            args = parse_args(info, body["args"])
        else:
            info = next((h for h in program.handlers if h.qname == body["handler"]), None)
            if info is None:
                return {"outcome": "REPLAY_DIVERGENCE", "ref": ref, "detail": "в программе нет этого обработчика"}
            row = store.db.execute("SELECT payload FROM outbox WHERE seq = ?", (int(body["seq"]),)).fetchone()
            args = (C.unobserve(C.decode(bytes(row[0])), info.params[0], nominal=False),)
    except C.BadValue as e:
        return {"outcome": "REPLAY_DIVERGENCE", "ref": ref, "detail": f"вход не подходит программе: {e}"}
    host = ReplayHost(program, body["ops"])
    try:
        ex = run_entry(program, info, args, fuel, host)
        got = observe(ex.value, info.ret) if kind == "command" and ex.termination == "RETURNED" else None
    except RecursionError:
        return dict(RESOURCE_LIMIT, outcome="IMPLEMENTATION_STOP", ref=ref)
    if ex.termination == "IMPLEMENTATION_STOP" and ex.code == "REPLAY_DIVERGENCE":
        return {"outcome": "REPLAY_DIVERGENCE", "ref": ref, "detail": (ex.data or {}).get("detail")}
    if host.i != len(body["ops"]):
        return {"outcome": "REPLAY_DIVERGENCE", "ref": ref, "detail": "журнал содержит больше операций"}
    if kind == "command" and got != body["value"]:
        return {"outcome": "REPLAY_DIVERGENCE", "ref": ref, "detail": "другой результат"}
    if kind == "handler" and ex.termination != "RETURNED":
        return {"outcome": "REPLAY_DIVERGENCE", "ref": ref, "detail": "обработчик не завершился"}
    return {"outcome": "REPLAY_MATCH", "ref": ref, "operations": len(body["ops"])}


def seed(store: Store, program: Program, table: str, entries) -> dict:
    """Служебная загрузка строк (фикстуры): одна транзакция, StateVersion +1, запись в журнал."""
    g = gate(store, program)
    if g is not None:
        return g
    tbl = program.tables.get(table)
    if tbl is None:
        return refused("REQUEST_INVALID", detail=f"нет таблицы {table}")
    try:
        rows = [(C.unobserve(k, tbl.key), C.unobserve(v, tbl.value)) for k, v in entries]
    except (C.BadValue, ValueError, TypeError) as e:
        return refused("REQUEST_INVALID", detail=str(e))
    store.db.execute("BEGIN IMMEDIATE")
    try:
        g = gate(store, program)
        if g is not None:
            store.db.execute("ROLLBACK")
            return g
        sv = next_version(store)
        if sv is None:
            store.db.execute("ROLLBACK")
            return refused("STATE_VERSION_EXHAUSTED")
        for k, v in rows:
            store.put(table_id(tbl), tbl, k, v)
        store.set_meta("state_version", sv)
        store.journal("seed", f"seed:{table}", {"table": table, "rows": str(len(rows))})
        store.db.execute("COMMIT")
    except BaseException:
        if store.db.in_transaction:
            store.db.execute("ROLLBACK")
        raise
    return {"outcome": "COMMITTED", "rows": len(rows), "state_version": sv}


def dump(store: Store, program: Program) -> dict:
    """Состояние хранилища для сравнения (наблюдение state, HST-17)."""
    tables = {}
    for qn, tbl in sorted(program.tables.items()):
        tid = table_id(tbl)
        if store.db.execute("SELECT name FROM sqlite_master WHERE name = ?", (f"t_{tid}",)).fetchone() is None:
            continue
        tables[qn] = [[observe(k, tbl.key), observe(v, tbl.value)] for k, v in store.rows(tid, tbl.key, tbl.value)]
    outbox = [{"seq": s, "event": e, "payload": json.loads(bytes(p).decode("utf-8"))}
              for s, e, p in store.db.execute("SELECT seq, event, payload FROM outbox ORDER BY seq")]
    inbox = [{"handler": h, "seq": s, "outcome": o} for h, s, o in
             store.db.execute("SELECT handler, seq, outcome FROM inbox ORDER BY handler, seq")]
    pending = [{"handler": h, "seq": s} for h, s in store.backlog()]   # недостроенные проекции видны явно
    return {"state_version": int(store.meta("state_version")), "epoch": int(store.meta("epoch")),
            "tables": tables, "outbox": outbox, "inbox": inbox, "pending": pending}


def load_policy(root: Path) -> dict | None:
    p = root / "host-policy.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


__all__ = ["Program", "run_command", "run_query", "status", "deliver", "replay", "seed", "dump", "schema_of",
           "schema_digest", "type_text"]
