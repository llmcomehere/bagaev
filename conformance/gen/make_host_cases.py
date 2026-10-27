#!/usr/bin/env python3
"""Автор сценарных случаев хоста (Ф4): области store, events, migrate.

Ожидания посчитаны вручную по spec/runtime/host.md (HST-03…HST-17), outcomes.md OUT-03 и canonical.md
CANON-11; эталон для них не запускается (origin = independent). Программа — счётчик app.bag в трёх версиях:
v1 (Int64), v2 (запись Tally и миграция), v3 и v4 (недопустимые изменения схемы). @id заданы явно, чтобы
таблицы совпадали между версиями. Повторный запуск перезаписывает эти области.

  python3 conformance/gen/make_host_cases.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "conformance" / "cases"
AREAS = ("store", "events", "migrate")
_spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)


def anchor(heading: str) -> str:
    return f"spec/runtime/host.md#{_conf.slug(heading)}"


H1, H2, H3, H4, H5, H6, H7, H8 = (anchor(h) for h in (
    "1. Хранилище", "2. Привязка схемы", "3. Команда", "4. Запрос", "5. События", "6. Журнал и replay",
    "7. Миграция", "8. Сбои и восстановление"))
OUT3 = f"spec/kernel/outcomes.md#{_conf.slug('3. Исход точки входа')}"
EFF = f"spec/language/effects.md#{_conf.slug('4. Хранилище, события и точки входа')}"

# ---------------------------------------------------------------------------- программы
HEAD = '''@id("aa0001")
module app

use std.store

@id("aa0008")
pub type BumpError = enum {
  @id("aa0009") NonPositive,
  @id("aa000a") TooLarge,
}

@id("aa0005")
pub event Bumped {
  @id("aa0006") name: String,
  @id("aa0007") total: Int64,
}
'''

V1 = HEAD + '''
@id("aa0002")
pub store S {
  @id("aa0003") table counts: Map<String, Int64>
  @id("aa0004") table seen: Map<String, Int64>
}

/// Запись идёт до проверки предела: Err после неё обязан откатить запись (HST-06).
@id("aa000b")
pub command bump(name: String, by: Int64) -> Result<Int64, BumpError>
  uses { reads S.counts, writes S.counts, emits Bumped }
{
  if by <= 0 {
    return Err(BumpError.NonPositive)
  }
  let total = match store.get(S.counts, name) {
    Some(n) => n + by,
    None => by,
  };
  store.put(S.counts, name, total);
  if total > 100 {
    return Err(BumpError.TooLarge)
  }
  emit Bumped { name: name, total: total };
  Ok(total)
}

@id("aa000c")
pub query get(name: String) -> Option<Int64>
  uses { reads S.counts }
{
  store.get(S.counts, name)
}

/// Обработчик падает на итоге 13: деление на ноль (HST-11).
@id("aa000d")
handler remember(ev: Bumped)
  uses { writes S.seen }
{
  let _ = 100 / (ev.total - 13);
  store.put(S.seen, ev.name, ev.total);
}

@id("aa000e")
command hidden(name: String) -> Result<(), BumpError>
  uses { writes S.counts }
{
  store.remove(S.counts, name);
  Ok(())
}
'''

TALLY = '''
@id("aa000f")
pub type Tally = record {
  @id("aa000g") total: Int64,
  @id("aa000h") bumps: Int64,
}

@id("aa000k")
pub type MigErr = enum {
  @id("aa000m") Negative,
}
'''

V2 = HEAD + TALLY + '''
@id("aa0002")
pub store S {
  @id("aa0003") table counts: Map<String, Tally>
  @id("aa0004") table seen: Map<String, Int64>
}

@id("aa000c")
pub query get(name: String) -> Option<Tally>
  uses { reads S.counts }
{
  store.get(S.counts, name)
}

@id("aa000j")
migration to_tally on S.counts(old: Int64) -> Result<Tally, MigErr> {
  if old < 0 {
    Err(MigErr.Negative)
  } else {
    Ok(Tally { total: old, bumps: 1 })
  }
}
'''

V3 = HEAD + '''
@id("aa0002")
pub store S {
  @id("aa0003") table counts: Map<Int64, Int64>
}
'''

V4 = HEAD + TALLY + '''
@id("aa0002")
pub store S {
  @id("aa0003") table counts: Map<String, Tally>
  @id("aa0004") table seen: Map<String, Int64>
}
'''

V5 = V1.replace("store.put(S.counts, name, total);", "store.put(S.counts, name, total * 2);")   # та же схема, другая запись

V6 = V1.replace('  @id("aa0007") total: Int64,\n}', '  @id("aa0007") total: Int64,\n  @id("aa000n") by: Int64,\n}') \
       .replace("emit Bumped { name: name, total: total };", "emit Bumped { name: name, total: total, by: by };")

# эволюция типа под прежним именем (HST-04, HST-14): строение — часть схемы, миграция выбирается по строению
W1 = HEAD + '''
@id("ab0001")
pub type Tally = record {
  @id("ab0002") total: Int64,
}

@id("aa0002")
pub store S {
  @id("aa0003") table counts: Map<String, Tally>
  @id("aa0004") table seen: Map<String, Int64>
}

@id("aa000c")
pub query get(name: String) -> Option<Tally>
  uses { reads S.counts }
{
  store.get(S.counts, name)
}
'''

W2 = HEAD + '''
@id("ab0003")
pub type TallyV1 = record {
  @id("ab0004") total: Int64,
}

@id("ab0001")
pub type Tally = record {
  @id("ab0002") total: Int64,
  @id("ab0005") bumps: Int64,
}

@id("aa000k")
pub type MigErr = enum {
  @id("aa000m") Negative,
}

@id("aa0002")
pub store S {
  @id("aa0003") table counts: Map<String, Tally>
  @id("aa0004") table seen: Map<String, Int64>
}

@id("aa000c")
pub query get(name: String) -> Option<Tally>
  uses { reads S.counts }
{
  store.get(S.counts, name)
}

@id("ab0006")
migration grow on S.counts(old: TallyV1) -> Result<Tally, MigErr> {
  Ok(Tally { total: old.total, bumps: 1 })
}
'''

W3 = W2.replace("Tally", "Count").replace("CountV1", "TallyV1").replace(
    '''
@id("ab0006")
migration grow on S.counts(old: TallyV1) -> Result<Count, MigErr> {
  Ok(Count { total: old.total, bumps: 1 })
}
''', "")

# Переименование ключа не меняет его строения (HST-04/14), но меняет CANON-11.
KEY_V1 = '''@id("aa0001")
module app
use std.store

@id("ac0001")
pub type OldKey = opaque String

@id("aa0002")
pub store S {
  @id("aa0003") table items: Map<OldKey, Int64>
}

@id("aa000c")
pub query get(k: String) -> Option<Int64> uses { reads S.items } {
  store.get(S.items, OldKey(k))
}

@id("aa000b")
pub command put(k: String, n: Int64) -> Result<(), String> uses { writes S.items } {
  store.put(S.items, OldKey(k), n);
  Ok(())
}

@id("aa000e")
pub command remove(k: String) -> Result<(), String> uses { writes S.items } {
  store.remove(S.items, OldKey(k));
  Ok(())
}
'''
KEY_V2 = KEY_V1.replace("OldKey", "NewKey")
NESTED_KEY_V1 = KEY_V1.replace("Map<OldKey, Int64>", "Map<Envelope, Int64>").replace(
    "OldKey(k)", "Envelope { part: Some(OldKey(k)) }") + '''
@id("ac0002")
pub type Envelope = record {
  @id("ac0003") part: Option<OldKey>,
}
'''
NESTED_KEY_V2 = NESTED_KEY_V1.replace("OldKey", "NewKey")
KEY_VALUE_V2 = NESTED_KEY_V2.replace("Map<Envelope, Int64>", "Map<Envelope, Tally>").replace(
    "Option<Int64>", "Option<Tally>").replace(
    ", n);", ", Tally { total: n, bumps: 1 });") + TALLY + '''
@id("aa000j")
migration to_tally on S.items(old: Int64) -> Result<Tally, MigErr> {
  if old < 0 {
    Err(MigErr.Negative)
  } else {
    Ok(Tally { total: old, bumps: 1 })
  }
}
'''

# ---------------------------------------------------------------------------- значения CANON-11
COUNTS, SEEN = "app.S.counts", "app.S.seen"
RES = "Result<Int64,app.BumpError>"
NS = "app"
K1, K2, K3 = "key-000000000001", "key-000000000002", "key-000000000003"
MAX = 9223372036854775807


def s(v):
    return {"type": "String", "value": v}


def i(v):
    return {"type": "Int64", "value": str(v)}


def ok(v):
    return {"type": RES, "tag": "Ok", "payload": i(v)}


def err(tag):
    return {"type": RES, "tag": "Err", "payload": {"type": "app.BumpError", "tag": tag}}


def some(v, t="Int64"):
    return {"type": f"Option<{t}>", "tag": "Some", "payload": v}


def none(t="Int64"):
    return {"type": f"Option<{t}>", "tag": "None"}


def tally(total, bumps):
    return {"type": "app.Tally", "fields": {"total": i(total), "bumps": i(bumps)}}


def bumped(name, total):
    return {"type": "app.Bumped", "fields": {"name": s(name), "total": i(total)}}


def span(src: str, frag: str) -> list:
    b = src.encode("utf-8")
    k = b.index(frag.encode("utf-8"))
    return [k, k + len(frag.encode("utf-8"))]


SITE_ADD = {"file": "app.bag", "span": span(V1, "n + by")}
SITE_DIV = {"file": "app.bag", "span": span(V1, "100 / (ev.total - 13)")}

# ---------------------------------------------------------------------------- шаги и ожидания
def bump(name, by, key=K1, **kw):
    return dict({"op": "command", "entry": "app.bump", "args": [s(name), i(by)], "namespace": NS, "key": key}, **kw)


def get(name, **kw):
    return dict({"op": "query", "entry": "app.get", "args": [s(name)]}, **kw)


def status(key=K1):
    return {"op": "status", "namespace": NS, "key": key}


def seed(table, rows, **kw):
    return dict({"op": "seed", "table": table, "rows": rows}, **kw)


def committed(value, sv, replayed=False):
    return {"value": value, "outcome": "COMMITTED", "final": True, "replayed": replayed, "state_version": sv}


def aborted(value, sv, replayed=False):
    return {"value": value, "outcome": "ABORTED", "final": True, "replayed": replayed, "state_version": sv}


def refused(code, **data):
    return {"outcome": "REFUSED", "code": code, **({"data": data} if data else {})}


def result(value, receipt, sv):
    return {"value": value, "outcome": "RESULT", "receipt_outcome": receipt, "state_version": sv}


def absent(sv):
    return {"outcome": "ABSENT_AT_READ", "state_version": sv}


def returned(value):
    return {"outcome": "RETURNED", "value": value}


def delivered(*ds):
    return {"outcome": "DELIVERED", "deliveries": list(ds)}


def d_ok(seq, sv, replayed=False):
    r = {"handler": "app.remember", "seq": seq, "outcome": "COMMITTED", "replayed": replayed}
    if not replayed:
        r["state_version"] = sv
    return r


def state(sv, counts=(), seen=(), outbox=(), inbox=(), epoch=0, counts_t=None, handler=True):
    """Состояние HST-17. pending — события outbox без записи inbox по подпискам активной привязки (HST-11):
    у v1 есть обработчик app.remember, у v2 подписок нет (handler=False)."""
    enc = counts_t or (lambda v: i(v))
    pending = [{"handler": "app.remember", "seq": n} for n in range(1, len(outbox) + 1) if n not in inbox] if handler else []
    return {"state_version": sv, "epoch": epoch,
            "tables": {COUNTS: [[s(k), enc(v)] for k, v in sorted(counts)],
                       SEEN: [[s(k), i(v)] for k, v in sorted(seen)]},
            "outbox": [{"seq": n, "event": "app.Bumped", "payload": bumped(k, v)} for n, (k, v) in enumerate(outbox, 1)],
            "inbox": [{"handler": "app.remember", "seq": n, "outcome": "COMMITTED"} for n in inbox],
            "pending": pending}


CASES = []


def case(area, name, refs, steps, value, st=None, files=None, note=None, state_program=None):
    run = {"steps": steps}
    if state_program is not None:
        run["state_program"] = state_program
    exp = {"phase": area, "outcome": "COMPLETED", "value": value}
    if st is not None:
        exp["state"] = st
    CASES.append((area, name, refs, files or {"app.bag": V1}, run, exp, note))


# ============================================================ store: команда, квитанция, запрос
case("store", "commit-retry-01", [H3, OUT3],
     [bump("a", 5), bump("a", 5), get("a"), status()],
     [committed(ok(5), 1), committed(ok(5), 1, replayed=True), returned(some(i(5))), result(ok(5), "COMMITTED", 1)],
     state(1, counts=[("a", 5)], outbox=[("a", 5)]),
     note="повтор с тем же ключом возвращает квитанцию и ничего не меняет (HST-05, HST-06)")

case("store", "idempotency-conflict-01", [H3],
     [bump("a", 5), bump("a", 6), get("a"), dict(status(), entry="app.bump", args=[s("a"), i(6)]),
      dict(status(), entry="app.bump", args=[s("a"), i(5)])],
     [committed(ok(5), 1), refused("IDEMPOTENCY_CONFLICT", namespace=NS, key=K1), returned(some(i(5))),
      refused("IDEMPOTENCY_CONFLICT", namespace=NS, key=K1), result(ok(5), "COMMITTED", 1)],
     state(1, counts=[("a", 5)], outbox=[("a", 5)]))

case("store", "err-final-receipt-01", [H3, H1, OUT3],
     [bump("a", 0), bump("a", 0), status(), bump("b", 150, key=K2), get("b"), status(K2)],
     [aborted(err("NonPositive"), 1), aborted(err("NonPositive"), 1, replayed=True), result(err("NonPositive"), "ABORTED", 1),
      aborted(err("TooLarge"), 2), returned(none()), result(err("TooLarge"), "ABORTED", 2)],
     state(2),
     note="Err — окончательный исход с квитанцией; запись тела до Err откатана, событий нет; StateVersion растёт (HST-03)")

case("store", "fault-no-receipt-01", [H3, OUT3],
     [seed(COUNTS, [[s("a"), i(1)]]), bump("a", MAX), status(), bump("a", 1)],
     [{"outcome": "COMMITTED", "rows": 1, "state_version": 1},
      {"outcome": "ABORTED", "final": False, "termination": "FAULT", "code": "ARITHMETIC_OVERFLOW", "site": SITE_ADD,
       "replayed": False},
      absent(1), committed(ok(2), 2)],
     state(2, counts=[("a", 2)], outbox=[("a", 2)]),
     note="FAULT откатывает всё и не резервирует ключ: тот же ключ с другим запросом исполняется (HST-06)")

case("store", "receipt-before-stale-guard-01", [H3],
     [bump("a", 1, expected_state_version=0), bump("a", 1, expected_state_version=0), bump("a", 1),
      bump("a", 2, key=K2, expected_state_version=0), status(K2)],
     [committed(ok(1), 1), committed(ok(1), 1, replayed=True), committed(ok(1), 1, replayed=True),
      refused("STALE_STATE", expected=0, actual=1), absent(1)],
     note="квитанция ищется до guard версии (D44); guard не входит в дайджест запроса; отказ guard'а ключ не резервирует")

case("store", "admission-refusals-01", [H3],
     [{"op": "command", "entry": "app.nope", "args": [], "namespace": NS, "key": K1},
      {"op": "command", "entry": "app.hidden", "args": [s("a")], "namespace": NS, "key": K1},
      {"op": "command", "entry": "app.get", "args": [s("a")], "namespace": NS, "key": K1},
      {"op": "command", "entry": "app.bump", "args": [s("a")], "namespace": NS, "key": K1},
      {"op": "command", "entry": "app.bump", "args": [i(1), i(1)], "namespace": NS, "key": K1},
      {"op": "command", "entry": "app.bump", "args": [s("a"), {"type": "Int64", "value": "01"}], "namespace": NS, "key": K1},
      bump("a", 1, key="short"), status()],
     [refused("UNKNOWN_ENTRYPOINT", name="app.nope"), refused("ENTRYPOINT_NOT_EXPORTED", name="app.hidden"),
      refused("UNKNOWN_ENTRYPOINT", name="app.get"), refused("REQUEST_INVALID"), refused("REQUEST_INVALID"),
      refused("REQUEST_INVALID"), refused("REQUEST_INVALID"), absent(0)],
     note="отказы до допуска не пишут ничего; detail — пояснение реализации, в наблюдение L2 не входит")

case("store", "authority-01", [H3, EFF],
     [bump("a", 1, caller="bot", policy={"callers": {"ui": ["app.bump"]}}),
      bump("a", 1, caller="ui", policy={"callers": {"ui": ["app.bump"]}}),
      bump("a", 1, key=K2, caller="ui", policy={"callers": {"ui": ["*"]}, "revoke": ["emits app.Bumped"]}),
      status(K2), get("a")],
     [refused("ACCESS_DENIED", entry="app.bump", caller="bot"), committed(ok(1), 1),
      {"outcome": "ABORTED", "final": False, "termination": "IMPLEMENTATION_STOP", "code": "ACCESS_DENIED", "replayed": False},
      absent(1), returned(some(i(1)))],
     state(1, counts=[("a", 1)], outbox=[("a", 1)]),
     note="политика выбирает точки входа; отозванный атом останавливает Perform, запись до него откатана (HST-08, HST-09)")

case("store", "query-snapshot-01", [H4],
     [seed(COUNTS, [[s("b"), i(4)], [s("a"), i(3)]]), get("b"), get("z"),
      {"op": "query", "entry": "app.bump", "args": [s("a"), i(1)]}],
     [{"outcome": "COMMITTED", "rows": 2, "state_version": 1}, returned(some(i(4))), returned(none()),
      refused("UNKNOWN_ENTRYPOINT", name="app.bump")],
     state(1, counts=[("a", 3), ("b", 4)]),
     note="запрос не меняет StateVersion; строки в состоянии — в порядке Key, а не вставки (HST-02)")

case("store", "replay-01", [H6],
     [bump("a", 2), {"op": "deliver"}, {"op": "replay", "ref": f"{NS}:{K1}"},
      {"op": "replay", "ref": "app.remember:1"}, {"op": "replay", "ref": f"{NS}:{K2}"}],
     [committed(ok(2), 1), delivered(d_ok(1, 2)),
      {"outcome": "REPLAY_MATCH", "ref": f"{NS}:{K1}", "operations": 3},
      {"outcome": "REPLAY_MATCH", "ref": "app.remember:1", "operations": 1},
      {"outcome": "ABSENT_AT_READ", "ref": f"{NS}:{K2}"}])

case("store", "replay-divergence-01", [H6],
     [bump("a", 2), dict({"op": "replay", "ref": f"{NS}:{K1}"}, program="v5"), {"op": "replay", "ref": f"{NS}:{K1}"}],
     [committed(ok(2), 1), {"outcome": "REPLAY_DIVERGENCE", "ref": f"{NS}:{K1}"},
      {"outcome": "REPLAY_MATCH", "ref": f"{NS}:{K1}", "operations": 3}],
     state(1, counts=[("a", 2)], outbox=[("a", 2)]), files={"app.bag": V1, "v5/app.bag": V5}, state_program="",
     note="программа той же схемы пишет другое значение: replay сверяет аргументы записи и видит расхождение (HST-13)")

for point, done in (("before_begin", False), ("before_commit", False), ("after_commit", True)):
    case("store", f"crash-{point.replace('_', '-')}-01", [H8, H3],
         [bump("a", 2, crash_at=point), status(), bump("a", 2), status()],
         [{"outcome": "CRASHED", "at": point}, result(ok(2), "COMMITTED", 1) if done else absent(0),
          committed(ok(2), 1, replayed=done), result(ok(2), "COMMITTED", 1)],
         state(1, counts=[("a", 2)], outbox=[("a", 2)]),
         note="сбой как kill -9; восстановление — по квитанции; эффект ровно один (HST-16)")

# ============================================================ events
case("events", "deliver-once-01", [H5],
     [bump("a", 2), bump("b", 3, key=K2), {"op": "deliver"}, {"op": "deliver"}, {"op": "deliver", "seq": 1}],
     [committed(ok(2), 1), committed(ok(3), 2), delivered(d_ok(1, 3), d_ok(2, 4)), delivered(),
      delivered(d_ok(1, None, replayed=True))],
     state(4, counts=[("a", 2), ("b", 3)], seen=[("a", 2), ("b", 3)], outbox=[("a", 2), ("b", 3)], inbox=[1, 2]),
     note="запись inbox — квитанция обработки; повтор доставки не исполняет обработчик (O07, C13)")

case("events", "fault-keeps-order-01", [H5],
     [bump("a", 13), bump("b", 1, key=K2), {"op": "deliver"}, {"op": "deliver", "handler": "app.remember", "seq": 2}],
     [committed(ok(13), 1), committed(ok(1), 2),
      delivered({"handler": "app.remember", "seq": 1, "outcome": "ABORTED", "termination": "FAULT",
                 "code": "DIVISION_BY_ZERO", "site": SITE_DIV}),
      delivered(d_ok(2, 3))],
     state(3, counts=[("a", 13), ("b", 1)], seen=[("b", 1)], outbox=[("a", 13), ("b", 1)], inbox=[2]),
     note="FAULT обработчика оставляет событие недоставленным и останавливает очередь обработчика; явная доставка seq 2 допустима")

case("events", "crash-handler-01", [H5, H8],
     [bump("a", 2), {"op": "deliver", "crash_at": "before_commit"}, {"op": "deliver"}, {"op": "deliver"}],
     [committed(ok(2), 1), {"outcome": "CRASHED", "at": "before_commit"}, delivered(d_ok(1, 2)), delivered()],
     state(2, counts=[("a", 2)], seen=[("a", 2)], outbox=[("a", 2)], inbox=[1]))

# ============================================================ migrate
V12 = {"app.bag": V1, "v2/app.bag": V2}
PLAN = [{"table": COUNTS, "id": "aa0003", "action": "migrate", "migration": "app.to_tally", "from": "Int64", "to": "app.Tally"},
        {"table": SEEN, "id": "aa0004", "action": "keep"}]
EVENTS = [{"event": "app.Bumped", "id": "aa0005", "action": "keep"}]
SEED2 = seed(COUNTS, [[s("b"), i(7)], [s("a"), i(5)]])
SEEDED = {"outcome": "COMMITTED", "rows": 2, "state_version": 1}


def v2(step):
    return dict(step, program="v2")


case("migrate", "apply-epoch-01", [H7, H2],
     [SEED2, v2(get("a")), v2({"op": "migrate", "action": "plan"}), v2({"op": "migrate"}), v2(get("a")),
      v2({"op": "migrate"}), get("a")],
     [SEEDED, refused("SCHEMA_BINDING_MISMATCH"),
      {"epoch": 0, "state_version": 1, "tables": PLAN, "events": EVENTS, "outcome": "PLANNED"},
      {"outcome": "APPLIED", "epoch": 1, "state_version": 2, "rows": 2, "tables": PLAN, "events": EVENTS},
      returned(some(tally(5, 1), "app.Tally")),
      {"epoch": 1, "state_version": 2, "outcome": "UP_TO_DATE", "tables": [], "events": []},
      refused("SCHEMA_BINDING_MISMATCH")],
     state(2, counts=[("a", 5), ("b", 7)], epoch=1, counts_t=lambda v: tally(v, 1), handler=False), files=V12, state_program="v2",
     note="после переключения прежняя программа отклоняется; повтор apply — UP_TO_DATE (HST-14, HST-15)")

def tally1(total):
    return {"type": "app.Tally", "fields": {"total": i(total)}}


SHAPE_PLAN = [{"table": COUNTS, "id": "aa0003", "action": "migrate", "migration": "app.grow", "from": "app.Tally",
               "to": "app.Tally"}, {"table": SEEN, "id": "aa0004", "action": "keep"}]
KEEP_PLAN = [{"table": COUNTS, "id": "aa0003", "action": "keep"}, {"table": SEEN, "id": "aa0004", "action": "keep"}]
case("migrate", "same-name-shape-01", [H2, H7],
     [seed(COUNTS, [[s("a"), tally1(5)]]), v2(get("a")), v2({"op": "migrate", "action": "plan"}), v2({"op": "migrate"}),
      v2(get("a")), dict(get("a"), program="v3"), dict({"op": "migrate", "action": "plan"}, program="v3"),
      dict({"op": "migrate"}, program="v3"), dict(get("a"), program="v3")],
     [{"outcome": "COMMITTED", "rows": 1, "state_version": 1}, refused("SCHEMA_BINDING_MISMATCH"),
      {"epoch": 0, "state_version": 1, "tables": SHAPE_PLAN, "events": EVENTS, "outcome": "PLANNED"},
      {"outcome": "APPLIED", "epoch": 1, "state_version": 2, "rows": 1, "tables": SHAPE_PLAN, "events": EVENTS},
      returned(some(tally(5, 1), "app.Tally")), refused("SCHEMA_BINDING_MISMATCH"),
      {"epoch": 1, "state_version": 2, "tables": KEEP_PLAN, "events": EVENTS, "outcome": "PLANNED"},
      {"outcome": "APPLIED", "epoch": 2, "state_version": 3, "rows": 0, "tables": KEEP_PLAN, "events": EVENTS},
      returned(some({"type": "app.Count", "fields": {"total": i(5), "bumps": i(1)}}, "app.Count"))],
     state(3, counts=[("a", 5)], epoch=2, counts_t=lambda v: {"type": "app.Count", "fields": {"total": i(v), "bumps": i(1)}},
           handler=False),
     files={"app.bag": W1, "v2/app.bag": W2, "v3/app.bag": W3}, state_program="v3",
     note="поле добавлено в тип под прежним именем: привязка видит смену строения, миграция выбрана по строению "
          "(TallyV1 = прежняя Tally); переименование типа без смены строения — keep без переписывания строк, "
          "строки читаются по строению")

case("migrate", "backlog-01", [H7],
     [bump("a", 2), v2({"op": "migrate"}), {"op": "deliver"}, v2({"op": "migrate"})],
     [committed(ok(2), 1), refused("MIGRATION_BACKLOG", pending=[{"handler": "app.remember", "seq": 1}], count=1),
      delivered(d_ok(1, 2)), {"outcome": "APPLIED", "epoch": 1, "state_version": 3, "rows": 1, "tables": PLAN, "events": EVENTS}],
     state(3, counts=[("a", 2)], seen=[("a", 2)], outbox=[("a", 2)], inbox=[1], epoch=1, counts_t=lambda v: tally(v, 1), handler=False),
     files=V12, state_program="v2")

case("migrate", "row-failure-01", [H7],
     [seed(COUNTS, [[s("c"), i(-2)], [s("a"), i(5)], [s("b"), i(-1)]]), v2({"op": "migrate"}), bump("a", 1)],
     [{"outcome": "COMMITTED", "rows": 3, "state_version": 1},
      refused("MIGRATION_FAILED", table=COUNTS, key=s("b"), error={"type": "app.MigErr", "tag": "Negative"}),
      committed(ok(6), 2)],
     state(2, counts=[("a", 6), ("b", -1), ("c", -2)], outbox=[("a", 6)]),
     files=V12, state_program="",
     note="строки идут в порядке Key, а не вставки (c, a, b): первая ошибка — на ключе b; данные не тронуты, писатели снова работают")

case("migrate", "plan-invalid-01", [H7],
     [seed(COUNTS, [[s("a"), i(5)]]), dict({"op": "migrate", "action": "plan"}, program="v3"),
      dict({"op": "migrate", "action": "plan"}, program="v4")],
     [{"outcome": "COMMITTED", "rows": 1, "state_version": 1},
      refused("MIGRATION_PLAN_INVALID", problems=[
          {"table": COUNTS, "id": "aa0003", "reason": "KEY_TYPE_CHANGED", "from": "String", "to": "Int64"},
          {"table": SEEN, "id": "aa0004", "reason": "TABLE_REMOVED"}]),
      refused("MIGRATION_PLAN_INVALID", problems=[
          {"table": COUNTS, "id": "aa0003", "reason": "MIGRATION_MISSING", "from": "Int64", "to": "app.Tally"}])],
     files={"app.bag": V1, "v3/app.bag": V3, "v4/app.bag": V4}, state_program="")

case("migrate", "crash-prepare-01", [H7, H8],
     [SEED2, v2({"op": "migrate", "crash_at": "migration_prepare"}), bump("a", 1), {"op": "deliver"},
      v2({"op": "migrate"})],
     [SEEDED, {"outcome": "CRASHED", "at": "migration_prepare"}, refused("MIGRATION_IN_PROGRESS"),
      delivered(refused("MIGRATION_IN_PROGRESS")),
      {"outcome": "APPLIED", "epoch": 1, "state_version": 2, "rows": 2, "tables": PLAN, "events": EVENTS}],
     state(2, counts=[("a", 5), ("b", 7)], epoch=1, counts_t=lambda v: tally(v, 1), handler=False), files=V12, state_program="v2",
     note="замок переживает сбой: писатели стоят; повтор apply той же миграции завершает её")

case("migrate", "crash-swap-01", [H7, H8],
     [SEED2, v2({"op": "migrate", "crash_at": "before_swap_commit"}), v2({"op": "migrate"}),
      v2({"op": "migrate", "crash_at": "after_swap"})],
     [SEEDED, {"outcome": "CRASHED", "at": "before_swap_commit"},
      {"outcome": "APPLIED", "epoch": 1, "state_version": 2, "rows": 2, "tables": PLAN, "events": EVENTS},
      {"epoch": 1, "state_version": 2, "outcome": "UP_TO_DATE", "tables": [], "events": []}],
     state(2, counts=[("a", 5), ("b", 7)], epoch=1, counts_t=lambda v: tally(v, 1), handler=False), files=V12, state_program="v2")

case("migrate", "event-change-01", [H7, H2],
     [bump("a", 2), {"op": "deliver"}, dict(bump("a", 1, key=K2), program="v6"), dict({"op": "migrate"}, program="v6"),
      dict(bump("a", 1, key=K2), program="v6"), dict({"op": "deliver"}, program="v6")],
     [committed(ok(2), 1), delivered(d_ok(1, 2)), refused("SCHEMA_BINDING_MISMATCH"),
      {"outcome": "APPLIED", "epoch": 1, "state_version": 3, "rows": 0,
       "tables": [{"table": COUNTS, "id": "aa0003", "action": "keep"}, {"table": SEEN, "id": "aa0004", "action": "keep"}],
       "events": [{"event": "app.Bumped", "id": "aa0005", "action": "change"}]},
      committed(ok(3), 4), delivered(d_ok(2, 5))],
     files={"app.bag": V1, "v6/app.bag": V6}, state_program="v6",
     note="тип события входит в привязку: новое поле требует миграции; дренаж до неё гарантирует, что старых недоставленных нет")

case("migrate", "foreign-lock-01", [H7],
     [seed(COUNTS, [[s("a"), i(5)]]), {"op": "lock"}, bump("a", 1), v2({"op": "migrate"}),
      {"op": "migrate", "action": "abort"}, bump("a", 1)],
     [{"outcome": "COMMITTED", "rows": 1, "state_version": 1}, {"outcome": "LOCKED"}, refused("MIGRATION_IN_PROGRESS"),
      refused("MIGRATION_IN_PROGRESS"), {"outcome": "ABORTED", "dropped": []}, committed(ok(6), 2)],
     files=V12, state_program="")

# Нормативные ожидания r39: исходы вычислены до запуска реализации по HST-04/14/15/16.
# После удаления a остаётся только b: старый байтовый ключ a не может спрятаться за успешным put.
ITEMS = "app.S.items"
KEY_KEEP = [{"table": ITEMS, "id": "aa0003", "action": "keep"}]
KEY_MIGRATE = [{"table": ITEMS, "id": "aa0003", "action": "migrate", "migration": "app.to_tally",
                "from": "Int64", "to": "app.Tally"}]
KEY_OK = {"type": "Result<Unit,String>", "tag": "Ok", "payload": {"type": "Unit"}}


def renamed_key(k, new=False, nested=False):
    v = {"type": "app.NewKey" if new else "app.OldKey", "value": s(k)}
    return {"type": "app.Envelope", "fields": {"part": some(v, v["type"])}} if nested else v


def key_state(sv, rows, epoch=0, new=False, nested=False, migrated=False):
    return {"state_version": sv, "epoch": epoch,
            "tables": {ITEMS: [[renamed_key(k, new, nested), tally(v, 1) if migrated else i(v)] for k, v in rows]},
            "outbox": [], "inbox": [], "pending": []}


def key_put(k, n, **kw):
    return dict({"op": "command", "entry": "app.put", "args": [s(k), i(n)], "namespace": NS, "key": K1}, **kw)


def key_remove(k, **kw):
    return dict({"op": "command", "entry": "app.remove", "args": [s(k)], "namespace": NS, "key": K2}, **kw)


for name, old_src, new_src, nested, migrated in (
        ("key-rename-01", KEY_V1, KEY_V2, False, False),
        ("nested-key-rename-01", NESTED_KEY_V1, NESTED_KEY_V2, True, False),
        ("key-rename-value-01", NESTED_KEY_V1, KEY_VALUE_V2, True, True)):
    tables = KEY_MIGRATE if migrated else KEY_KEEP
    val = (lambda n: tally(n, 1)) if migrated else i
    typ = "app.Tally" if migrated else "Int64"
    case("migrate", name, [H2, H7, H3, H4],
         [seed(ITEMS, [[renamed_key("b", nested=nested), i(9)], [renamed_key("a", nested=nested), i(7)]]),
          v2(get("a")), v2({"op": "migrate", "action": "plan"}), v2({"op": "migrate"}), v2(get("a")),
          v2(key_put("a", 8)), v2(get("a")), v2(key_remove("a")), v2(get("a")), v2(get("b")),
          v2({"op": "migrate"}), v2(get("b"))],
         [{"outcome": "COMMITTED", "rows": 2, "state_version": 1}, refused("SCHEMA_BINDING_MISMATCH"),
          {"outcome": "PLANNED", "epoch": 0, "state_version": 1, "tables": tables, "events": []},
          {"outcome": "APPLIED", "epoch": 1, "state_version": 2, "rows": 2 if migrated else 0,
           "tables": tables, "events": []}, returned(some(val(7), typ)), committed(KEY_OK, 3),
          returned(some(val(8), typ)), committed(KEY_OK, 4), returned(none(typ)), returned(some(val(9), typ)),
          {"outcome": "UP_TO_DATE", "epoch": 1, "state_version": 4, "tables": [], "events": []},
          returned(some(val(9), typ))],
         key_state(4, [("b", 9)], epoch=1, new=True, nested=nested, migrated=migrated),
         files={"app.bag": old_src, "v2/app.bag": new_src}, state_program="v2",
         note="переименование ключа сохраняет get/put/remove и единственность логического ключа; "
              "при неизменном внешнем Envelope учитывается вложенное имя; явная миграция значения не копирует старые байты ключа")

case("migrate", "key-rename-rollback-01", [H2, H7],
     [seed(ITEMS, [[renamed_key("b", nested=True), i(-1)], [renamed_key("a", nested=True), i(7)]]),
      v2({"op": "migrate"}), get("a"), get("b"), key_put("a", 8), get("a"), v2(get("a"))],
     [{"outcome": "COMMITTED", "rows": 2, "state_version": 1},
      refused("MIGRATION_FAILED", table=ITEMS, key=renamed_key("b", nested=True),
              error={"type": "app.MigErr", "tag": "Negative"}),
      returned(some(i(7))), returned(some(i(-1))), committed(KEY_OK, 2), returned(some(i(8))),
      refused("SCHEMA_BINDING_MISMATCH")],
     key_state(2, [("a", 8), ("b", -1)], nested=True),
     files={"app.bag": NESTED_KEY_V1, "v2/app.bag": KEY_VALUE_V2}, state_program="",
     note="ошибка значения b после успешной строки a откатывает также перекодировку ключей; прежняя программа снова пишет")

for point, done in (("before_swap_commit", False), ("after_swap", True)):
    case("migrate", f"key-rename-crash-{point.replace('_', '-')}-01", [H2, H7, H8],
         [seed(ITEMS, [[renamed_key("a", nested=True), i(7)]]),
          v2({"op": "migrate", "crash_at": point}), get("a"), v2(get("a")),
          v2({"op": "migrate"}), v2(get("a")), v2(key_put("a", 8)), v2(key_remove("a")), v2(get("a"))],
         [{"outcome": "COMMITTED", "rows": 1, "state_version": 1}, {"outcome": "CRASHED", "at": point},
          refused("SCHEMA_BINDING_MISMATCH") if done else returned(some(i(7))),
          returned(some(i(7))) if done else refused("SCHEMA_BINDING_MISMATCH"),
          {"outcome": "UP_TO_DATE", "epoch": 1, "state_version": 2, "tables": [], "events": []} if done else
          {"outcome": "APPLIED", "epoch": 1, "state_version": 2, "rows": 0, "tables": KEY_KEEP, "events": []},
          returned(some(i(7))), committed(KEY_OK, 3), committed(KEY_OK, 4), returned(none())],
         key_state(4, [], epoch=1, new=True, nested=True),
         files={"app.bag": NESTED_KEY_V1, "v2/app.bag": NESTED_KEY_V2}, state_program="v2",
         note="сбой до фиксации оставляет прежние ключи и привязку, после фиксации — новые; повтор не создаёт дублей")


def main():
    for area in AREAS:
        shutil.rmtree(OUT / area, ignore_errors=True)
    for area, name, refs, files, run, exp, note in CASES:
        d = OUT / area / name
        d.mkdir(parents=True)
        for rel, src in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(src, encoding="utf-8")
        c = {"id": f"{area}/{name}", "spec": refs, "origin": "independent", "levels": ["L2"],
             "files": sorted(files), "run": run, "expect": exp}
        if note:
            c["note"] = note
        (d / "case.json").write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(CASES)} случаев: " + ", ".join(f"{a} {sum(1 for c in CASES if c[0] == a)}" for a in AREAS))


if __name__ == "__main__":
    main()
