#!/usr/bin/env python3
"""Автор случаев связей (Ф5): области graph, impact, context.

Ожидания выведены вручную из правил spec/links/08-bagaev-extraction.md (LNK-08-*), эталон для них не
запускается. Две группы:
- программа-счётчик app.bag с рёбрами всех видов (origin = independent);
- приложение examples/authorship и его правки — сценарии C05, C08, C10, C11, C12 фикстуры
  models/r07-core/data/authorship-fixtures.json, переведённые с символических узлов (E.export, E.byline, …)
  на настоящие сущности программы (origin = model:…#Cnn). Соответствие узлов — в поле note.
Повторный запуск перезаписывает эти области.

  python3 conformance/gen/make_links_cases.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "conformance" / "cases"
AREAS = ("graph", "impact", "context")
APP = ROOT / "examples" / "authorship"
FIX = "model:models/r07-core/data/authorship-fixtures.json"
_spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)


def anchor(h):
    return "spec/links/08-bagaev-extraction.md#" + _conf.slug(h)


L2, L3, L4, L5, L6 = (anchor(h) for h in ("2. Узлы и ревизии", "3. Рёбра", "4. Граф и покрытие",
                                          "5. Влияние", "6. ContextPack"))
OUT5 = "spec/kernel/outcomes.md#" + _conf.slug("4. Статусы анализа и знаний")

# ---------------------------------------------------------------------------- программа-счётчик
P = '''@id("nk0001")
module app

use std.store
use std.test

@id("nk0002")
pub type Point = record {
  @id("nk0003") x: Int64,
}

@id("nk0004")
pub entity Counting {
  purpose "Счёт"
}

@id("nk0005")
pub contract Exact about Counting {
  @id("nk0006") rule positive "итог положителен"
}

@id("nk0007")
pub store S {
  @id("nk0008") table totals: Map<String, Int64>
  @id("nk0009") table copy: Map<String, Int64> derived_from Counting
}

@id("nk000a")
pub event Added {
  @id("nk000b") name: String,
}

@id("nk000c")
fn double(n: Int64) -> Int64 {
  n * 2
}

@id("nk000d")
pub fn origin(n: Int64) -> Point
  implements Exact.positive
{
  Point { x: double(n) }
}

@id("nk000e")
pub command add(name: String) -> Result<(), Int64>
  uses { writes S.totals, emits Added }
  requires Exact.positive
{
  store.put(S.totals, name, origin(1).x);
  emit Added { name: name };
  Ok(())
}

@id("nk000f")
handler on_added(ev: Added)
  uses { reads S.totals, writes S.copy }
{
  match store.get(S.totals, ev.name) {
    Some(v) => store.put(S.copy, ev.name, v),
    None => (),
  }
}

@id("nk000g")
pub query total(name: String) -> Option<Int64>
  uses { reads S.copy }
{
  store.get(S.copy, name)
}

@id("nk000h")
fn apply(f: fn(Int64) -> Int64, n: Int64) -> Int64 {
  f(n)
}

@id("nk000j")
pub fn quadruple(n: Int64) -> Int64 {
  apply(double, double(n))
}

@id("nk000k")
pub fn alone(n: Int64) -> Int64 {
  n + 1
}

@id("nk000m")
test origin_positive
  checks Exact.positive
{
  test.expect("x", origin(1).x > 0)
}
'''


def edit(src, old, new):
    assert src.count(old) == 1, old
    return src.replace(old, new)


DOUBLE2 = edit(P, "  n * 2\n", "  n + n\n")
NO_ORIGIN = edit(edit(P, "  requires Exact.positive\n", ""), "store.put(S.totals, name, origin(1).x);",
                 "store.put(S.totals, name, 1);")
ORIGIN_SAME = edit(P, "  Point { x: double(n) }\n", "  Point { x: double(n) + 0 }\n")
ORIGIN_BAD = edit(P, "  Point { x: double(n) }\n", "  Point { x: 0 - double(n) }\n")
RENAMED = edit(P, "pub fn alone(n: Int64)", "pub fn lonely(n: Int64)")
NEW_ID = edit(P, '@id("nk000k")', '@id("nk000z")')
POINT_Y = edit(edit(P, '  @id("nk0003") x: Int64,\n}', '  @id("nk0003") x: Int64,\n  @id("nk000n") y: Int64,\n}'),
               "  Point { x: double(n) }\n", "  Point { x: double(n), y: 0 }\n")
ALONE_CALLS = edit(P, "  n + 1\n", "  double(n) + 1\n")
DOUBLE_NEW_ID = edit(P, '@id("nk000c")', '@id("nk000y")')
WEAK_TEST = edit(edit(P, "  Point { x: double(n) }\n", "  Point { x: 0 - double(n) }\n"),
                 'test.expect("x", origin(1).x > 0)', 'test.expect("x", origin(1).x > 0 or true)')
ORIGIN_SIG = edit(edit(P, "pub fn origin(n: Int64) -> Point", "pub fn origin(m: Int64) -> Point"),
                  "  Point { x: double(n) }\n", "  Point { x: double(m) }\n")
RULE_TEXT = edit(P, 'rule positive "итог положителен"', 'rule positive "итог строго положителен"')

ALIAS = '''@id("ab0001")
module app

use std.i64.{add as op, ArithmeticError}

@id("ab0002")
pub fn combine(a: Int64, b: Int64) -> Result<Int64, ArithmeticError> {
  op(a, b)
}

@id("ab0003")
pub fn twice(a: Int64) -> Result<Int64, ArithmeticError> {
  combine(a, a)
}
'''
ALIAS2 = edit(ALIAS, "{add as op,", "{sub as op,")

MIG = '''@id("mg0001")
module app

use std.store

@id("mg0002")
pub type Bad = enum {
  @id("mg0003") Never,
}

@id("mg0004")
pub store S {
  @id("mg0005") table t: Map<String, Int64>
}

@id("mg0006")
pub query get(k: String) -> Option<Int64>
  uses { reads S.t }
{
  store.get(S.t, k)
}

@id("mg0007")
pub query peek(k: String) -> Bool
  uses { reads S.t }
{
  k == ""
}

@id("mg0008")
migration conv on S.t(old: Int64) -> Result<Int64, Bad> {
  Ok(old + 1)
}

@id("mg0009")
pub fn renamed(n: Int64) -> Int64
  supersedes "zz0001"
{
  n
}
'''
MIG2 = edit(MIG, "  Ok(old + 1)\n", "  Ok(old + 2)\n")

CYCLE = '''@id("cy0001")
module app

@id("cy0002")
fn even(n: Int64) -> Bool {
  if n == 0 {
    true
  } else {
    odd(n - 1)
  }
}

@id("cy0003")
fn odd(n: Int64) -> Bool {
  if n == 0 {
    false
  } else {
    even(n - 1)
  }
}

@id("cy0004")
pub fn parity(n: Int64) -> Bool {
  even(n)
}
'''
CYCLE2 = edit(CYCLE, "    false\n", "    1 == 2\n")

REFS = '''@id("rf0001")
module app

@id("rf0002")
fn inc(n: Int64) -> Int64 {
  n + 1
}

@id("rf0003")
fn twice(f: fn(Int64) -> Int64, n: Int64) -> Int64 {
  f(f(n))
}

@id("rf0004")
pub fn run(n: Int64) -> Int64 {
  twice(inc, n)
}
'''
REFS2 = edit(REFS, "  n + 1\n", "  n + 2\n")

CASES = []


def case(area, name, refs, files, links, value, origin="independent", note=None, outcome=None):
    exp = {"phase": area, "outcome": outcome or {"graph": "GRAPH", "impact": "IMPACT", "context": "CONTEXT"}[area]}
    if links.get("op") == "why":
        exp["outcome"] = "WHY"
    if links.get("op") == "relations":
        exp["outcome"] = "RELATIONS"
    if value is not None:
        exp["value"] = value
    CASES.append((area, name, refs, files, links, exp, origin, note))


def pf(cand=None, alt=None, base=P):
    f = {"app.bag": base}
    if cand is not None:
        f["cand/app.bag"] = cand
    if alt is not None:
        f["alt/app.bag"] = alt
    return f


def a(n):
    return "app." + n


EXCL = ["excluded_with_basis", "D83b-no-dependency-path"]

# ============================================================ graph
case("graph", "all-kinds-01", [L2, L3, L4], pf(), {"op": "graph"}, {
    "nodes": sorted([[a("Added"), "event"], [a("Added.name"), "field"], [a("Counting"), "entity"],
                     [a("Exact"), "contract"], [a("Exact.positive"), "rule"], [a("Point"), "type"],
                     [a("Point.x"), "field"], [a("S"), "store"], [a("S.copy"), "table"], [a("S.totals"), "table"],
                     [a("add"), "command"], [a("alone"), "fn"], [a("apply"), "fn"], [a("double"), "fn"],
                     [a("on_added"), "handler"], [a("origin"), "fn"], [a("origin_positive"), "test"],
                     [a("quadruple"), "fn"], [a("total"), "query"], ["app", "module"]]),
    "edges": sorted([
        ["about", a("Exact"), a("Counting")],
        ["calls", a("add"), a("origin")],
        ["calls", a("origin"), a("double")],
        ["calls", a("origin_positive"), a("origin")],
        ["calls", a("origin_positive"), "std:std.test.expect"],
        ["calls", a("quadruple"), a("apply")],
        ["calls", a("quadruple"), a("double")],
        ["checks", a("origin_positive"), a("Exact.positive")],
        ["consumes", a("on_added"), a("Added")],
        ["derived_from", a("S.copy"), a("Counting")],
        ["emits", a("add"), a("Added")],
        ["implements", a("origin"), a("Exact.positive")],
        ["reads", a("on_added"), a("S.totals")],
        ["reads", a("total"), a("S.copy")],
        ["references", a("quadruple"), a("double")],
        ["requires", a("add"), a("Exact.positive")],
        ["uses_type", a("add"), a("Point")],
        ["uses_type", a("on_added"), a("Added")],
        ["uses_type", a("origin"), a("Point")],
        ["uses_type", a("origin_positive"), a("Point")],
        ["writes", a("add"), a("S.totals")],
        ["writes", a("on_added"), a("S.copy")]]),
    "coverage": {k: ("PARTIAL" if k == "supersedes" else "COMPLETE") for k in sorted(
        ["about", "calls", "checks", "consumes", "defines", "derived_from", "emits", "implements", "migrates",
         "reads", "references", "requires", "supersedes", "uses_type", "writes"])},
    "gaps": [[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]], "unused_atoms": []},
    note="вызов через значение fn-типа (apply: f(n)) ребра не даёт: функция-значение уже дала references в quadruple")

case("graph", "relations-01", [L4], pf(), {"op": "relations", "entity": a("double")}, {
    "outgoing": [],
    "incoming": [["calls", a("origin")], ["calls", a("quadruple")], ["defines", "app"], ["references", a("quadruple")]]})

# ============================================================ impact: программа-счётчик
FULL_I1 = [[a("Added"), 3], [a("S"), 4], [a("S.copy"), 5], [a("S.totals"), 3], [a("add"), 2], [a("double"), 0],
           [a("on_added"), 4], [a("origin"), 1], [a("origin_positive"), 2], [a("quadruple"), 1], [a("total"), 6]]
BOTH = ["base", "candidate"]


def report(status="COMPLETE", readiness="ELIGIBLE_IF_ALL_OBLIGATIONS_PASS", seeds=(), in_scope=(), unknown=(),
           unknown_incomplete=0, frontier=(), obligations=(), tests=(), gaps=(), watch=None, closed=()):
    return {"status": status, "readiness": readiness, "seeds": list(seeds), "in_scope": sorted(in_scope),
            "unknown": sorted(unknown), "unknown_incomplete": unknown_incomplete, "frontier": sorted(frontier),
            "obligations": sorted(obligations), "closed": sorted(closed), "tests_to_run": sorted(tests),
            "gaps": sorted(gaps), "watch": watch or {}}


case("impact", "propagation-01", [L5, OUT5], pf(DOUBLE2),
     {"op": "impact", "candidate": "cand", "watch": [a("alone"), a("apply"), a("Point")]},
     report(seeds=[[a("double"), "changed"]], in_scope=FULL_I1,
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]],
            watch={a("alone"): EXCL, a("apply"): EXCL, a("Point"): EXCL}),
     note="вызовы, ссылка на функцию, запись → чтение таблицы, emit → обработчик, таблица → её store")

case("impact", "removed-edge-union-01", [L5], pf(NO_ORIGIN),
     {"op": "impact", "candidate": "cand", "watch": [a("origin")]},
     report(seeds=[[a("add"), "changed"]],
            in_scope=[[a("add"), 0], [a("S.totals"), 1], [a("Added"), 1], [a("S"), 2], [a("on_added"), 2],
                      [a("S.copy"), 3], [a("total"), 4]],
            obligations=[[a("Exact.positive"), a("add"), "requires", "open", ["base"]],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]],
            watch={a("origin"): EXCL}),
     note="requires снят в кандидате, но ребро базы держит обязательство открытым (объединение графов, D12)")

case("impact", "cycle-01", [L5], {"app.bag": CYCLE, "cand/app.bag": CYCLE2}, {"op": "impact", "candidate": "cand"},
     report(readiness="NO_OPEN_OBLIGATIONS", seeds=[[a("odd"), "changed"]],
            in_scope=[[a("odd"), 0], [a("even"), 1], [a("parity"), 2]]),
     note="взаимная рекурсия: обход конечен, каждая сущность обрабатывается один раз")

case("impact", "references-01", [L3, L5], {"app.bag": REFS, "cand/app.bag": REFS2},
     {"op": "impact", "candidate": "cand", "watch": [a("twice")]},
     report(readiness="NO_OPEN_OBLIGATIONS", seeds=[[a("inc"), "changed"]], in_scope=[[a("inc"), 0], [a("run"), 1]],
            watch={a("twice"): EXCL}),
     note="inc вызывается только через значение: влияние идёт по ребру references к run; twice не зависит от inc")

case("impact", "budget-frontier-01", [L5, OUT5], pf(DOUBLE2), {"op": "impact", "candidate": "cand", "budget": 2},
     report(status="INCOMPLETE", readiness="BLOCKED", seeds=[[a("double"), "changed"]],
            in_scope=[[a("double"), 0], [a("origin"), 1]], unknown_incomplete=15,
            frontier=[a("quadruple"), a("add"), a("origin_positive")],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "unknown", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "unknown", BOTH],
                         [a("Counting"), a("Exact"), "about", "unknown", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "unknown", BOTH]],
            tests=[a("origin_positive")]),
     note="два шага: double и origin; достигнутые, но не обработанные — frontier; остальные 15 — unknown (неполный анализ)")

case("impact", "access-unknown-01", [L5, OUT5], pf(DOUBLE2),
     {"op": "impact", "candidate": "cand", "unavailable": [a("add")]},
     report(readiness="BLOCKED", seeds=[[a("double"), "changed"]],
            in_scope=[[a("double"), 0], [a("origin"), 1], [a("quadruple"), 1], [a("origin_positive"), 2]],
            unknown=[[a("add"), "ACCESS_BLOCKED"], [a("S.totals"), "DEPENDS_ON_UNKNOWN"],
                     [a("Added"), "DEPENDS_ON_UNKNOWN"], [a("S"), "DEPENDS_ON_UNKNOWN"],
                     [a("on_added"), "DEPENDS_ON_UNKNOWN"], [a("S.copy"), "DEPENDS_ON_UNKNOWN"],
                     [a("total"), "DEPENDS_ON_UNKNOWN"]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "unknown", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "unknown", BOTH]],
            tests=[a("origin_positive")]),
     note="недоступная сущность — TOP: она и всё, что от неё зависит, unknown; исключения через неё нет")

case("impact", "certificate-interface-01", [L5], pf(ORIGIN_SAME),
     {"op": "impact", "candidate": "cand", "with_tests": True, "watch": [a("add"), a("total")]},
     report(seeds=[[a("origin"), "changed"]], in_scope=[[a("origin"), 0], [a("add"), 1], [a("origin_positive"), 1], [a("S.totals"), 2], [a("Added"), 2],
                      [a("S"), 3], [a("on_added"), 3], [a("S.copy"), 4], [a("total"), 5]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            closed=[[a("Exact.positive"), a("add"), "requires", "D83a-interface-contract"]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]],
            watch={a("add"): "in_scope", a("total"): "in_scope"}),
     note="D83(a) закрывает обязательство add → Exact.positive (провайдер origin: интерфейс и правило те же, прежний "
          "тест проходит), но не отношение: выходы add и всё ниже остаются в области (links/03 §3)")

case("impact", "certificate-needs-pass-01", [L5], pf(ORIGIN_BAD),
     {"op": "impact", "candidate": "cand", "with_tests": True, "watch": [a("add")]},
     report(seeds=[[a("origin"), "changed"]],
            in_scope=[[a("origin"), 0], [a("add"), 1], [a("origin_positive"), 1], [a("S.totals"), 2], [a("Added"), 2],
                      [a("S"), 3], [a("on_added"), 3], [a("S.copy"), 4], [a("total"), 5]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]],
            watch={a("add"): "in_scope"}),
     note="проверка правила на кандидате падает: сертификата нет, зависимость add от origin остаётся")

case("impact", "rename-keeps-id-01", [L2, L5], pf(RENAMED), {"op": "impact", "candidate": "cand"},
     report(readiness="NO_OPEN_OBLIGATIONS", seeds=[[a("lonely"), "changed"]], in_scope=[[a("lonely"), 0]]),
     note="переименование сохраняет EntityId: одна изменённая сущность, а не удаление и создание")

case("impact", "new-id-is-remove-add-01", [L2, L5], pf(NEW_ID), {"op": "impact", "candidate": "cand"},
     report(readiness="NO_OPEN_OBLIGATIONS", seeds=[[a("alone"), "removed"], [a("alone"), "added"]],
            in_scope=[[a("alone"), 0], [a("alone"), 0]]),
     note="смена @id — удаление прежней сущности и создание новой (SURF-07)")

case("impact", "callee-new-id-01", [L2, L5], pf(DOUBLE_NEW_ID), {"op": "impact", "candidate": "cand"},
     report(seeds=[[a("double"), "removed"], [a("origin"), "edge-removed"], [a("quadruple"), "edge-removed"],
                   [a("double"), "added"]],
            in_scope=[[a("double"), 0], [a("double"), 0], [a("origin"), 0], [a("quadruple"), 0], [a("add"), 1],
                      [a("origin_positive"), 1], [a("S.totals"), 2], [a("Added"), 2], [a("S"), 3], [a("on_added"), 3],
                      [a("S.copy"), 4], [a("total"), 5]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]]),
     note="у вызывающих тот же текст, но рёбра ведут к новому ID: они — семена по разнице рёбер (LNK-08-13)")

case("impact", "std-alias-01", [L3, L5], {"app.bag": ALIAS, "cand/app.bag": ALIAS2}, {"op": "impact", "candidate": "cand"},
     report(readiness="NO_OPEN_OBLIGATIONS", seeds=[["app", "changed"], [a("combine"), "edge-removed"]],
            in_scope=[["app", 0], [a("combine"), 0], [a("twice"), 1]]),
     note="подмена импорта std меняет цель ребра calls к std:<имя> — источник становится семенем (ревью m5 H1)")

case("impact", "migrates-01", [L3, L5], {"app.bag": MIG, "cand/app.bag": MIG2}, {"op": "impact", "candidate": "cand"},
     report(readiness="NO_OPEN_OBLIGATIONS", seeds=[[a("conv"), "changed"]],
            in_scope=[[a("conv"), 0], [a("S.t"), 1], [a("S"), 2], [a("get"), 2]],
            gaps=[[a("get"), "EXTERNAL_CONSUMERS"]]),
     note="содержимое таблицы зависит от её миграции; peek объявляет reads, но не читает — ребра нет (EFF-12)")

case("impact", "certificate-weakened-test-01", [L5], pf(WEAK_TEST),
     {"op": "impact", "candidate": "cand", "with_tests": True},
     report(seeds=[[a("origin"), "changed"], [a("origin_positive"), "changed"]],
            in_scope=[[a("origin"), 0], [a("origin_positive"), 0], [a("add"), 1], [a("S.totals"), 2], [a("Added"), 2],
                      [a("S"), 3], [a("on_added"), 3], [a("S.copy"), 4], [a("total"), 5]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]]),
     note="кандидат ослабил свой тест: свидетельство — только прежний тест базы с той же ревизией (ревью m5 H3)")

case("impact", "certificate-sig-changed-01", [L5], pf(ORIGIN_SIG),
     {"op": "impact", "candidate": "cand", "with_tests": True},
     report(seeds=[[a("origin"), "changed"]], in_scope=[[a("origin"), 0], [a("add"), 1], [a("origin_positive"), 1], [a("S.totals"), 2], [a("Added"), 2],
                      [a("S"), 3], [a("on_added"), 3], [a("S.copy"), 4], [a("total"), 5]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]]),
     note="интерфейс провайдера изменился (имя параметра): D83(a) неприменим, обязательство add открыто")

case("impact", "rule-changed-01", [L5], pf(RULE_TEXT), {"op": "impact", "candidate": "cand", "with_tests": True},
     report(seeds=[[a("Exact"), "changed"], [a("Exact.positive"), "changed"]],
            in_scope=[[a("Exact"), 0], [a("Exact.positive"), 0]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("Exact"), "about", "open", BOTH]],
            tests=[a("origin_positive")]),
     note="новый текст правила открывает все его обязательства; код не меняется — распространения по коду нет")

case("impact", "unknown-upgrade-01", [L5], pf(DOUBLE2), {"op": "impact", "candidate": "cand", "unavailable": [a("Point")]},
     report(readiness="BLOCKED", seeds=[[a("double"), "changed"]], in_scope=FULL_I1,
            unknown=[[a("Point"), "ACCESS_BLOCKED"]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]]),
     note="add сначала достигнут через недоступный Point (unknown, расстояние 1), затем через изменённый double "
          "(расстояние 2) — известно затронутое сильнее unknown")

case("impact", "unavailable-unreached-01", [L5], pf(DOUBLE2),
     {"op": "impact", "candidate": "cand", "unavailable": [a("alone")], "watch": [a("alone")]},
     report(readiness="BLOCKED", seeds=[[a("double"), "changed"]], in_scope=FULL_I1,
            unknown=[[a("alone"), "ACCESS_BLOCKED"]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]],
            watch={a("alone"): "unknown"}),
     note="недоступная сущность — unknown, даже если обход до неё не доходит: её нельзя исключить по содержимому (ревью m5 H4)")

case("impact", "type-change-01", [L2, L5], pf(POINT_Y), {"op": "impact", "candidate": "cand"},
     report(seeds=[[a("Point"), "changed"], [a("origin"), "changed"], [a("Point.y"), "added"]],
            in_scope=[[a("Point"), 0], [a("Point.y"), 0], [a("origin"), 0], [a("add"), 1], [a("origin_positive"), 1],
                      [a("S.totals"), 2], [a("Added"), 2], [a("S"), 3], [a("on_added"), 3], [a("S.copy"), 4],
                      [a("total"), 5]],
            obligations=[[a("Exact.positive"), a("origin"), "implements", "open", BOTH],
                         [a("Exact.positive"), a("add"), "requires", "open", BOTH],
                         [a("Exact.positive"), a("origin_positive"), "checks", "open", BOTH],
                         [a("Counting"), a("S.copy"), "derived_from", "open", BOTH]],
            tests=[a("origin_positive")], gaps=[[a("add"), "EXTERNAL_CONSUMERS"], [a("total"), "EXTERNAL_CONSUMERS"]]),
     note="новое поле записи: тип, поле и конструирующая функция — семена; пользователи типа — в области")

case("impact", "why-affected-01", [L5], pf(DOUBLE2),
     {"op": "why", "candidate": "cand", "entity": a("total"), "affected": True},
     {"outcome": "AFFECTED", "status": "in_scope", "path": [
         [a("double"), None, None], [a("origin"), "calls", "base"], [a("add"), "calls", "base"],
         [a("S.totals"), "writes", "base"], [a("on_added"), "reads", "base"], [a("S.copy"), "writes", "base"],
         [a("total"), "reads", "base"]]})

case("impact", "why-excluded-recheck-stale-01", [L5], pf(DOUBLE2, ALONE_CALLS),
     {"op": "why", "candidate": "cand", "entity": a("alone"), "recheck": "alt"},
     {"outcome": "EXCLUDED", "basis": ["D83b-no-dependency-path"], "recheck": ["stale"]},
     note="прежнее основание исключения перепроверяется по другой версии: alone стал вызывать double — stale")

case("impact", "why-excluded-recheck-applicable-01", [L5], pf(DOUBLE2, ALONE_CALLS),
     {"op": "why", "candidate": "cand", "entity": a("apply"), "recheck": "alt"},
     {"outcome": "EXCLUDED", "basis": ["D83b-no-dependency-path"], "recheck": ["applicable"]})

case("impact", "why-excluded-recheck-closure-01", [L5], pf(RENAMED, DOUBLE2),
     {"op": "why", "candidate": "cand", "entity": a("quadruple"), "recheck": "alt"},
     {"outcome": "EXCLUDED", "basis": ["D83b-no-dependency-path"], "recheck": ["stale"]},
     note="текст quadruple тот же, но изменилась его зависимость double: предпосылка-замыкание устарела")

case("graph", "migrates-supersedes-01", [L3, L4], {"app.bag": MIG}, {"op": "graph"}, {
    "nodes": sorted([["app", "module"], [a("Bad"), "type"], [a("Bad.Never"), "variant"], [a("S"), "store"],
                     [a("S.t"), "table"], [a("get"), "query"], [a("peek"), "query"], [a("conv"), "migration"],
                     [a("renamed"), "fn"]]),
    "edges": sorted([["migrates", a("conv"), a("S.t")], ["reads", a("get"), a("S.t")],
                     ["supersedes", a("renamed"), "zz0001"], ["uses_type", a("conv"), a("Bad")]]),
    "coverage": {k: ("PARTIAL" if k == "supersedes" else "COMPLETE") for k in sorted(
        ["about", "calls", "checks", "consumes", "defines", "derived_from", "emits", "implements", "migrates",
         "reads", "references", "requires", "supersedes", "uses_type", "writes"])},
    "gaps": sorted([[a("get"), "EXTERNAL_CONSUMERS"], [a("peek"), "EXTERNAL_CONSUMERS"],
                    [a("renamed"), "SUPERSEDES_HISTORY_UNCHECKED"]]),
    "unused_atoms": [[a("peek"), "reads app.S.t"]]},
    note="supersedes — ребро к строке ID с пробелом до сверки с историей (Ф6); объявленный неиспользуемый атом — запись "
         "unused_atoms, не ребро (EFF-12)")

# ============================================================ context
case("context", "full-01", [L6], pf(DOUBLE2), {"op": "context", "candidate": "cand", "context_budget": 20000},
     {"ready_for_step": True, "blockers": [], "next_cursor": None, "within_budget": True, "obligations": 4,
      "coverage": [[a("double"), "expanded"], [a("Counting"), "expanded"], [a("Exact.positive"), "expanded"],
                   [a("origin"), "expanded"], [a("quadruple"), "expanded"], [a("add"), "expanded"],
                   [a("origin_positive"), "expanded"], [a("S.totals"), "expanded"], [a("Added"), "expanded"],
                   [a("S"), "expanded"], [a("on_added"), "expanded"], [a("S.copy"), "expanded"],
                   [a("total"), "expanded"], [a("Point"), "boundary"], [a("Added.name"), "boundary"],
                   [a("apply"), "boundary"]]},
     note="порядок: семена; цели открытых обязательств; область по (расстоянию, EntityId); границы — исключённые зависимости")

case("context", "blocked-01", [L6], pf(DOUBLE2),
     {"op": "context", "candidate": "cand", "context_budget": 20000, "unavailable": [a("add")]},
     {"ready_for_step": False, "blockers": ["ACCESS_BLOCKED"], "next_cursor": None, "within_budget": True,
      "obligations": 4,
      "coverage": [[a("double"), "expanded"], [a("Exact.positive"), "expanded"], [a("origin"), "expanded"],
                   [a("quadruple"), "expanded"], [a("origin_positive"), "expanded"], [a("Point"), "boundary"],
                   [a("apply"), "boundary"], [a("S"), "pending", "UNKNOWN"], [a("S.totals"), "pending", "UNKNOWN"],
                   [a("S.copy"), "pending", "UNKNOWN"], [a("Added"), "pending", "UNKNOWN"],
                   [a("add"), "blocked", "ACCESS_BLOCKED"], [a("on_added"), "pending", "UNKNOWN"],
                   [a("total"), "pending", "UNKNOWN"]]})

case("context", "incomplete-analysis-01", [L6], pf(DOUBLE2),
     {"op": "context", "candidate": "cand", "context_budget": 20000, "budget": 2},
     {"ready_for_step": False, "blockers": ["ANALYSIS_SCOPE_INCOMPLETE"], "next_cursor": None, "within_budget": True,
      "obligations": 5,
      "coverage": [[a("double"), "expanded"], [a("Exact.positive"), "expanded"], [a("origin"), "expanded"],
                   [a("quadruple"), "pending", "ANALYSIS_FRONTIER"], [a("add"), "pending", "ANALYSIS_FRONTIER"],
                   [a("origin_positive"), "pending", "ANALYSIS_FRONTIER"]]},
     note="неполный анализ (бюджет 2): готовности нет, frontier — pending с действием; границ нет — исключений нет")

case("context", "envelope-too-large-01", [L6], pf(DOUBLE2), {"op": "context", "candidate": "cand", "context_budget": 10},
     None, outcome="REFUSED")


# ============================================================ authorship: сценарии фикстуры
def app_files(**edits):
    out = {}
    for f in sorted(APP.rglob("*.bag")):
        out[f.relative_to(APP).as_posix()] = f.read_text(encoding="utf-8")
    cand = dict(out)
    for rel, fn in edits.items():
        cand[rel.replace("__", "/") + ".bag"] = fn(cand[rel.replace("__", "/") + ".bag"])
    files = dict(out)
    files.update({"cand/" + k: v for k, v in cand.items()})
    return files


def c05(src):
    start, end = src.index('@id("qcp1fw")'), src.index('@id("ae80t2")')
    return src[:start] + '@id("qcp1fw")\npub fn export_article(a: Article, all_people: Map<PersonId, Person>) -> String {\n  "{}"\n}\n\n' + src[end:]


def c08(src):
    src = src.replace("use std.bytes\n", "use std.bytes\nuse std.seq\nuse std.utf8\nuse blog.articles.{Article}\n"
                                         "use blog.authorship\nuse blog.people\n")
    return src.replace('''pub fn image_pipeline(img: Bytes) -> Bytes {
  resize(img, 640, 480)
}''', '''pub fn image_pipeline(img: Bytes, a: Article) -> Bytes {
  watermark(resize(img, 640, 480), a)
}

/// Водяной знак с подписью авторов (C08): вход теперь зависит от авторства.
@id("wmk001")
fn watermark(img: Bytes, a: Article) -> Bytes {
  match seq.get(authorship.ids(a.authors), 0) {
    Some(p) => bytes.concat(img, utf8.encode(people.id_text(p))),
    None => img,
  }
}''')


B = "blog."
C10 = dict(blog__byline=lambda s: edit(s, '" · "', '" / "'))
IDS = dict(blog__authorship=lambda s: edit(s, "    Authors(xs) => xs,", "    Authors(xs) => seq.concat(xs, []),"))
BOTH_A = ["base", "candidate"]
COMPLETE_RULE = B + "authorship.AttributionComplete.complete"
OBL_C11 = sorted([[B + "authorship.AttributionComplete.complete", B + "byline.byline", "requires", "open", BOTH_A]] + [
    [t, s, k, "unknown", BOTH_A] for t, s, k in [
        (B + "authorship.AuthorsShape.nonempty", B + "authorship.make", "implements"),
        (B + "authorship.AuthorsShape.ordered", B + "authorship.make", "implements"),
        (B + "authorship.AuthorsShape.unique", B + "authorship.make", "implements"),
        (B + "authorship.AuthorsShape.existing", B + "authorship.make", "implements"),
        (COMPLETE_RULE, B + "indexer.index_authorship", "implements"),
        (COMPLETE_RULE, B + "search.articles_by", "requires"),
        (COMPLETE_RULE, B + "export.export_article", "requires"),
        (B + "authorship.AuthorsShape.nonempty", B + "editor.set_authors", "requires"),
        (B + "authorship.AuthorsShape.unique", B + "editor.set_authors", "requires"),
        (COMPLETE_RULE, B + "tests.export_keeps_all_authors", "checks"),
        (B + "authorship.AuthorsShape.nonempty", B + "tests.make_enforces_shape", "checks"),
        (B + "authorship.AuthorsShape.unique", B + "tests.make_enforces_shape", "checks"),
        (B + "authorship.Authorship", B + "authorship.AttributionComplete", "about"),
        (B + "authorship.Authorship", B + "authorship.AuthorsShape", "about"),
        (B + "authorship.Authorship", B + "db.Blog.author_index", "derived_from")]])
MAP_NOTE = ("узлы фикстуры → программа: E.byline → blog.byline.byline, E.export → blog.export.export_article, "
            "E.indexer → blog.indexer.index_authorship, E.image_pipeline → blog.image.image_pipeline, "
            "E.image_resize → blog.image.resize, E.image_watermark → blog.image.watermark, O05 → обязательство "
            "(AttributionComplete.complete, export_article); g_export_requires → requires export_article → complete")

case("impact", "authorship-c10-01", [L5], app_files(**C10),
     {"op": "impact", "candidate": "cand",
      "watch": [B + "export.export_article", B + "indexer.index_authorship", B + "image.resize"]},
     report(seeds=[[B + "byline.byline", "changed"]], in_scope=[[B + "byline.byline", 0]],
            obligations=[[COMPLETE_RULE, B + "byline.byline", "requires", "open", BOTH_A]],
            tests=[B + "tests.export_keeps_all_authors"],
            watch={B + "export.export_article": EXCL, B + "indexer.index_authorship": EXCL, B + "image.resize": EXCL}),
     origin=FIX + "#C10", note="смена разделителя подписи; " + MAP_NOTE)

case("impact", "authorship-c05-01", [L5], app_files(blog__export=c05),
     {"op": "impact", "candidate": "cand", "watch": [B + "export.authors_json"]},
     report(seeds=[[B + "export.export_article", "changed"]],
            in_scope=[[B + "export.export_article", 0], [B + "tests.export_keeps_all_authors", 1]],
            obligations=[[COMPLETE_RULE, B + "export.export_article", "requires", "open", ["base"]],
                         [COMPLETE_RULE, B + "tests.export_keeps_all_authors", "checks", "open", BOTH_A]],
            tests=[B + "tests.export_keeps_all_authors"], watch={B + "export.authors_json": EXCL}),
     origin=FIX + "#C05",
     note="экспорт-константа снимает свои рёбра; ребро базы держит O05 открытым, снятие ребра исключения не даёт; " + MAP_NOTE)

case("impact", "authorship-c11-01", [L5, OUT5], app_files(**IDS), {"op": "impact", "candidate": "cand", "budget": 2},
     report(status="INCOMPLETE", readiness="BLOCKED", seeds=[[B + "authorship.ids", "changed"]],
            in_scope=[[B + "authorship.ids", 0], [B + "byline.byline", 1]], unknown_incomplete=89,
            frontier=[B + "authorship.includes", B + "export.export_article", B + "indexer.index_authorship"],
            obligations=OBL_C11, tests=[B + "tests.export_keeps_all_authors"]),
     origin=FIX + "#C11", note="бюджет анализа исчерпан: frontier, обязательства unknown; 94 сущности, 2 в области, 3 во frontier; " + MAP_NOTE)

case("impact", "authorship-c12-01", [L5, OUT5], app_files(**IDS),
     {"op": "impact", "candidate": "cand", "unavailable": [B + "export.export_article"]},
     report(readiness="BLOCKED", seeds=[[B + "authorship.ids", "changed"]],
            in_scope=[[B + "authorship.ids", 0], [B + "byline.byline", 1], [B + "authorship.includes", 1],
                      [B + "indexer.index_authorship", 1], [B + "db.Blog.author_index", 2], [B + "db.Blog", 3],
                      [B + "search.articles_by", 3]],
            unknown=[[B + "export.export_article", "ACCESS_BLOCKED"],
                     [B + "tests.export_keeps_all_authors", "DEPENDS_ON_UNKNOWN"]],
            obligations=[[COMPLETE_RULE, B + "byline.byline", "requires", "open", BOTH_A],
                         [COMPLETE_RULE, B + "search.articles_by", "requires", "open", BOTH_A],
                         [COMPLETE_RULE, B + "indexer.index_authorship", "implements", "open", BOTH_A],
                         [COMPLETE_RULE, B + "export.export_article", "requires", "unknown", BOTH_A],
                         [COMPLETE_RULE, B + "tests.export_keeps_all_authors", "checks", "unknown", BOTH_A],
                         [B + "authorship.Authorship", B + "db.Blog.author_index", "derived_from", "open", BOTH_A]],
            tests=[B + "tests.export_keeps_all_authors"],
            gaps=[[B + "search.articles_by", "EXTERNAL_CONSUMERS"]]),
     origin=FIX + "#C12", note="недоступный экспорт: обязательство O05 unknown, приёмка заблокирована; " + MAP_NOTE)


def c08_files():
    f = app_files(**C10)
    for k, v in app_files(blog__image=c08).items():
        if k.startswith("cand/"):
            f["alt/" + k[5:]] = v
    return f


case("impact", "authorship-c08-pipeline-01", [L5], c08_files(),
     {"op": "why", "candidate": "cand", "entity": B + "image.image_pipeline", "recheck": "alt"},
     {"outcome": "EXCLUDED", "basis": ["D83b-no-dependency-path"], "recheck": ["stale"]},
     origin=FIX + "#C08", note="кэшированное исключение image_pipeline устарело после водяного знака; " + MAP_NOTE)

case("impact", "authorship-c08-resize-01", [L5], c08_files(),
     {"op": "why", "candidate": "cand", "entity": B + "image.resize", "recheck": "alt"},
     {"outcome": "EXCLUDED", "basis": ["D83b-no-dependency-path"], "recheck": ["applicable"]},
     origin=FIX + "#C08", note="внутренности resize остаются исключёнными: предпосылки те же; " + MAP_NOTE)

case("impact", "authorship-c08-scope-01", [L5], app_files(blog__image=c08), {"op": "impact", "candidate": "cand"},
     report(readiness="NO_OPEN_OBLIGATIONS",
            seeds=[[B + "image.image_pipeline", "changed"], [B + "image", "changed"], [B + "image.watermark", "added"]],
            in_scope=[[B + "image", 0], [B + "image.image_pipeline", 0], [B + "image.watermark", 0]]),
     origin=FIX + "#C08", note="в области — конвейер и водяной знак (и заголовок модуля: изменились use); " + MAP_NOTE)

AID = dict(blog__articles=lambda s: edit(s, "  ArticleId(raw)\n", "  ArticleId(raw ++ \"\")\n"))
case("impact", "authorship-test-store-01", [L5], app_files(**AID), {"op": "impact", "candidate": "cand"},
     report(seeds=[[B + "articles.article_id", "changed"]],
            in_scope=[[B + "articles.article_id", 0], [B + "tests.export_keeps_all_authors", 1],
                      [B + "tests.store_copy_is_isolated", 1]],
            obligations=[[COMPLETE_RULE, B + "tests.export_keeps_all_authors", "checks", "open", BOTH_A]],
            tests=[B + "tests.export_keeps_all_authors", B + "tests.store_copy_is_isolated"]),
     note="article_id вызывают только тесты; store_copy_is_isolated пишет в Blog.articles своей копии хранилища "
          "(HST-18) — рабочие таблицы и редактор не затронуты (LNK-08-12)")

MK = dict(blog__authorship=lambda s: edit(s, "  if seq.length(ids) == 0 {", "  if 0 == seq.length(ids) {"))
SHAPE = B + "authorship.AuthorsShape."
case("impact", "authorship-certificate-01", [L5], app_files(**MK),
     {"op": "impact", "candidate": "cand", "with_tests": True, "watch": [B + "editor.set_authors"]},
     report(seeds=[[B + "authorship.make", "changed"]],
            in_scope=[[B + "authorship.make", 0], [B + "editor.set_authors", 1], [B + "tests.export_keeps_all_authors", 1],
                      [B + "tests.make_enforces_shape", 1], [B + "tests.store_copy_is_isolated", 1],
                      [B + "db.Blog.articles", 2], [B + "events.AuthorshipChanged", 2], [B + "db.Blog", 3],
                      [B + "indexer.index_authorship", 3], [B + "db.Blog.author_index", 4], [B + "search.articles_by", 5]],
            obligations=[[SHAPE + r, B + "authorship.make", "implements", "open", BOTH_A]
                         for r in ("nonempty", "ordered", "unique", "existing")] +
                        [[COMPLETE_RULE, B + "indexer.index_authorship", "implements", "open", BOTH_A],
                         [COMPLETE_RULE, B + "search.articles_by", "requires", "open", BOTH_A],
                         [COMPLETE_RULE, B + "tests.export_keeps_all_authors", "checks", "open", BOTH_A],
                         [SHAPE + "nonempty", B + "tests.make_enforces_shape", "checks", "open", BOTH_A],
                         [SHAPE + "unique", B + "tests.make_enforces_shape", "checks", "open", BOTH_A],
                         [B + "authorship.Authorship", B + "db.Blog.author_index", "derived_from", "open", BOTH_A]],
            closed=[[SHAPE + "nonempty", B + "editor.set_authors", "requires", "D83a-interface-contract"],
                    [SHAPE + "unique", B + "editor.set_authors", "requires", "D83a-interface-contract"]],
            tests=[B + "tests.export_keeps_all_authors", B + "tests.make_enforces_shape",
                   B + "tests.store_copy_is_isolated"],
            gaps=[[B + "editor.set_authors", "EXTERNAL_CONSUMERS"], [B + "search.articles_by", "EXTERNAL_CONSUMERS"]],
            watch={B + "editor.set_authors": "in_scope"}),
     note="редактор полагается на nonempty и unique, make их реализует, прежний тест формы проходит и исполняет make — "
          "D83(a) закрывает эти обязательства; complete у search не закрыт: тест complete не исполняет indexer. "
          "Тесты с записью в хранилище рабочие таблицы не связывают (HST-18)")



def main():
    for area in AREAS:
        shutil.rmtree(OUT / area, ignore_errors=True)
    for area, name, refs, files, links, exp, origin, note in CASES:
        d = OUT / area / name
        d.mkdir(parents=True)
        for rel, src in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(src, encoding="utf-8")
        c = {"id": f"{area}/{name}", "spec": refs, "origin": origin, "levels": ["L2"], "files": sorted(files),
             "run": {"links": links}, "expect": exp}
        if note:
            c["note"] = note
        (d / "case.json").write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(CASES)} случаев: " + ", ".join(f"{a} {sum(1 for c in CASES if c[0] == a)}" for a in AREAS))


if __name__ == "__main__":
    main()
