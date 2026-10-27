#!/usr/bin/env python3
"""Автор случаев изменения и протокола (Ф6): области edit, accept, protocol.

Ожидания выведены вручную из правил spec/protocol/agent-protocol.md (CHG-01…20); эталон для них не запускается.
Программа-приветствие app.bag: правило Polite.nonempty, его реализация greet, тест greet_nonempty, функции shout
и helper. Сценарии фикстуры authorship (models/r07-core/data/authorship-fixtures.json, origin = model:…#Cnn): C04 и
C06 переведены на пример examples/authorship, C07 (две работы от одной базы) — на app.bag. Случаи с суффиксом
ревью m6 закрепляют найденные ложные приёмки (registry/reviews/m6.md). Повторный запуск перезаписывает эти области.

  python3 conformance/gen/make_change_cases.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "conformance" / "cases"
AREAS = ("edit", "accept", "protocol")
APP = ROOT / "examples" / "authorship"
FIX = "model:models/r07-core/data/authorship-fixtures.json"
_spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)


def anchor(h):
    return "spec/protocol/agent-protocol.md#" + _conf.slug(h)


S2, S3, S4, S5, S6, S7, S8, S9 = (anchor(h) for h in (
    "2. Снимок", "3. SourceEdit и идентичность", "4. ChangeContract и политика", "5. Свидетельства", "6. WorkState",
    "7. Операции протокола", "8. Приёмка", "9. Перенос на новый head"))

Q = '''@id("cq0001")
module app

use std.test

@id("cq0002")
pub entity Greeting {
  purpose "Приветствие пользователю"
  terms ["привет"]
  not_about ["прощание"]
}

@id("cq0003")
pub contract Polite about Greeting {
  @id("cq0004") rule nonempty "приветствие не пустое"
}

@id("cq0005")
pub fn greet(name: String) -> String
  implements Polite.nonempty
{
  "Привет, " ++ name
}

@id("cq0006")
pub fn shout(name: String) -> String {
  greet(name) ++ "!"
}

@id("cq0007")
fn helper(n: Int64) -> Int64 {
  n + 1
}

@id("cq0008")
test greet_nonempty
  checks Polite.nonempty
{
  test.expect("не пусто", greet("x") != "")
}
'''
QB = Q.encode("utf-8")
HELPER = '''@id("cq0007")
fn helper(n: Int64) -> Int64 {
  n + 1
}
'''
RULE, GREET, TEST = "app.Polite.nonempty", "app.greet", "app.greet_nonempty"
CASES = []


def case(area, name, refs, steps, value, files=None, origin="independent", note=None, policy=None, head_rev=None):
    run = {"change": {"principal": "agent", "steps": steps}}
    if policy is not None:
        run["change"]["policy"] = policy
    exp = {"phase": area, "outcome": "COMPLETED", "value": value}
    if head_rev is not None:
        exp["state"] = {"head_revision": head_rev}
    CASES.append((area, name, refs, files or {"app.bag": Q}, run, exp, origin, note))


def key(tag):
    return (tag + "-" + "k" * 20)[:24]


def begin(tag="b", intent="изменение", n=1):
    return {"request": {"operation": "change_begin", "idempotency_key": key(tag + str(n)), "arguments": {"intent": intent}}}


def write(op, rev, tag, ch="$change", principal=None, **args):
    s = {"request": {"operation": op, "change_id": ch, "expected_work_revision": rev, "idempotency_key": key(tag),
                     "arguments": args}}
    if principal:
        s["principal"] = principal
    return s


def apply(rev, tag, files, ops=None, ch="$change", assign=None, principal=None):
    se = {"files": files}
    if ops is not None:
        se["identity_ops"] = ops
    if assign is not None:
        se["assign_ids"] = assign
    return write("apply", rev, tag, ch, principal, source_edit=se)


def resume(ch="$change", principal=None):
    s = {"request": {"operation": "work_resume", "change_id": ch, "arguments": {}}}
    if principal:
        s["principal"] = principal
    return s


def old(path, old_text, text):
    return {"path": path, "base_sha256": f"$sha:{path}", "edits": [{"old_text": old_text, "text": text}]}


def ok_begin():
    return {"status": "succeeded", "replayed": False, "work_revision": 1}


NO_ID = {"lineage": [], "removed": [], "added": [], "renamed": []}


def ok_apply(rev, touched, identity=None, draft=False, diags=()):
    return {"status": "succeeded", "replayed": False, "work_revision": rev, "touched": touched,
            "identity": identity or NO_ID, "draft": draft, "diagnostics": list(diags)}


def blocked(code, **data):
    out = {"status": "blocked", "replayed": False, "code": code}
    if data:
        out["data"] = data
    return out


def failed(code, **data):
    return dict(blocked(code, **data), status="failed")


def resumed(rev, blockers=(), obligations=(), clauses=(), ready=None, needs_rebase=False, contract_rev=1, status="open"):
    return {"status": "succeeded", "replayed": False, "work_revision": rev, "needs_rebase": needs_rebase,
            "ready_for_acceptance": (not blockers) if ready is None else ready, "contract_revision": contract_rev,
            "status_": status, "blockers": sorted(blockers), "obligations": sorted(obligations),
            "clauses": sorted(clauses)}


def verified(rev, evidence):
    return {"status": "succeeded", "replayed": False, "work_revision": rev, "evidence": sorted(evidence)}


def accepted(rev, obligations=(), replaced=(), replaced_tests=(), gaps=(), lineage=(), replayed=False):
    """Проекция записи приёмки: каждое обязательство вне excluded_with_basis — [вид, цель, источник, статус, основание];
    lineage — [операция, предшественники, преемники]."""
    return {"status": "succeeded", "replayed": replayed, "work_revision": rev,
            "obligations": sorted(list(o) for o in obligations), "replaced_clauses": list(replaced),
            "replaced_tests": [list(t) for t in replaced_tests], "coverage_gaps": [list(g) for g in gaps],
            "lineage": [list(x) for x in lineage]}


def contract(rev, crev, clauses=(), replaced=(), assumptions=(), allowed=None, replaced_tests=(), pins=()):
    return {"status": "succeeded", "replayed": False, "work_revision": rev, "contract_revision": crev,
            "clauses": list(clauses), "replaced": [list(r) for r in replaced], "assumptions": [list(a) for a in assumptions],
            "allowed": allowed, "replaced_tests": list(replaced_tests), "policy_pins": list(pins)}


def pos(text, frag):
    b = text.encode("utf-8")
    i = b.index(frag.encode("utf-8"))
    return i, i + len(frag.encode("utf-8"))


GREET_OPEN = [[RULE, GREET, "implements", "open", "evidence-missing-or-stale"],
              [RULE, TEST, "checks", "open", "evidence-missing-or-stale"]]
GREET_OK = [[RULE, GREET, "implements", "supported", "tests"], [RULE, TEST, "checks", "supported", "tests"]]
GREET_ACC = [["checks", "cq0004", "cq0008", "supported", "tests"], ["implements", "cq0004", "cq0005", "supported", "tests"]]
GREET_EDIT = old("app.bag", '"Привет, " ++ name', '"Здравствуй, " ++ name')
GREET_EDIT_LIT = dict(GREET_EDIT, base_sha256=hashlib.sha256(QB).hexdigest())   # повтор — те же байты запроса
T_GREET = pos(Q.replace('"Привет, " ++ name', '"Здравствуй, " ++ name'), '"Здравствуй, " ++ name')

# ============================================================ edit
s, e = pos(Q, '"Привет, "')
case("edit", "replace-span-01", [S3], [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag",
                                                                  "edits": [{"start": s, "end": e, "text": '"Здравствуй, "'}]}])],
     [ok_begin(), ok_apply(2, {"app.bag": [[s, s + len('"Здравствуй, "'.encode())]]})],
     note="замена байтового диапазона; затронутый диапазон — в новом тексте")

case("edit", "old-text-ambiguous-01", [S3], [begin(), apply(1, "a1", [old("app.bag", "name", "who")]),
                                             apply(1, "a2", [GREET_EDIT])],
     [ok_begin(), blocked("AMBIGUOUS_EDIT", path="app.bag", edit=0, occurrences=4), ok_apply(2, {"app.bag": [list(T_GREET)]})],
     note="«name» встречается 4 раза; отказ не меняет ревизию работы — следующая правка с той же ожидаемой ревизией")

case("edit", "stale-source-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "0" * 64, "edits": [{"old_text": "n + 1", "text": "n + 2"}]}]),
      apply(1, "a2", [{"path": "nope.bag", "base_sha256": "0" * 64, "edits": [{"old_text": "x", "text": "y"}]}])],
     [ok_begin(), blocked("STALE_SOURCE", path="app.bag"), blocked("STALE_SOURCE", path="nope.bag")])

a, b = pos(Q, "n + 1")
case("edit", "overlap-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag",
                                "edits": [{"start": a, "end": b, "text": "n"}, {"start": a + 2, "end": b, "text": "+ 2"}]}]),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag",
                       "edits": [{"start": a, "end": a, "text": "("}, {"start": a, "end": a, "text": "["}]}])],
     [ok_begin(), blocked("OVERLAPPING_EDITS", path="app.bag", edits=[0, 1]),
      blocked("OVERLAPPING_EDITS", path="app.bag", edits=[0, 1])],
     note="пересечение и две вставки в одну точку — порядок неоднозначен")

p0 = QB.index("Привет".encode())
case("edit", "range-invalid-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag",
                                "edits": [{"start": p0 + 1, "end": p0 + 2, "text": "x"}]}]),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag",
                       "edits": [{"start": len(QB), "end": len(QB) + 1, "text": "x"}]}])],
     [ok_begin(), blocked("RANGE_INVALID", path="app.bag", edit=0, start=p0 + 1, end=p0 + 2, size=len(QB)),
      blocked("RANGE_INVALID", path="app.bag", edit=0, start=len(QB), end=len(QB) + 1, size=len(QB))],
     note="середина двухбайтового «П» и выход за конец файла")

NO_HELPER = Q.replace(HELPER + "\n", "")
case("edit", "remove-without-intent-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": NO_HELPER}]),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": NO_HELPER}],
            ops=[{"op": "delete", "id": "cq0007", "reason": "не используется"}])],
     [ok_begin(), blocked("ENTITY_REMOVED_WITHOUT_INTENT", ids=["cq0007"], names={"cq0007": "app.helper"}),
      ok_apply(2, {"app.bag": [[0, len(NO_HELPER.encode())]]},
               {"lineage": [{"op": "delete", "predecessors": ["cq0007"], "successors": [], "reason": "не используется"}],
                "removed": ["cq0007"], "added": [], "renamed": []})],
     note="удаление сущности только с объявленным намерением и причиной")

COPY_SAME = Q + "\n" + HELPER.replace("fn helper", "fn helper2")
COPY_NEW = Q + "\n" + HELPER.replace("fn helper", "fn helper2").replace("cq0007", "cq0009")
case("edit", "copy-identity-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": COPY_SAME}]),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": COPY_NEW}],
            ops=[{"op": "copy", "from": "cq0007", "id": "cq0009"}])],
     [ok_begin(), blocked("DUPLICATE_ENTITY_ID", ids=["cq0007"], places={"cq0007": ["app.bag", "app.bag"]}),
      ok_apply(2, {"app.bag": [[0, len(COPY_NEW.encode())]]},
               {"lineage": [{"op": "copy", "predecessors": ["cq0007"], "successors": ["cq0009"], "reason": None}],
                "removed": [], "added": ["cq0009"], "renamed": []})],
     note="копия с прежним ID — скрытый конфликт; копия обязана получить новый ID (T03-C03)")

RENAMED = Q.replace("fn helper(", "fn helper_two(")
case("edit", "rename-keeps-id-01", [S3],
     [begin(), apply(1, "a1", [old("app.bag", "fn helper(", "fn helper_two(")], ops=[{"op": "rename", "id": "cq0005"}]),
      apply(1, "a2", [old("app.bag", "fn helper(", "fn helper_two(")], ops=[{"op": "rename", "id": "cq0007"}])],
     [ok_begin(), blocked("IDENTITY_OP_MISMATCH", op=0),
      ok_apply(2, {"app.bag": [list(pos(RENAMED, "fn helper_two("))]},
               {"lineage": [{"op": "rename", "predecessors": ["cq0007"], "successors": ["cq0007"], "reason": None,
                             "names": ["app.helper", "app.helper_two"]}],
                "removed": [], "added": [], "renamed": ["cq0007"]})],
     note="переименование сохраняет ID; объявленный rename сущности, чьё имя не менялось, — несоответствие")

SPLIT = Q.replace(HELPER, '''@id("cq000a")
fn helper_a(n: Int64) -> Int64 {
  n
}

@id("cq000b")
fn helper_b(n: Int64) -> Int64 {
  n + 1
}
''')
case("edit", "split-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": SPLIT}],
                     ops=[{"op": "split", "from": "cq0007", "into": ["cq000a"], "reason": "r"}]),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": SPLIT}],
            ops=[{"op": "split", "from": "cq0007", "into": ["cq000a", "cq000b"], "reason": "две роли"}])],
     [ok_begin(), blocked("IDENTITY_OP_MISMATCH", op=0),
      ok_apply(2, {"app.bag": [[0, len(SPLIT.encode())]]},
               {"lineage": [{"op": "split", "predecessors": ["cq0007"], "successors": ["cq000a", "cq000b"],
                             "reason": "две роли"}],
                "removed": ["cq0007"], "added": ["cq000a", "cq000b"], "renamed": []})],
     note="split требует не меньше двух преемников; преемник не угадывается")

EXTRA = '''module app.extra

fn one() -> Int64 {
  1
}
'''
case("edit", "assign-ids-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app/extra.bag", "create": EXTRA}], assign=True)],
     [ok_begin(), ok_apply(2, {"app/extra.bag": [[0, len(EXTRA.encode())]]},
                           {"lineage": [], "removed": [], "added": ["<assigned>", "<assigned>"], "renamed": []})],
     note="новый файл без @id: назначаются два ID (модуль и функция) — детерминированно по семени работы")

case("edit", "retired-id-01", [S3, S8],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": NO_HELPER}],
                     ops=[{"op": "delete", "id": "cq0007", "reason": "не используется"}]),
      write("accept", 2, "c1"), begin(n=2),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": Q}], ch="$change2")],
     [ok_begin(), ok_apply(2, {"app.bag": [[0, len(NO_HELPER.encode())]]},
                           {"lineage": [{"op": "delete", "predecessors": ["cq0007"], "successors": [], "reason": "не используется"}],
                            "removed": ["cq0007"], "added": [], "renamed": []}),
      accepted(3, lineage=[["delete", ["cq0007"], []]]), ok_begin(), blocked("ENTITY_ID_RETIRED", ids=["cq0007"])],
     head_rev=2, note="ID, удалённый принятой работой, не используется повторно (01 §7A)")

# ============================================================ accept
case("accept", "flow-01", [S5, S6, S8],
     [begin(), apply(1, "a1", [GREET_EDIT]), resume(), write("accept", 2, "c1"), write("verify", 2, "v1"), resume(),
      write("accept", 3, "c2"), write("accept", 3, "c2")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(T_GREET)]}),
      resumed(2, ["OBLIGATION_OPEN", "OBLIGATION_OPEN", "TESTS_NOT_RUN"], GREET_OPEN),
      blocked("OPEN_OBLIGATIONS", blockers=["OBLIGATION_OPEN", "TESTS_NOT_RUN"]),
      verified(3, [[TEST, "PASS"]]), resumed(3, [], GREET_OK),
      accepted(4, GREET_ACC), accepted(4, GREET_ACC, replayed=True)],
     head_rev=2, note="обязательства открыты до свидетельств, затронутый тест не прогнан; применимые PASS неизменённого "
                      "теста базы закрывают их")

HELPER_EDIT = old("app.bag", "  n + 1\n", "  n + 2\n")
case("accept", "stale-base-rebase-01", [S8, S9],
     [begin(), begin(n=2), apply(1, "a1", [GREET_EDIT]), write("verify", 2, "v1"), write("accept", 3, "c1"),
      apply(1, "a2", [HELPER_EDIT], ch="$change2"), write("accept", 2, "c2", ch="$change2"),
      resume("$change2"), write("rebase", 2, "r2", ch="$change2"), resume("$change2"),
      write("accept", 3, "c3", ch="$change2")],
     [ok_begin(), ok_begin(), ok_apply(2, {"app.bag": [list(T_GREET)]}), verified(3, [[TEST, "PASS"]]),
      accepted(4, GREET_ACC),
      ok_apply(2, {"app.bag": [list(pos(Q.replace("  n + 1\n", "  n + 2\n"), "  n + 2\n"))]}),
      blocked("STALE_BASE"),
      resumed(2, ["NEEDS_REBASE"], needs_rebase=True),
      {"status": "succeeded", "replayed": False, "work_revision": 3, "identity": NO_ID},
      resumed(3), accepted(4)],
     head_rev=3, origin=FIX + "#C07",
     note="две работы от одной базы: вторая получает STALE_BASE, head не меняется; перенос по old_text на новый head "
          "даёт совместный кандидат, он проверяется и принимается (C07; T10-C04, T10-C05)")

s2, e2 = pos(Q, '"Привет, "')
case("accept", "rebase-conflict-01", [S9],
     [begin(), begin(n=2), apply(1, "a1", [GREET_EDIT]), write("verify", 2, "v1"), write("accept", 3, "c1"),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "edits": [{"start": s2, "end": e2, "text": '"Хай, "'}]}],
            ch="$change2"),
      write("rebase", 2, "r2", ch="$change2")],
     [ok_begin(), ok_begin(), ok_apply(2, {"app.bag": [list(T_GREET)]}), verified(3, [[TEST, "PASS"]]),
      accepted(4, GREET_ACC),
      ok_apply(2, {"app.bag": [[s2, s2 + len('"Хай, "'.encode())]]}), blocked("REBASE_CONFLICT", path="app.bag")],
     head_rev=2, note="правка по байтовому диапазону изменённого файла не переносится — автоматического слияния нет")

EMPTY = old("app.bag", '"Привет, " ++ name', '""')
case("accept", "contradicted-01", [S5, S6],
     [begin(), apply(1, "a1", [EMPTY]), write("verify", 2, "v1"), resume(), write("accept", 3, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q.replace('"Привет, " ++ name', '""'), '""'))]}),
      verified(3, [[TEST, "FAIL"]]),
      resumed(3, ["EVIDENCE_CONTRADICTED", "OBLIGATION_CONTRADICTED", "OBLIGATION_CONTRADICTED"],
              [[RULE, GREET, "implements", "contradicted", "tests"], [RULE, TEST, "checks", "contradicted", "tests"]]),
      blocked("OPEN_OBLIGATIONS", blockers=["EVIDENCE_CONTRADICTED", "OBLIGATION_CONTRADICTED"])],
     note="применимый FAIL — противоречие; успешной проверки типов недостаточно")

WEAK = [old("app.bag", '"Привет, " ++ name', '""'), ]
WEAK_TEST = old("app.bag", 'test.expect("не пусто", greet("x") != "")', 'test.expect("не пусто", true)')
case("accept", "weakened-test-01", [S4, S6],
     [begin(), apply(1, "a1", [EMPTY]), apply(2, "a2", [WEAK_TEST]), write("verify", 3, "v1"), resume(),
      write("contract_update", 4, "k1", ops=[{"op": "add_clause", "id": "c1", "claim": "тест проходит",
                                               "method": {"test": TEST}}]),
      resume()],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q.replace('"Привет, " ++ name', '""'), '""'))]}),
      ok_apply(3, {"app.bag": [list(pos(Q.replace('"Привет, " ++ name', '""').replace(
          'test.expect("не пусто", greet("x") != "")', 'test.expect("не пусто", true)'), 'test.expect("не пусто", true)'))]}),
      verified(4, [[TEST, "PASS"]]),
      resumed(4, ["OBLIGATION_OPEN", "OBLIGATION_OPEN"],
              [[RULE, GREET, "implements", "open", "base-test-changed"], [RULE, TEST, "checks", "open", "base-test-changed"]]),
      contract(5, 2, ["c1"]),
      resumed(5, ["OBLIGATION_OPEN", "OBLIGATION_OPEN"],
              [[RULE, GREET, "implements", "open", "base-test-changed"], [RULE, TEST, "checks", "open", "base-test-changed"]],
              clauses=[["c1", "supported", "tests"]], contract_rev=2)],
     note="тест изменён в работе — его PASS не закрывает обязательство правила; условие контракта с этим тестом "
          "выполнено, но без явного replace_test обязательство остаётся открытым (T10-C02)")

case("accept", "clause-remove-01", [S4, S8],
     [begin(), write("contract_update", 1, "k1", ops=[{"op": "add_clause", "id": "c1", "claim": "тест проходит",
                                                       "method": {"test": TEST}}]),
      resume(), write("contract_update", 2, "k2", ops=[{"op": "remove_clause", "id": "c1"}]),
      write("contract_update", 2, "k3", ops=[{"op": "remove_clause", "id": "c1", "reason": "условие перенесено"}]),
      write("accept", 3, "c1")],
     [ok_begin(), contract(2, 2, ["c1"]),
      resumed(2, ["CLAUSE_OPEN"], clauses=[["c1", "open", "evidence-missing"]], contract_rev=2),
      failed("REQUEST_INVALID", op=0), contract(3, 3, replaced=[["c1", False]]),
      accepted(4, replaced=["c1"])],
     head_rev=2, note="условие без свидетельства блокирует; удалить его можно только с причиной, удаление видно в приёмке")

case("accept", "evidence-transfer-01", [S5],
     [begin(), apply(1, "a1", [GREET_EDIT]), write("verify", 2, "v1"), apply(3, "a2", [HELPER_EDIT]), resume(),
      apply(4, "a3", [old("app.bag", '"Здравствуй, " ++ name', '"Добрый день, " ++ name')]), resume()],
     [ok_begin(), ok_apply(2, {"app.bag": [list(T_GREET)]}), verified(3, [[TEST, "PASS"]]),
      ok_apply(4, {"app.bag": [list(pos(Q.replace('"Привет, " ++ name', '"Здравствуй, " ++ name').replace("  n + 1\n", "  n + 2\n"),
                                        "  n + 2\n"))]}),
      resumed(4, [], GREET_OK),
      ok_apply(5, {"app.bag": [list(pos(Q.replace('"Привет, " ++ name', '"Добрый день, " ++ name').replace("  n + 1\n", "  n + 2\n"),
                                        '"Добрый день, " ++ name'))]}),
      resumed(5, ["OBLIGATION_OPEN", "OBLIGATION_OPEN", "TESTS_NOT_RUN"], GREET_OPEN)],
     note="правка helper не меняет замыкание теста — свидетельство переносится (same-closure); правка greet — свидетельство "
          "чужого кандидата устарело (T10-C03)")

case("accept", "scope-01", [S4, S6],
     [begin(), write("contract_update", 1, "k1", ops=[{"op": "scope", "allowed": ["app.helper"]}]),
      apply(2, "a1", [GREET_EDIT]), write("verify", 3, "v1"), write("accept", 4, "c1")],
     [ok_begin(), contract(2, 2, allowed=["app.helper"]),
      ok_apply(3, {"app.bag": [list(T_GREET)]}), verified(4, [[TEST, "PASS"]]),
      blocked("OPEN_OBLIGATIONS", blockers=["SCOPE_EXCEEDED"])],
     note="изменение вне области контракта блокирует приёмку")

case("accept", "assumption-01", [S4, S6],
     [begin(), apply(1, "a1", [old("app.bag", 'purpose "Приветствие пользователю"', 'purpose "Приветствие гостю"')]),
      resume(), write("contract_update", 2, "k1", ops=[{"op": "assume", "obligation": ["about", "cq0002", "cq0003"],
                                                        "reason": "смысл правила прежний"}]),
      resume(), write("accept", 3, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q.replace('purpose "Приветствие пользователю"', 'purpose "Приветствие гостю"'),
                                                     'purpose "Приветствие гостю"'))]}),
      resumed(2, ["OBLIGATION_OPEN"], [["app.Greeting", "app.Polite", "about", "open", "no-method"]]),
      contract(3, 2, assumptions=[["about", "cq0002", "cq0003"]]),
      resumed(3, [], [["app.Greeting", "app.Polite", "about", "supported", "assumption"]], contract_rev=2),
      accepted(4, [["about", "cq0002", "cq0003", "supported", "assumption"]])],
     head_rev=2, note="обязательство about по политике закрывается только принятым предположением с причиной")

SUP = old("app.bag", "fn helper(n: Int64) -> Int64 {", 'fn helper(n: Int64) -> Int64\n  supersedes "cq9999"\n{')
case("accept", "supersedes-unknown-01", [S6],
     [begin(), apply(1, "a1", [SUP]), resume(), write("accept", 2, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q.replace("fn helper(n: Int64) -> Int64 {",
                                                              'fn helper(n: Int64) -> Int64\n  supersedes "cq9999"\n{'),
                                                    'fn helper(n: Int64) -> Int64\n  supersedes "cq9999"\n{'))]}),
      resumed(2, ["SUPERSEDES_UNKNOWN"]), blocked("OPEN_OBLIGATIONS", blockers=["SUPERSEDES_UNKNOWN"])],
     note="supersedes сверяется с историей принятых снимков (SURF-15): ID, которого там не было, блокирует приёмку")

BAD_TYPE = old("app.bag", "  n + 1\n", '  n + "1"\n')
case("accept", "draft-01", [S3, S6],
     [begin(), apply(1, "a1", [BAD_TYPE]), resume(), write("verify", 2, "v1")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q.replace("  n + 1\n", '  n + "1"\n'), '  n + "1"\n'))]}, draft=True,
                           diags=["TYPE_MISMATCH"]),
      resumed(2, ["CANDIDATE_INVALID"]), blocked("CANDIDATE_INVALID")],
     note="кандидат с ошибкой проверки — черновик: ни свидетельств, ни приёмки")


# ============================================================ ревью m6: ложные приёмки и неточности
Q2 = Q + '''
@id("cq0009")
test greet_has_name
  checks Polite.nonempty
{
  test.expect("имя", greet("Иван") == "Привет, Иван")
}
'''
T2 = "app.greet_has_name"
BANG = old("app.bag", '"Привет, " ++ name', '"Привет!"')
WEAK2 = old("app.bag", 'test.expect("имя", greet("Иван") == "Привет, Иван")', 'test.expect("имя", true)')
Q2a = Q2.replace('"Привет, " ++ name', '"Привет!"')
Q2b = Q2a.replace('test.expect("имя", greet("Иван") == "Привет, Иван")', 'test.expect("имя", true)')
W2_OPEN = [[RULE, GREET, "implements", "open", "base-test-changed"], [RULE, TEST, "checks", "open", "base-test-changed"],
           [RULE, T2, "checks", "open", "base-test-changed"]]
W2_OK = [[RULE, GREET, "implements", "supported", "tests"], [RULE, TEST, "checks", "supported", "tests"],
         [RULE, T2, "checks", "supported", "tests"]]
case("accept", "weakened-second-test-01", [S5, S6],
     [begin(), apply(1, "a1", [BANG]), apply(2, "a2", [WEAK2]), write("verify", 3, "v1"), resume(), write("accept", 4, "c1"),
      write("contract_update", 4, "k1", ops=[{"op": "replace_test", "test": T2}]),
      write("contract_update", 4, "k2", ops=[{"op": "replace_test", "test": T2, "reason": "проверка имени снята осознанно"}]),
      resume(), write("accept", 5, "c2")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q2a, '"Привет!"'))]}),
      ok_apply(3, {"app.bag": [list(pos(Q2b, 'test.expect("имя", true)'))]}),
      verified(4, [[TEST, "PASS"], [T2, "PASS"]]),
      resumed(4, ["OBLIGATION_OPEN"] * 3, W2_OPEN), blocked("OPEN_OBLIGATIONS", blockers=["OBLIGATION_OPEN"]),
      failed("REQUEST_INVALID", op=0), contract(5, 2, replaced_tests=[T2]),
      resumed(5, [], W2_OK, contract_rev=2),
      accepted(6, [["checks", "cq0004", "cq0008", "supported", "tests"], ["checks", "cq0004", "cq0009", "supported", "tests"],
                   ["implements", "cq0004", "cq0005", "supported", "tests"]],
               replaced_tests=[[T2, "проверка имени снята осознанно"]])],
     files={"app.bag": Q2}, head_rev=2,
     note="у правила два теста; один ослаблен — PASS второго не закрывает обязательство, пока набор методов "
          "не изменён явно (replace_test с причиной); замена видна в записи приёмки (ревью m6 H1, K6)")

Q3 = Q + '''
@id("cq0009")
test shout_exact
{
  test.expect("крик", shout("Иван") == "Привет, Иван!")
}
'''
case("accept", "fail-unlinked-test-01", [S5, S6],
     [begin(), apply(1, "a1", [old("app.bag", 'greet(name) ++ "!"', 'greet(name) ++ "?"')]), resume(),
      write("verify", 2, "v1"), resume(), write("accept", 3, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q3.replace('greet(name) ++ "!"', 'greet(name) ++ "?"'), 'greet(name) ++ "?"'))]}),
      resumed(2, ["TESTS_NOT_RUN"]), verified(3, [[TEST, "PASS"], ["app.shout_exact", "FAIL"]]),
      resumed(3, ["EVIDENCE_CONTRADICTED"]), blocked("OPEN_OBLIGATIONS", blockers=["EVIDENCE_CONTRADICTED"])],
     files={"app.bag": Q3},
     note="тест без checks: затронутый тест обязан быть прогнан, применимый FAIL — противоречие, даже если правила "
          "у теста нет (A05 шаг 2; ревью m6 H2)")

SCOPE_RENAME = Q.replace(HELPER + "\n", "").replace('''pub fn shout(name: String) -> String {
  greet(name) ++ "!"
}''', '''pub fn helper(name: String) -> String {
  greet(name) ++ "?!"
}''')
case("accept", "scope-rename-01", [S4, S6],
     [begin(), write("contract_update", 1, "k1", ops=[{"op": "scope", "allowed": ["app.helper"]}]),
      apply(2, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": SCOPE_RENAME}],
            ops=[{"op": "delete", "id": "cq0007", "reason": "не нужен"}]),
      write("verify", 3, "v1"), resume(), write("accept", 4, "c1")],
     [ok_begin(), contract(2, 2, allowed=["app.helper"]),
      ok_apply(3, {"app.bag": [[0, len(SCOPE_RENAME.encode())]]},
               {"lineage": [{"op": "delete", "predecessors": ["cq0007"], "successors": [], "reason": "не нужен"}],
                "removed": ["cq0007"], "added": [], "renamed": ["cq0006"]}),
      verified(4, [[TEST, "PASS"]]), resumed(4, ["SCOPE_EXCEEDED"], contract_rev=2),
      blocked("OPEN_OBLIGATIONS", blockers=["SCOPE_EXCEEDED"])],
     note="область по имени: сущность внутри, только если в области её имя и в базе, и в кандидате — переименование "
          "shout в разрешённое имя helper область не обходит (ревью m6 H3)")

BANG_RULE = '@id("cq0004") rule nonempty "приветствие не пустое"\n  @id("cq000c") rule bang "крик с восклицанием"'
BANG_FN = 'pub fn shout(name: String) -> String\n  implements Polite.bang\n{'
BANG_TEST = '@id("cq000d")\ntest shout_bang\n  checks Polite.bang\n{\n  test.expect("!", shout("x") != "")\n}\n\n@id("cq0008")'
NEW_RULE_OBL_OPEN = [["app.Greeting", "app.Polite", "about", "open", "no-method"],
                     ["app.Polite.bang", "app.shout", "implements", "supported", "tests"],
                     ["app.Polite.bang", "app.shout_bang", "checks", "supported", "tests"]]
NEW_RULE_OBL_OK = [["app.Greeting", "app.Polite", "about", "supported", "assumption"]] + NEW_RULE_OBL_OPEN[1:]
QN = Q.replace('@id("cq0004") rule nonempty "приветствие не пустое"', BANG_RULE).replace(
    "pub fn shout(name: String) -> String {", BANG_FN).replace('@id("cq0008")', BANG_TEST)
case("accept", "new-rule-01", [S4, S5, S6],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "edits": [
         {"old_text": '@id("cq0004") rule nonempty "приветствие не пустое"', "text": BANG_RULE},
         {"old_text": "pub fn shout(name: String) -> String {", "text": BANG_FN},
         {"old_text": '@id("cq0008")', "text": BANG_TEST}]}]),
      write("verify", 2, "v1"), resume(),
      write("contract_update", 3, "k1", ops=[
          {"op": "add_clause", "id": "bang", "claim": "shout кричит", "method": {"test": "app.shout_bang"}},
          {"op": "assume", "obligation": ["about", "cq0002", "cq0003"], "reason": "новое правило того же смысла"}]),
      resume(), write("accept", 4, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": sorted([list(pos(QN, BANG_RULE)), list(pos(QN, BANG_FN)), list(pos(QN, BANG_TEST))])},
                           dict(NO_ID, added=["cq000c", "cq000d"])),
      verified(3, [[TEST, "PASS"], ["app.shout_bang", "PASS"]]),
      resumed(3, ["OBLIGATION_OPEN", "OBLIGATION_OPEN", "OBLIGATION_OPEN"],
              [["app.Polite.bang", "app.shout", "implements", "open", "no-method-tests"],
               ["app.Polite.bang", "app.shout_bang", "checks", "open", "no-method-tests"],
               NEW_RULE_OBL_OPEN[0]]),
      contract(4, 2, ["bang"], assumptions=[["about", "cq0002", "cq0003"]]),
      resumed(4, [], NEW_RULE_OBL_OK, clauses=[["bang", "supported", "tests"]], contract_rev=2),
      accepted(5, [["about", "cq0002", "cq0003", "supported", "assumption"],
                   ["checks", "cq000c", "cq000d", "supported", "tests"],
                   ["implements", "cq000c", "cq0006", "supported", "tests"]])],
     head_rev=2,
     note="новое правило: тестов базы у него нет; обязательства закрывает новый тест, только когда он назван методом "
          "условия контракта (CHG-13; ревью m6 H5). Изменение контракта Polite — обязательство about, оно закрывается "
          "предположением")

case("accept", "policy-01", [S4, S6],
     [begin(), apply(1, "a1", [GREET_EDIT]), write("verify", 2, "v1"), resume(),
      write("contract_update", 3, "k1", ops=[{"op": "assume", "obligation": ["implements", "cq0004", "cq0005"],
                                               "reason": "реализация проверена ревью"}]),
      resume(), write("accept", 4, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(T_GREET)]}), verified(3, [[TEST, "PASS"]]),
      resumed(3, ["OBLIGATION_OPEN"], [[RULE, GREET, "implements", "open", "no-method"],
                                       [RULE, TEST, "checks", "supported", "tests"]]),
      contract(4, 2, assumptions=[["implements", "cq0004", "cq0005"]]),
      resumed(4, [], [[RULE, GREET, "implements", "supported", "assumption"], [RULE, TEST, "checks", "supported", "tests"]],
              contract_rev=2),
      accepted(5, [["checks", "cq0004", "cq0008", "supported", "tests"],
                   ["implements", "cq0004", "cq0005", "supported", "assumption"]])],
     policy={"obligations": {"implements": ["assumption"]}}, head_rev=2,
     note="раздел obligations политики заменяет основания вида поверх политики по умолчанию (CHG-10; ревью m6 H4)")

case("accept", "policy-changed-01", [S4, S6],
     [begin(), apply(1, "a1", [HELPER_EDIT]), {"op": "policy", "policy": {"obligations": {"about": ["assumption", "tests"]}}},
      resume(), write("accept", 2, "c1"), write("contract_update", 2, "k1", ops=[{"op": "pin_policy"}]),
      write("contract_update", 2, "k2", ops=[{"op": "pin_policy", "reason": "новая политика проекта"}]),
      write("accept", 3, "c2")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q.replace("  n + 1\n", "  n + 2\n"), "  n + 2\n"))]}),
      {"status": "policy_changed"}, resumed(2, ["POLICY_CHANGED"]), blocked("OPEN_OBLIGATIONS", blockers=["POLICY_CHANGED"]),
      failed("REQUEST_INVALID", op=0), contract(3, 2, pins=["новая политика проекта"]), accepted(4)],
     head_rev=2, note="работа закрепляет ревизию политики (A05 шаг 3): смена политики — блокер, пока её не закрепят "
                      "заново с причиной (ревью m6 M6)")

case("accept", "rebase-assign-ids-01", [S3, S9],
     [begin(), begin(n=2), apply(1, "a1", [{"path": "app/extra.bag", "create": EXTRA}], assign=True),
      apply(1, "a2", [HELPER_EDIT], ch="$change2"), write("accept", 2, "c2", ch="$change2"),
      resume(), write("rebase", 2, "r1"), resume(), write("accept", 3, "c1")],
     [ok_begin(), ok_begin(), ok_apply(2, {"app/extra.bag": [[0, len(EXTRA.encode())]]},
                                       {"lineage": [], "removed": [], "added": ["<assigned>", "<assigned>"], "renamed": []}),
      ok_apply(2, {"app.bag": [list(pos(Q.replace("  n + 1\n", "  n + 2\n"), "  n + 2\n"))]}), accepted(3),
      resumed(2, ["NEEDS_REBASE"], needs_rebase=True),
      {"status": "succeeded", "replayed": False, "work_revision": 3,
       "identity": {"lineage": [], "removed": [], "added": ["<assigned>", "<assigned>"], "renamed": []}},
      resumed(3), accepted(4)],
     head_rev=3, note="ID, назначенные apply, переносятся rebase из журнала правок — кандидат после переноса проходит "
                      "проверку (ревью m6 M1)")

case("edit", "kind-change-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": Q.replace(
         HELPER, '@id("cq0007")\ntest helper\n{\n  test.expect("x", true)\n}\n')}])],
     [ok_begin(), blocked("ENTITY_KIND_CHANGED", ids=["cq0007"], kinds={"cq0007": ["fn", "test"]})],
     note="вид сущности под тем же ID не меняется (01 §3): функция не становится тестом без delete и нового ID "
          "(ревью m6 M8)")

QA = Q + "\n// ааа\n"
case("edit", "old-text-overlap-01", [S3],
     [begin(), apply(1, "a1", [old("app.bag", "аа", "б")])],
     [ok_begin(), blocked("AMBIGUOUS_EDIT", path="app.bag", edit=0, occurrences=2)],
     files={"app.bag": QA}, note="перекрывающиеся вхождения тоже считаются: «аа» в «ааа» — два (ревью m6 M2)")

case("edit", "path-alias-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app//extra.bag", "create": EXTRA}]),
      apply(1, "a2", [{"path": "app/./extra.bag", "create": EXTRA}]),
      apply(1, "a3", [{"path": ".hidden/extra.bag", "create": EXTRA}]),
      apply(1, "a4", [{"path": "app.bag", "base_sha256": "0" * 64, "edits": [{"old_text": "n + 1", "text": "n + 2"}]},
                      {"path": "b.bag", "create": ["не текст"]}])],
     [ok_begin(), failed("REQUEST_INVALID", path="app//extra.bag"), failed("REQUEST_INVALID", path="app/./extra.bag"),
      failed("REQUEST_INVALID", path=".hidden/extra.bag"), failed("REQUEST_INVALID", path="b.bag")],
     note="путь в нормальной форме — у файла одно имя; форма всей правки проверяется до base_sha256 (CHG-04; ревью m6 L)")


# программа сертификата D83(a) из корпуса Ф5 (conformance/gen/make_links_cases.py, impact/certificate-interface-01)
CERT = (OUT / "impact" / "certificate-interface-01" / "app.bag").read_text(encoding="utf-8")
CERT_EDIT = old("app.bag", "  Point { x: double(n) }", "  Point { x: double(n) + 0 }")
EP = "app.Exact.positive"
CERT_BASE = [[EP, "app.origin", "implements", "supported", "tests"], [EP, "app.origin_positive", "checks", "supported", "tests"],
             ["app.Counting", "app.S.copy", "derived_from", "open", "no-method"]]
case("accept", "d83a-policy-01", [S4, S6],
     [begin(), apply(1, "a1", [CERT_EDIT]), write("verify", 2, "v1"), resume(),
      {"op": "policy", "policy": {"obligations": {"requires": ["tests"]}}}, resume()],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(CERT.replace("  Point { x: double(n) }", "  Point { x: double(n) + 0 }"),
                                                    "  Point { x: double(n) + 0 }"))]}),
      verified(3, [["app.origin_positive", "PASS"]]),
      resumed(3, ["OBLIGATION_OPEN"], CERT_BASE), {"status": "policy_changed"},
      resumed(3, ["OBLIGATION_OPEN", "POLICY_CHANGED"], CERT_BASE + [[EP, "app.add", "requires", "supported", "tests"]])],
     files={"app.bag": CERT},
     note="по политике по умолчанию сертификат D83(a) закрывает обязательство requires команды add; политика без D83a "
          "для requires делает его обычным обязательством — его закрывают тесты правила (CHG-10; ревью m6 M6)")


# ============================================================ authorship: C04, C06
def app_files():
    return {f.relative_to(APP).as_posix(): f.read_text(encoding="utf-8") for f in sorted(APP.rglob("*.bag"))}


B = "blog."
CR = B + "authorship.AttributionComplete.complete"
case("accept", "authorship-c04-01", [S5, S6],
     [begin(), apply(1, "a1", [old("blog/export.bag", "authors_json(xs, all_people, i + 1,", "authors_json([], all_people, i + 1,")]),
      write("verify", 2, "v1"), resume(), write("accept", 3, "c1")],
     [ok_begin(), ok_apply(2, {"blog/export.bag": [list(pos(app_files()["blog/export.bag"].replace(
         "authors_json(xs, all_people, i + 1,", "authors_json([], all_people, i + 1,"), "authors_json([], all_people, i + 1,"))]}),
      verified(3, [[B + "tests.export_keeps_all_authors", "FAIL"], [B + "tests.make_enforces_shape", "PASS"],
                   [B + "tests.store_copy_is_isolated", "PASS"]]),
      resumed(3, ["EVIDENCE_CONTRADICTED", "OBLIGATION_CONTRADICTED", "OBLIGATION_CONTRADICTED"],
              [[CR, B + "export.export_article", "requires", "contradicted", "tests"],
               [CR, B + "tests.export_keeps_all_authors", "checks", "contradicted", "tests"]]),
      blocked("OPEN_OBLIGATIONS", blockers=["EVIDENCE_CONTRADICTED", "OBLIGATION_CONTRADICTED"])],
     files=app_files(), origin=FIX + "#C04",
     note="экспорт только первого автора при прежней сигнатуре: проверка типов проходит, тест полноты падает — приёмка запрещена")

IDS_EDIT = old("blog/authorship.bag", "    Authors(xs) => xs,", "    Authors(xs) => seq.concat(xs, []),")
C06_OBL = [[CR, B + "byline.byline", "requires", "open", "evidence-missing-or-stale"],
           [CR, B + "search.articles_by", "requires", "open", "evidence-missing-or-stale"],
           [CR, B + "indexer.index_authorship", "implements", "open", "evidence-missing-or-stale"],
           [CR, B + "export.export_article", "requires", "open", "evidence-missing-or-stale"],
           [CR, B + "tests.export_keeps_all_authors", "checks", "open", "evidence-missing-or-stale"],
           [B + "authorship.Authorship", B + "db.Blog.author_index", "derived_from", "open", "no-method"]]
C06_OK = [o[:3] + (["supported", "tests"] if o[2] != "derived_from" else o[3:]) for o in C06_OBL]
C06_AS = [o[:3] + (["supported", "tests"] if o[2] != "derived_from" else ["supported", "assumption"]) for o in C06_OBL]
C06_ASSUME = ["derived_from", "6qfcyw", "e2mrc6"]
case("accept", "authorship-c06-resume-01", [S5, S6],
     [begin(), apply(1, "a1", [IDS_EDIT]), write("verify", 2, "v1"), resume(), resume(principal="session_b"),
      write("accept", 3, "c1", principal="session_b"),
      write("contract_update", 3, "k1", principal="session_b",
            ops=[{"op": "assume", "obligation": C06_ASSUME, "reason": "индекс строится из того же состава авторов"}]),
      resume(principal="session_b"), write("accept", 4, "c2", principal="session_b")],
     [ok_begin(), ok_apply(2, {"blog/authorship.bag": [list(pos(app_files()["blog/authorship.bag"].replace(
         "    Authors(xs) => xs,", "    Authors(xs) => seq.concat(xs, []),"), "    Authors(xs) => seq.concat(xs, []),"))]}),
      verified(3, [[B + "tests.export_keeps_all_authors", "PASS"], [B + "tests.make_enforces_shape", "PASS"],
                   [B + "tests.store_copy_is_isolated", "PASS"]]),
      resumed(3, ["OBLIGATION_OPEN"], C06_OK), resumed(3, ["OBLIGATION_OPEN"], C06_OK),
      blocked("OPEN_OBLIGATIONS", blockers=["OBLIGATION_OPEN"]),
      contract(4, 2, assumptions=[C06_ASSUME]),
      resumed(4, [], C06_AS, contract_rev=2),
      accepted(5, [["checks", "6abbe4", "8hqzc5", "supported", "tests"],
                   ["derived_from", "6qfcyw", "e2mrc6", "supported", "assumption"],
                   ["implements", "6abbe4", "z1ac6c", "supported", "tests"],
                   ["requires", "6abbe4", "2mtfg0", "supported", "tests"],
                   ["requires", "6abbe4", "7y89wt", "supported", "tests"],
                   ["requires", "6abbe4", "qcp1fw", "supported", "tests"]],
               gaps=[["2mtfg0", "EXTERNAL_CONSUMERS"]])],
     files=app_files(), head_rev=2, origin=FIX + "#C06",
     note="другая сессия продолжает работу: те же обязательства и те же применимые свидетельства (оценка пересчитана, "
          "O04, O05, O10), тот же запрет приёмки; закрыв оставшееся обязательство, она принимает работу. Пробел покрытия "
          "публичного запроса записан в приёмку")

# ============================================================ полнота предметов критериев (переоценка r34)
SHOUT = '@id("cq0006")\npub fn shout(name: String) -> String {\n  greet(name) ++ "!"\n}\n'
MERGED_FN = '@id("cq000h")\npub fn shout(name: String) -> String {\n  greet(name) ++ "!"\n}\n'
MERGED = Q.replace(SHOUT + "\n" + HELPER, MERGED_FN)
case("edit", "merge-01", [S3],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": MERGED}],
                     ops=[{"op": "merge", "from": ["cq0006"], "into": "cq000h", "reason": "r"}]),
      apply(1, "a2", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": MERGED}],
            ops=[{"op": "merge", "from": ["cq0006", "cq0007"], "into": "cq000h", "reason": "одна функция"}])],
     [ok_begin(), blocked("IDENTITY_OP_MISMATCH", op=0),
      ok_apply(2, {"app.bag": [[0, len(MERGED.encode())]]},
               {"lineage": [{"op": "merge", "predecessors": ["cq0006", "cq0007"], "successors": ["cq000h"],
                             "reason": "одна функция"}],
                "removed": ["cq0006", "cq0007"], "added": ["cq000h"], "renamed": []})],
     note="merge требует не меньше двух источников и нового ID преемника; источники и преемник — в lineage")

SPLIT_RULE = (Q.replace('  @id("cq0004") rule nonempty "приветствие не пустое"',
                        '  @id("cq000e") rule filled "приветствие не пустое"\n  @id("cq000f") rule greets "приветствие начинается с привета"')
               .replace("  implements Polite.nonempty", "  implements Polite.filled, Polite.greets")
               .replace("  checks Polite.nonempty", "  checks Polite.filled, Polite.greets"))
PF, PG = "app.Polite.filled", "app.Polite.greets"
SPLIT_OPEN = [[RULE, GREET, "implements", "open", "successor-evidence"], [RULE, TEST, "checks", "open", "successor-evidence"],
              [PF, GREET, "implements", "open", "no-method-tests"], [PG, GREET, "implements", "open", "no-method-tests"],
              [PF, TEST, "checks", "open", "no-method-tests"], [PG, TEST, "checks", "open", "no-method-tests"],
              ["app.Greeting", "app.Polite", "about", "open", "no-method"]]
SPLIT_OK = [[RULE, GREET, "implements", "supported", "successor-tests"], [RULE, TEST, "checks", "supported", "successor-tests"],
            [PF, GREET, "implements", "supported", "tests"], [PG, GREET, "implements", "supported", "tests"],
            [PF, TEST, "checks", "supported", "tests"], [PG, TEST, "checks", "supported", "tests"],
            ["app.Greeting", "app.Polite", "about", "supported", "assumption"]]
case("accept", "split-rule-01", [S3, S6, S8],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": SPLIT_RULE}],
                     ops=[{"op": "split", "from": "cq0004", "into": ["cq000e", "cq000f"], "reason": "два требования"}]),
      write("verify", 2, "v1"), resume(),
      write("contract_update", 3, "k1", ops=[
          {"op": "add_clause", "id": "c1", "claim": "тест проверяет оба правила", "method": {"test": TEST}},
          {"op": "assume", "obligation": ["about", "cq0002", "cq0003"], "reason": "смысл контракта прежний"}]),
      resume(), write("accept", 4, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [[0, len(SPLIT_RULE.encode())]]},
                           {"lineage": [{"op": "split", "predecessors": ["cq0004"], "successors": ["cq000e", "cq000f"],
                                         "reason": "два требования"}],
                            "removed": ["cq0004"], "added": ["cq000e", "cq000f"], "renamed": []}),
      verified(3, [[TEST, "PASS"]]),
      resumed(3, ["OBLIGATION_OPEN"] * 7, SPLIT_OPEN),
      contract(4, 2, ["c1"], assumptions=[["about", "cq0002", "cq0003"]]),
      resumed(4, [], SPLIT_OK, clauses=[["c1", "supported", "tests"]], contract_rev=2),
      accepted(5, [["about", "cq0002", "cq0003", "supported", "assumption"],
                   ["checks", "cq0004", "cq0008", "supported", "successor-tests"],
                   ["implements", "cq0004", "cq0005", "supported", "successor-tests"],
                   ["checks", "cq000e", "cq0008", "supported", "tests"], ["checks", "cq000f", "cq0008", "supported", "tests"],
                   ["implements", "cq000e", "cq0005", "supported", "tests"], ["implements", "cq000f", "cq0005", "supported", "tests"]],
               lineage=[["split", ["cq0004"], ["cq000e", "cq000f"]]])],
     head_rev=2,
     note="преемник при split не угадывается: обязательства прежнего правила открыты, пока их не закроют методы "
          "преемников; изменённый тест считается методом новых правил, только когда назван условием контракта (T02-C03)")

QM = (Q.replace('  @id("cq0004") rule nonempty "приветствие не пустое"',
                '  @id("cq0004") rule nonempty "приветствие не пустое"\n  @id("cq000j") rule short "приветствие короткое"')
       .replace("  implements Polite.nonempty", "  implements Polite.nonempty, Polite.short")
       .replace("  checks Polite.nonempty", "  checks Polite.nonempty, Polite.short"))
QM2 = (QM.replace('  @id("cq0004") rule nonempty "приветствие не пустое"\n  @id("cq000j") rule short "приветствие короткое"',
                  '  @id("cq000k") rule sane "приветствие не пустое и короткое"')
         .replace("  implements Polite.nonempty, Polite.short", "  implements Polite.sane")
         .replace("  checks Polite.nonempty, Polite.short", "  checks Polite.sane"))
PS, PN = "app.Polite.short", "app.Polite.sane"
MERGE_OPEN = [[RULE, GREET, "implements", "open", "successor-evidence"], [PS, GREET, "implements", "open", "successor-evidence"],
              [RULE, TEST, "checks", "open", "successor-evidence"], [PS, TEST, "checks", "open", "successor-evidence"],
              [PN, GREET, "implements", "open", "no-method-tests"], [PN, TEST, "checks", "open", "no-method-tests"],
              ["app.Greeting", "app.Polite", "about", "open", "no-method"]]
MERGE_OK = [[RULE, GREET, "implements", "supported", "successor-tests"], [PS, GREET, "implements", "supported", "successor-tests"],
            [RULE, TEST, "checks", "supported", "successor-tests"], [PS, TEST, "checks", "supported", "successor-tests"],
            [PN, GREET, "implements", "supported", "tests"], [PN, TEST, "checks", "supported", "tests"],
            ["app.Greeting", "app.Polite", "about", "supported", "assumption"]]
case("accept", "merge-rule-01", [S3, S6, S8],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": QM2}],
                     ops=[{"op": "merge", "from": ["cq0004", "cq000j"], "into": "cq000k", "reason": "одно требование"}]),
      write("verify", 2, "v1"), resume(),
      write("contract_update", 3, "k1", ops=[
          {"op": "add_clause", "id": "c1", "claim": "тест проверяет объединённое правило", "method": {"test": TEST}},
          {"op": "assume", "obligation": ["about", "cq0002", "cq0003"], "reason": "смысл контракта прежний"}]),
      resume(), write("accept", 4, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [[0, len(QM2.encode())]]},
                           {"lineage": [{"op": "merge", "predecessors": ["cq0004", "cq000j"], "successors": ["cq000k"],
                                         "reason": "одно требование"}],
                            "removed": ["cq0004", "cq000j"], "added": ["cq000k"], "renamed": []}),
      verified(3, [[TEST, "PASS"]]),
      resumed(3, ["OBLIGATION_OPEN"] * 7, MERGE_OPEN),
      contract(4, 2, ["c1"], assumptions=[["about", "cq0002", "cq0003"]]),
      resumed(4, [], MERGE_OK, clauses=[["c1", "supported", "tests"]], contract_rev=2),
      accepted(5, [["about", "cq0002", "cq0003", "supported", "assumption"],
                   ["checks", "cq0004", "cq0008", "supported", "successor-tests"],
                   ["checks", "cq000j", "cq0008", "supported", "successor-tests"],
                   ["implements", "cq0004", "cq0005", "supported", "successor-tests"],
                   ["implements", "cq000j", "cq0005", "supported", "successor-tests"],
                   ["checks", "cq000k", "cq0008", "supported", "tests"], ["implements", "cq000k", "cq0005", "supported", "tests"]],
               lineage=[["merge", ["cq0004", "cq000j"], ["cq000k"]]])],
     files={"app.bag": QM}, head_rev=2,
     note="merge двух правил: обязательства обоих источников открыты, пока их не закроют методы преемника; история "
          "в lineage приёмки (T02-C03)")

case("accept", "unknown-budget-01", [S6],
     [begin(), apply(1, "a1", [GREET_EDIT]), write("verify", 2, "v1"),
      {"request": {"operation": "work_resume", "change_id": "$change", "arguments": {"analysis_budget": 1}}},
      {"request": {"operation": "work_resume", "change_id": "$change", "arguments": {"budget": 30}}},
      write("accept", 3, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(T_GREET)]}), verified(3, [[TEST, "PASS"]]),
      resumed(3, ["ANALYSIS_INCOMPLETE", "OBLIGATION_UNKNOWN", "OBLIGATION_UNKNOWN"],
              [[RULE, GREET, "implements", "supported", "tests"], [RULE, TEST, "checks", "unknown", "analysis-incomplete"],
               ["app.Greeting", "app.Polite", "about", "unknown", "analysis-incomplete"]]),
      resumed(3, [], GREET_OK), accepted(4, GREET_ACC)],
     head_rev=2,
     note="бюджет анализа 1: неполный анализ и unknown обязательства блокируют (T10-C01); малый бюджет пакета контекста "
          "обязательств не сокращает (T11-C04); приёмка всегда пересчитывает полный анализ")

USE_HELPER = '@id("cq000g")\nfn use_helper() -> Int64 {\n  helper(1)\n}\n\n@id("cq0008")'
QU = Q.replace('@id("cq0008")', USE_HELPER)
case("accept", "composition-break-01", [S8, S9],
     [begin(), begin(n=2), apply(1, "a1", [old("app.bag", "fn helper(", "fn helper_two(")]),
      apply(1, "a2", [old("app.bag", '@id("cq0008")', USE_HELPER)], ch="$change2"),
      write("accept", 2, "c1"), resume("$change2"), write("rebase", 2, "r2", ch="$change2"), resume("$change2"),
      write("verify", 3, "v2", ch="$change2"), write("accept", 3, "c2", ch="$change2")],
     [ok_begin(), ok_begin(), ok_apply(2, {"app.bag": [list(pos(RENAMED, "fn helper_two("))]},
                                       dict(NO_ID, renamed=["cq0007"])),
      ok_apply(2, {"app.bag": [list(pos(QU, USE_HELPER))]}, dict(NO_ID, added=["cq000g"])),
      accepted(3), resumed(2, ["NEEDS_REBASE"], needs_rebase=True),
      {"status": "succeeded", "replayed": False, "work_revision": 3, "identity": dict(NO_ID, added=["cq000g"])},
      resumed(3, ["CANDIDATE_INVALID"]), blocked("CANDIDATE_INVALID"),
      blocked("OPEN_OBLIGATIONS", blockers=["CANDIDATE_INVALID"])],
     head_rev=2,
     note="две правки успешны по отдельности (переименование helper и новый вызов helper); совместный кандидат после "
          "переноса проверяется заново и не принимается (T10-C05)")

SALUTE = (Q.replace("pub fn greet(", "pub fn salute(").replace("greet(name) ++", "salute(name) ++")
           .replace('greet("x")', 'salute("x")'))
SAL = "app.salute"
case("accept", "rename-refs-01", [S3, S6],
     [begin(), apply(1, "a1", [{"path": "app.bag", "base_sha256": "$sha:app.bag", "whole_file": SALUTE}]),
      write("verify", 2, "v1"), resume(),
      write("contract_update", 3, "k1", ops=[
          {"op": "replace_test", "test": TEST, "reason": "тест следует за переименованием"},
          {"op": "add_clause", "id": "c1", "claim": "тест проверяет переименованную функцию", "method": {"test": TEST}}]),
      resume(), write("accept", 4, "c1")],
     [ok_begin(), ok_apply(2, {"app.bag": [[0, len(SALUTE.encode())]]}, dict(NO_ID, renamed=["cq0005"])),
      verified(3, [[TEST, "PASS"]]),
      resumed(3, ["OBLIGATION_OPEN", "OBLIGATION_OPEN"],
              [[RULE, SAL, "implements", "open", "base-test-changed"], [RULE, TEST, "checks", "open", "base-test-changed"]]),
      contract(4, 2, ["c1"], replaced_tests=[TEST]),
      resumed(4, [], [[RULE, SAL, "implements", "supported", "tests"], [RULE, TEST, "checks", "supported", "tests"]],
              clauses=[["c1", "supported", "tests"]], contract_rev=2),
      accepted(5, GREET_ACC, replaced_tests=[[TEST, "тест следует за переименованием"]])],
     head_rev=2,
     note="переименование greet в salute с правкой вызывающих: ID и связи (implements, checks) сохраняются — пары "
          "обязательств те же по ID с новым именем (T02-C01). Текст теста изменился, поэтому тест — выбывший метод: "
          "нужна явная замена (CHG-13)")

case("protocol", "search-authorship-01", [S7],
     [{"request": {"operation": "search", "arguments": {"query": "атрибуция автор"}}},
      {"request": {"operation": "search", "arguments": {"query": "совместное редактирование статьи"}}}],
     [{"status": "succeeded", "replayed": False, "candidates": [[B + "authorship.Authorship", 2, ["purpose_or_terms"]]],
       "ambiguous": False, "selection": "none"},
      {"status": "succeeded", "replayed": False,
       "candidates": [[B + "authorship.Authorship", 0, ["not_about", "purpose_or_terms"]]],
       "ambiguous": True, "selection": "none"}],
     files=app_files(),
     note="на примере authorship: запрос о совместном редактировании совпадает со словом purpose, но not_about даёт "
          "отрицательное основание — кандидат, а не выбор (T11-C01, T11-C02)")


# ============================================================ protocol
case("protocol", "idempotency-01", [S7],
     [begin(), begin(), {"request": {"operation": "change_begin", "idempotency_key": key("b1"), "arguments": {"intent": "другое"}}},
      apply(5, "a1", [GREET_EDIT_LIT]), apply(1, "a1", [GREET_EDIT_LIT]), apply(1, "a1", [GREET_EDIT_LIT]),
      apply(2, "a1", [GREET_EDIT_LIT])],
     [ok_begin(), dict(ok_begin(), replayed=True), blocked("IDEMPOTENCY_CONFLICT", key=key("b1"), namespace="project"),
      blocked("WORK_CONFLICT"), ok_apply(2, {"app.bag": [list(T_GREET)]}),
      dict(ok_apply(2, {"app.bag": [list(T_GREET)]}), replayed=True),
      blocked("IDEMPOTENCY_CONFLICT", key=key("a1"), namespace="<change>")],
     note="тот же ключ и запрос — квитанция; другой запрос (в том числе другая ожидаемая ревизия) — конфликт; "
          "отказ guard'а ключ не резервирует")

case("protocol", "authority-01", [S7],
     [begin(), apply(1, "a1", [HELPER_EDIT]), write("accept", 2, "c1"), write("accept", 2, "c2", principal="reviewer"),
      begin(n=9, tag="r")],
     [ok_begin(), ok_apply(2, {"app.bag": [list(pos(Q.replace("  n + 1\n", "  n + 2\n"), "  n + 2\n"))]}),
      blocked("ACCESS_DENIED", operation="accept"), accepted(3), dict(ok_begin())],
     policy={"principals": {"agent": ["read", "change_begin", "apply", "verify"], "reviewer": ["*"]}}, head_rev=2,
     note="полномочие задаёт политика по субъекту транспорта; субъект запросом не назначается")

case("protocol", "request-invalid-01", [S7],
     [{"request": {"operation": "change_begin", "arguments": {"intent": "x"}}},
      {"request": {"operation": "deploy", "arguments": {}}},
      {"request": {"operation": "change_begin", "idempotency_key": key("b1"), "principal": "root", "arguments": {"intent": "x"}}},
      {"request": {"operation": "work_resume", "change_id": "ch-nope", "arguments": {}}},
      {"request": {"operation": "apply", "change_id": "ch-nope", "idempotency_key": key("a1"), "arguments": {}}}],
     [failed("REQUEST_INVALID"), failed("UNKNOWN_OPERATION", operation="deploy"), failed("REQUEST_INVALID"),
      failed("UNKNOWN_CHANGE", change_id="ch-nope"), failed("REQUEST_INVALID")],
     note="нет ключа; неизвестная операция; поле principal в запросе; неизвестная работа; запись без ожидаемой ревизии")

case("protocol", "search-01", [S7],
     [{"request": {"operation": "search", "arguments": {"query": "привет"}}},
      {"request": {"operation": "search", "arguments": {"query": "прощание привет"}}}],
     [{"status": "succeeded", "replayed": False, "candidates": [["app.Greeting", 1, ["purpose_or_terms"]]],
       "ambiguous": False, "selection": "none"},
      {"status": "succeeded", "replayed": False, "candidates": [["app.Greeting", 0, ["not_about", "purpose_or_terms"]]],
       "ambiguous": True, "selection": "none"}],
     note="поиск даёт кандидатов с основаниями, а не выбор; совпадение с not_about — отрицательное основание (T11-C01, T11-C02)")

case("protocol", "abandon-01", [S7],
     [begin(), write("abandon", 1, "x1"), write("abandon", 1, "x2", reason="не нужно"), apply(2, "a1", [HELPER_EDIT]),
      resume()],
     [ok_begin(), failed("REQUEST_INVALID"), {"status": "succeeded", "replayed": False, "work_revision": 2},
      blocked("WORK_CONFLICT", work_status="abandoned"), resumed(2, ["WORK_NOT_OPEN"], status="abandoned")],
     note="закрытая работа не принимает записей")


def main():
    for area in AREAS:
        shutil.rmtree(OUT / area, ignore_errors=True)
    for area, name, refs, files, run, exp, origin, note in CASES:
        d = OUT / area / name
        d.mkdir(parents=True)
        for rel, src in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(src, encoding="utf-8")
        c = {"id": f"{area}/{name}", "spec": refs, "origin": origin, "levels": ["L2"], "files": sorted(files),
             "run": run, "expect": exp}
        if note:
            c["note"] = note
        (d / "case.json").write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(CASES)} случаев: " + ", ".join(f"{a} {sum(1 for c in CASES if c[0] == a)}" for a in AREAS))


if __name__ == "__main__":
    main()
