"""Миграция хранилища при остановленных писателях (spec/runtime/host.md §7, D10, D81).

plan — сравнить активную привязку с новой программой и назначить действие каждой таблице и событию;
apply — writer_lock → дренаж очереди → одна транзакция: guard на привязку, epoch, StateVersion и замок →
теневые таблицы с проверкой каждой строки → переключение и epoch + 1.
"""
from __future__ import annotations

from bagaev_ref.kernel import canonical as C
from bagaev_ref.machine.observe import observe, type_text
from bagaev_ref.machine.values import key_of
from bagaev_ref.sema import types as T
from bagaev_ref.host.driver import Program, crash_point, next_version, refused, run_entry
from bagaev_ref.host.store import Store, schema_digest, schema_of, shape, table_id


def migrations_of(program: Program) -> dict:
    """EntityId таблицы → объявления migration новой программы (`migration … on <таблица>`)."""
    out = {}
    for m in program.project.user:
        for info in m.values.values():
            if getattr(info, "kind", None) == "migration" and info.module is m:
                out.setdefault(table_id(info.table), []).append(info)
    return out


def plan(store: Store, program: Program) -> dict:
    """Действие для каждой таблицы (keep, rename, create, migrate) и события (keep, rename, create, change, remove);
    отказ — до любых изменений (HST-14)."""
    old = C.decode(store.meta("schema_json").encode("utf-8"))
    new = schema_of(program.project)
    have, want = store.meta("schema"), schema_digest(program.project)
    base = {"from_schema": have, "to_schema": want, "epoch": int(store.meta("epoch")),
            "state_version": int(store.meta("state_version"))}
    if have == "":
        return refused("MIGRATION_NOT_BOUND")
    if have == want:
        return dict(base, outcome="UP_TO_DATE", tables=[], events=[])
    migs = migrations_of(program)
    ot, nt = old.get("tables", {}), new["tables"]
    tables, problems = [], []
    for tid in sorted(set(ot) | set(nt)):
        o, n = ot.get(tid), nt.get(tid)
        if n is None:
            problems.append({"table": o["name"], "id": tid, "reason": "TABLE_REMOVED"})
            continue
        if o is None:
            tables.append({"table": n["name"], "id": tid, "action": "create"})
            continue
        if o.get("key_shape") != n["key_shape"]:
            problems.append({"table": n["name"], "id": tid, "reason": "KEY_TYPE_CHANGED", "from": o["key"], "to": n["key"]})
            continue
        if o.get("value_shape") == n["value_shape"]:              # строение то же: имя типа и таблицы — метаданные
            tables.append({"table": n["name"], "id": tid, "action": "keep" if o["name"] == n["name"] else "rename"})
            continue
        # миграция выбирается по строению: Old — прежнее строение значения, New — новое (HST-14)
        cand = [mi for mi in migs.get(tid, []) if shape(mi.params[0]) == o.get("value_shape")
                and shape(T.prune(mi.ret).args[0]) == n["value_shape"]]
        if len(cand) != 1:
            problems.append({"table": n["name"], "id": tid, "reason": "MIGRATION_MISSING" if not cand else "MIGRATION_AMBIGUOUS",
                             "from": o["value"], "to": n["value"]})
            continue
        tables.append({"table": n["name"], "id": tid, "action": "migrate", "migration": cand[0].qname,
                       "from": o["value"], "to": n["value"]})
    oe, ne = old.get("events", {}), new["events"]
    events = []
    for eid in sorted(set(oe) | set(ne)):
        o, n = oe.get(eid), ne.get(eid)
        action = ("remove" if n is None else "create" if o is None else
                  "change" if o.get("shape") != n["shape"] else "keep" if o["name"] == n["name"] else "rename")
        events.append({"event": (n or o)["name"], "id": eid, "action": action})
    if problems:
        return refused("MIGRATION_PLAN_INVALID", problems=problems)
    body = dict(base, tables=tables, events=events)
    canon = dict(body, epoch=str(body["epoch"]), state_version=str(body["state_version"]))   # без чисел (CANON-02)
    return dict(body, outcome="PLANNED", plan_id=C.digest("migration-plan", "1", canon))


def apply(store: Store, program: Program, fuel: int = 10_000_000) -> dict:
    p = plan(store, program)
    if p["outcome"] != "PLANNED":
        return p
    pid = p["plan_id"]
    # 1. writer_lock: после него команды и доставка получают MIGRATION_IN_PROGRESS (HST-15)
    store.db.execute("BEGIN IMMEDIATE")
    lock = store.meta("writer_lock")
    if lock not in ("", pid):
        store.db.execute("ROLLBACK")
        return refused("MIGRATION_IN_PROGRESS", lock=lock)
    store.set_meta("writer_lock", pid)
    store.db.execute("COMMIT")
    # 2. дренаж: очередь событий по подпискам активной привязки должна быть пуста
    backlog = store.backlog()
    if backlog:
        release(store, pid)
        return refused("MIGRATION_BACKLOG", pending=[{"handler": h, "seq": s} for h, s in backlog[:20]],
                       count=len(backlog))
    crash_point("migration_prepare")
    # 3–4. одна транзакция: guard, теневые таблицы с проверкой строк, переключение. Второй apply того же плана
    # ждёт записи и после фиксации первого видит другую привязку — теневые таблицы не делятся между процессами.
    by_id = {table_id(t): t for t in program.tables.values()}
    migs = {mi.qname: mi for ms in migrations_of(program).values() for mi in ms}
    store.db.execute("BEGIN IMMEDIATE")
    try:
        sv_now = int(store.meta("state_version"))
        if (store.meta("schema"), int(store.meta("epoch")), sv_now, store.meta("writer_lock")) != \
                (p["from_schema"], p["epoch"], p["state_version"], pid):
            store.db.execute("ROLLBACK")
            release(store, pid)
            return refused("STALE_STATE", expected=p["state_version"], actual=sv_now, reason="binding")
        old_tables = C.decode(store.meta("schema_json").encode("utf-8"))["tables"]
        new_tables = schema_of(program.project)["tables"]
        # Без key_encoding прежняя привязка не сообщает вложенные nominal-имена:
        # консервативно перекодируем существующие ключи, а не создаём пустую таблицу.
        shadows = {t["id"] for t in p["tables"] if t["action"] == "migrate" or
                   (t["action"] != "create" and old_tables[t["id"]].get("key_encoding") !=
                    new_tables[t["id"]]["key_encoding"])}
        migrated = 0
        for t in p["tables"]:
            if t["id"] not in shadows:
                continue
            tbl = by_id[t["id"]]
            mi = migs[t["migration"]] if t["action"] == "migrate" else None
            store.db.execute(f'DROP TABLE IF EXISTS "s_{t["id"]}"')
            store.ensure_table(t["id"], prefix="s_")
            rows = [(C.unobserve(C.decode(bytes(kb)), tbl.key, nominal=False), kb, vb)
                    for kb, vb in store.db.execute(f'SELECT key, value FROM "t_{t["id"]}"').fetchall()]
            for k, kb, vb in sorted(rows, key=lambda r: key_of(r[0])):    # строки — в порядке Key (HST-15)
                if mi is not None:
                    ex = run_entry(program, mi, (C.unobserve(C.decode(bytes(vb)), mi.params[0], nominal=False),), fuel, None)
                    if ex.termination != "RETURNED" or ex.value.tag != "Ok":
                        store.db.execute("ROLLBACK")            # теневые таблицы исчезают вместе с транзакцией
                        release(store, pid)
                        key = C.decode(bytes(kb))
                        if ex.termination == "RETURNED":
                            return refused("MIGRATION_FAILED", table=t["table"], key=key,
                                           error=observe(ex.value.payload, T.prune(mi.ret).args[1]))
                        return refused("MIGRATION_FAILED", table=t["table"], key=key, error=ex.code, termination=ex.termination)
                    vb = Store.enc(ex.value.payload, tbl.value)
                    migrated += 1
                # INSERT без REPLACE: коллизия не должна молча терять строку. При любой
                # ошибке откатятся и ключи, и значения, и переключение привязки.
                store.db.execute(f'INSERT INTO "s_{t["id"]}" VALUES (?, ?)', (Store.enc(k, tbl.key), bytes(vb)))
        sv = next_version(store)
        if sv is None:
            store.db.execute("ROLLBACK")
            release(store, pid)
            return refused("STATE_VERSION_EXHAUSTED")
        for t in p["tables"]:
            if t["action"] == "create":
                store.ensure_table(t["id"])
            elif t["id"] in shadows:
                store.db.execute(f'DROP TABLE "t_{t["id"]}"')
                store.db.execute(f'ALTER TABLE "s_{t["id"]}" RENAME TO "t_{t["id"]}"')
        epoch = p["epoch"] + 1
        store.activate(program.project)
        store.set_meta("epoch", epoch)
        store.set_meta("state_version", sv)
        store.set_meta("writer_lock", "")
        store.journal("migration", pid, {"plan_id": pid, "epoch": str(epoch), "tables": p["tables"],
                                         "events": p["events"], "rows": str(migrated)})
        crash_point("before_swap_commit")
        store.db.execute("COMMIT")
    except RecursionError:                              # предел реализации (HST-19): откат, замок снят
        if store.db.in_transaction:
            store.db.execute("ROLLBACK")
        release(store, pid)
        raise
    except BaseException:
        if store.db.in_transaction:
            store.db.execute("ROLLBACK")
        raise
    crash_point("after_swap")
    return {"outcome": "APPLIED", "plan_id": pid, "epoch": epoch, "state_version": sv, "rows": migrated,
            "tables": p["tables"], "events": p["events"]}


def release(store: Store, pid: str):
    store.db.execute("BEGIN IMMEDIATE")
    if store.meta("writer_lock") == pid:
        store.set_meta("writer_lock", "")
    store.db.execute("COMMIT")


def abort(store: Store) -> dict:
    """Снять writer_lock после сбоя и удалить теневые таблицы, если они остались; данные не тронуты."""
    store.db.execute("BEGIN IMMEDIATE")
    lock = store.meta("writer_lock")
    shadows = [r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 's\\_%' ESCAPE '\\'")]
    for name in shadows:
        store.db.execute(f'DROP TABLE "{name}"')
    store.set_meta("writer_lock", "")
    store.db.execute("COMMIT")
    return {"outcome": "ABORTED" if lock else "NO_MIGRATION", "lock": lock, "dropped": shadows}
