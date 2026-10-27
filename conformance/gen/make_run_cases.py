#!/usr/bin/env python3
"""Автор случаев исполнения (Ф3): области l1, eval, data, stdlib, outcomes.

Откуда ожидания:
- l1/core-*: программы фикстуры CORE-0.1 (models/r07-core/fixtures/core-machine.json), переписанные на
  поверхностный синтаксис; трасса — из фикстуры, переименованная по MCH-11 (origin = model:…#id);
- l1/*, eval/*, data/*, outcomes/*: посчитаны вручную по spec/runtime/machine.md (MCH-04…MCH-09),
  surface.md §4 и canonical.md CANON-11 (origin = independent);
- stdlib/*: приёмочные примеры spec/stdlib/acceptance.md (SA-nnn), правила stdlib/types.md §4, векторы
  DATA-0.1 (data-core.json: Unicode и неверный UTF-8, origin = model:…).
Не перенесена программа C15 фикстуры CORE: `match Ok(42) {…}` без контекста — тип ошибки не выводится
(TYPES-0.1 §5), а аннотация меняет трассу; её подмножество проверяет мост conformance/bridges/core01.py.
Метка `@@` заменяется детерминированным @id. Повторный запуск перезаписывает эти области.

  python3 conformance/gen/make_run_cases.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "conformance" / "cases"
AREAS = ("l1", "eval", "data", "stdlib", "outcomes")
FIXTURE = ROOT / "models" / "r07-core" / "fixtures" / "core-machine.json"
_spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"


def anchor(path: str, heading: str) -> str:
    return f"{path}#{_conf.slug(heading)}"


M3 = anchor("spec/runtime/machine.md", "3. Шаг")
M4 = anchor("spec/runtime/machine.md", "4. Закрытый каталог правил")
M5 = anchor("spec/runtime/machine.md", "5. Примитивы и FAULT")
M6 = anchor("spec/runtime/machine.md", "6. Запуск")
M7 = anchor("spec/runtime/machine.md", "7. Соответствие CORE-0.1")
B2 = anchor("spec/ir/bir.md", "2. Формы")
S4 = anchor("spec/language/surface.md", "4. Выражения")
C11 = anchor("spec/kernel/canonical.md", "4. Наблюдаемое значение")
O1 = anchor("spec/kernel/outcomes.md", "1. Исход запуска программы")
SA = "spec/stdlib/acceptance.md"
D6 = anchor("spec/language/data-values.md", "6. Полный порядок Key")

CASES: list = []
CORE_RENAME = {"RESULT_ENTER": "VARIANT_ENTER", "RESULT_WRAP": "VARIANT_WRAP", "MATCH_OK": "MATCH_ARM",
               "MATCH_ERR": "MATCH_ARM"}


def with_ids(tag: str, src: str) -> str:
    out, parts = [], src.split("@@")
    for i, part in enumerate(parts):
        out.append(part)
        if i < len(parts) - 1:
            h = int(hashlib.sha256(f"{tag}/{i}".encode()).hexdigest(), 16)
            out.append('@id("' + "".join(CROCKFORD[(h >> (5 * j)) & 31] for j in range(6)) + '")')
    return "".join(out)


def program(body: str, ret: str, uses: str = "", extra: str = "") -> str:
    head = "@@\nmodule main\n" + (uses + "\n" if uses else "") + "\n"
    return head + extra + f"@@\npub fn main() -> {ret} {{\n{body}\n}}\n"


def case(area, name, refs, src, expect, origin="independent", l1=False, fuel=None, cancel_at=None, entry="main.main",
         note=None, site=None):
    run = {"entry": entry}
    if fuel is not None:
        run["fuel"] = fuel
    if cancel_at is not None:
        run["cancel_at"] = cancel_at
    exp = dict({"phase": "run", "effects": []}, **expect)
    if site is not None:                                # место FAULT — диапазон помеченного фрагмента (MCH-08)
        data = with_ids(f"{area}/{name}", src).encode("utf-8")
        i = data.index(site.encode("utf-8"))
        exp["site"] = {"file": "main.bag", "span": [i, i + len(site.encode("utf-8"))]}
    CASES.append((area, name, refs, src, exp, origin, ["L1", "L2"] if l1 else ["L2"], run, note))


def i64(v):
    return {"type": "Int64", "value": str(v)}


def boolean(v):
    return {"type": "Bool", "value": v}


def string(v):
    return {"type": "String", "value": v}


def tag(t, name, payload=None):
    d = {"type": t, "tag": name}
    if payload is not None:
        d["payload"] = payload
    return d


AE = "std.i64.ArithmeticError"
RES = f"Result<Int64,{AE}>"


def returned(value, trace=None):
    e = {"outcome": "RETURNED", "value": value}
    if trace is not None:
        e["steps"], e["trace_l1"] = len(trace), trace
    return e


# ====================================================================== l1: фикстура CORE-0.1
FIX = {p["id"]: p for p in json.loads(FIXTURE.read_text(encoding="utf-8"))["programs"]}
CORE_SURFACE = {
    "C01": ("7", "Int64", i64(7)),
    "C02": ("  let x: Int64 = 7;\n  x", "Int64", i64(7)),
    "C03": ("  if true {\n    7\n  } else {\n    9\n  }", "Int64", i64(7)),
    "C04": ("  if false {\n    7\n  } else {\n    9\n  }", "Int64", i64(9)),
    "C05": ("  (fn() => 7)()", "Int64", i64(7)),
    "C06": ("  (fn(x: Int64, unused: Int64) => x)(7, 9)", "Int64", i64(7)),
    "C07": (f"  (fn(unused: Result<Int64, i64.ArithmeticError>) => 7)(i64.div(1, 0))", "Int64", i64(7)),
    "C08": ("  let f = fn(x: Int64) => x;\n  f(f(5))", "Int64", i64(5)),
    "C09": ("  let factory = fn(capture: Int64) => fn() => capture;\n  let saved = factory(7);\n"
            "  let other = factory(9);\n  saved()", "Int64", i64(7)),
    "C14": ("  match i64.div(5, 0) {\n    Ok(ok) => i64.ArithmeticError.Overflow,\n    Err(err) => err,\n  }",
            "i64.ArithmeticError", tag(AE, "DivisionByZero")),
    "C16": ("  Ok(Err(i64.ArithmeticError.Overflow))", "Result<Result<Int64, i64.ArithmeticError>, i64.ArithmeticError>",
            tag(f"Result<{RES},{AE}>", "Ok", tag(RES, "Err", tag(AE, "Overflow")))),
    "C17": ("  fn(x: Int64) => x", "fn(Int64) -> Int64", {"type": "Fn"}),
    "C18": ("  ()", "()", {"type": "Unit"}),
    "A01": ("  i64.eq(-2, -2)", "Bool", boolean(True)),
    "A02": ("  i64.lt(-2, 1)", "Bool", boolean(True)),
    "A03": ("  i64.add(9223372036854775807, 1)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Err", tag(AE, "Overflow"))),
    "A04": ("  i64.sub(-9223372036854775808, 1)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Err", tag(AE, "Overflow"))),
    "A05": ("  i64.div(-9223372036854775808, -1)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Err", tag(AE, "Overflow"))),
    "A06": ("  i64.rem(-9223372036854775808, -1)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Ok", i64(0))),
    "A07": ("  i64.div(-7, 3)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Ok", i64(-2))),
    "A08": ("  i64.rem(-7, 3)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Ok", i64(-1))),
    "A09": ("  i64.div(7, -3)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Ok", i64(-2))),
    "A10": ("  i64.rem(7, -3)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Ok", i64(1))),
    "A11": ("  i64.rem(1, 0)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Err", tag(AE, "DivisionByZero"))),
    "A12": ("  i64.add(40, 2)", "Result<Int64, i64.ArithmeticError>", tag(RES, "Ok", i64(42))),
}
for fid, (body, ret, value) in CORE_SURFACE.items():
    trace = [CORE_RENAME.get(r, r) for r, _ in FIX[fid]["expected"]["trace"]]
    case("l1", f"core-{fid.lower()}", [M7, M4], program(body, ret, "use std.i64"), returned(value, trace),
         origin=f"model:models/r07-core/fixtures/core-machine.json#{fid}", l1=True)

# Ограниченные запуски (bounded_matrix фикстуры): исход по порядку MCH-04 из полной трассы фикстуры.
for fid in ("C01", "C06", "C07", "C08", "C14"):
    body, ret, value = CORE_SURFACE[fid]
    full = [CORE_RENAME.get(r, r) for r, _ in FIX[fid]["expected"]["trace"]]
    n = len(full)
    for budget, cancel in dict.fromkeys(((0, None), (n - 1, None), (n, n), (n, 0), (n + 5, n // 2), (n // 2, n // 2))):
        if cancel is not None and cancel <= min(budget, n) and cancel < n:
            exp = {"outcome": "SEMANTIC_STOP", "code": "CANCELLED", "steps": cancel, "trace_l1": full[:cancel]}
        elif budget < n:
            exp = {"outcome": "SEMANTIC_STOP", "code": "BUDGET_EXCEEDED", "steps": budget, "trace_l1": full[:budget]}
        else:
            exp = returned(value, full)
        case("l1", f"core-{fid.lower()}-b{budget}-c{'x' if cancel is None else cancel}", [M7, M3],
             program(body, ret, "use std.i64"), exp, origin="model:models/r07-core/fixtures/core-machine.json#bounded_matrix",
             l1=True, fuel=budget, cancel_at=cancel)

# ====================================================================== l1: новые правила (вручную по MCH-05)
POINT = "@@\ntype Point = record {\n  @@ x: Int64,\n  @@ y: Int64,\n}\n\n"
case("l1", "record-field", [M4, B2], program("  Point { y: 2, x: 1 }.x", "Int64", extra=POINT),
     returned(i64(1), ["FIELD_ENTER", "RECORD_ENTER", "CONST", "RECORD_NEXT", "CONST", "RECORD_BUILD", "FIELD_GET"]), l1=True)
case("l1", "seq-literal", [M4], program("  [1, 2]", "Seq<Int64>"),
     returned({"type": "Seq<Int64>", "items": [i64(1), i64(2)]}, ["SEQ_ENTER", "CONST", "SEQ_NEXT", "CONST", "SEQ_BUILD"]),
     l1=True)
case("l1", "empty-seq", [M4], program("  []", "Seq<Int64>"), returned({"type": "Seq<Int64>", "items": []}, ["SEQ_ENTER"]),
     l1=True)
case("l1", "map-literal", [M4], program("  Map { 1 => 2 }", "Map<Int64, Bool>".replace("Bool", "Int64")),
     returned({"type": "Map<Int64,Int64>", "entries": [[i64(1), i64(2)]]}, ["MAP_ENTER", "CONST", "MAP_NEXT", "CONST", "MAP_BUILD"]),
     l1=True)
case("l1", "return-from-function", [M4, B2],
     program("  f()", "Int64", extra="@@\nfn f() -> Int64 {\n  return 1;\n}\n\n"),
     returned(i64(1), ["CALL_ENTER", "VAR", "CALL_BODY", "LET_ENTER", "RETURN_ENTER", "CONST", "RETURN_EXIT"]), l1=True)
case("l1", "question-mark-option", [M4, B2],
     program("  g()", "Option<Int64>", "use std.seq",
             "@@\nfn g() -> Option<Int64> {\n  let x = seq.get([5], 0)?;\n  Some(x)\n}\n\n"),
     returned(tag("Option<Int64>", "Some", i64(5)),
              ["CALL_ENTER", "VAR", "CALL_BODY", "LET_ENTER", "MATCH_ENTER", "PRIM_ENTER", "SEQ_ENTER", "CONST",
               "SEQ_BUILD", "PRIM_NEXT", "CONST", "PRIM_APPLY", "MATCH_ARM", "VAR", "LET_BIND", "VARIANT_ENTER", "VAR",
               "VARIANT_WRAP"]), l1=True)
case("l1", "and-is-if", [M4, B2], program("  true and false", "Bool"),
     returned(boolean(False), ["IF_ENTER", "CONST", "IF_THEN", "CONST"]), l1=True)
case("l1", "statement-chain", [M4, B2], program("  1;\n  2", "Int64"),
     returned(i64(2), ["LET_ENTER", "CONST", "LET_BIND", "CONST"]), l1=True)
case("l1", "block-without-tail", [M4, B2], program("  1;", "()"),
     returned({"type": "Unit"}, ["LET_ENTER", "CONST", "LET_BIND", "CONST"]), l1=True)
case("l1", "fault-is-charged", [M4, M5], program("  1 / 0", "Int64"),
     {"outcome": "FAULT", "code": "DIVISION_BY_ZERO", "steps": 5,
      "trace_l1": ["PRIM_ENTER", "CONST", "PRIM_NEXT", "CONST", "PRIM_APPLY"]}, l1=True)
case("l1", "opaque-wrap-unwrap", [M4, B2],
     program("  match Id(7) {\n    Id(v) => v,\n  }", "Int64", extra="@@\ntype Id = opaque Int64\n\n"),
     returned(i64(7), ["MATCH_ENTER", "VARIANT_ENTER", "CONST", "VARIANT_WRAP", "MATCH_ARM", "VAR"]), l1=True)

# ====================================================================== eval (L2)
case("eval", "record-update-order", [S4, B2],
     program("  let p = Point { x: 1, y: 2 };\n  let q = Point { ..p, y: 5 };\n  q.x * 10 + q.y", "Int64", extra=POINT),
     returned(i64(15)))
SHAPE = "@@\ntype Shape = enum {\n  @@ Dot,\n  @@ Square(Int64),\n  @@ Rect(Point),\n}\n\n"
case("eval", "enum-match", [S4], program("  area(Shape.Rect(Point { x: 3, y: 4 })) + area(Shape.Square(5)) + area(Shape.Dot)",
                                         "Int64", extra=POINT + SHAPE +
                                         "@@\nfn area(s: Shape) -> Int64 {\n  match s {\n    Shape.Dot => 0,\n"
                                         "    Shape.Square(a) => a * a,\n    Shape.Rect(p) => p.x * p.y,\n  }\n}\n\n"),
     returned(i64(37)))
case("eval", "closure-capture", [S4], program("  let add = fn(a: Int64) => fn(b: Int64) => a + b;\n  let inc = add(1);\n"
                                              "  let add10 = add(10);\n  inc(add10(5))", "Int64"), returned(i64(16)))
case("eval", "recursion", [S4], program("  sum_to(100)", "Int64",
                                        extra="@@\nfn sum_to(n: Int64) -> Int64 {\n  if n == 0 {\n    0\n  } else {\n"
                                              "    n + sum_to(n - 1)\n  }\n}\n\n"), returned(i64(5050)))
case("eval", "mutual-recursion", [S4], program("  is_even(10)", "Bool",
                                               extra="@@\nfn is_even(n: Int64) -> Bool {\n  if n == 0 {\n    true\n  } else {\n"
                                                     "    is_odd(n - 1)\n  }\n}\n\n@@\nfn is_odd(n: Int64) -> Bool {\n"
                                                     "  if n == 0 {\n    false\n  } else {\n    is_even(n - 1)\n  }\n}\n\n"),
     returned(boolean(True)))
case("eval", "question-mark-result", [S4, B2],
     program("  sum(\"40\", \"x\")", "Result<Int64, i64.ParseIntError>", "use std.i64",
             "@@\nfn sum(a: String, b: String) -> Result<Int64, i64.ParseIntError> {\n  let x = i64.parse_decimal(a)?;\n"
             "  let y = i64.parse_decimal(b)?;\n  Ok(x + y)\n}\n\n"),
     returned(tag("Result<Int64,std.i64.ParseIntError>", "Err",
                  tag("std.i64.ParseIntError", "InvalidSyntax",
                      {"type": "std.i64.ParseSyntax", "fields": {"index": i64(0),
                                                                 "reason": tag("std.i64.ParseSyntaxReason", "InvalidDigit")}}))))
case("eval", "return-from-nested-block", [S4], program("  f(3)", "Int64",
                                                       extra="@@\nfn f(n: Int64) -> Int64 {\n  let x = {\n    if n > 2 {\n"
                                                             "      return 100\n    }\n    n\n  };\n  x + 1\n}\n\n"),
     returned(i64(100)))
case("eval", "short-circuit", [S4], program("  false and 1 / 0 == 0", "Bool"), returned(boolean(False)))
case("eval", "argument-order-first-fault", [S4, M5],
     program("  pair(1 / 0, 9223372036854775807 + 1)", "Int64",
             extra="@@\nfn pair(a: Int64, b: Int64) -> Int64 {\n  a\n}\n\n"),
     {"outcome": "FAULT", "code": "DIVISION_BY_ZERO"})
case("eval", "if-without-else", [S4], program("  if false {\n    ()\n  }", "()"), returned({"type": "Unit"}))
case("eval", "higher-order-std", [S4, B2],
     program("  seq.fold(seq.map([1, 2, 3], fn(x) => x * x), 0, fn(acc, x) => acc * 100 + x)", "Int64", "use std.seq"),
     returned(i64(10409)))
case("eval", "map-callback-order", [S4],
     program("  seq.map([\"a\", \"b\"], fn(s) => s ++ \"!\")", "Seq<String>", "use std.seq"),
     returned({"type": "Seq<String>", "items": [string("a!"), string("b!")]}))
case("eval", "shadowing", [S4, B2],
     program("  let x = 1;\n  let x = x + 10;\n  let f = fn(x: Int64) => x * 2;\n  f(x) + x", "Int64"), returned(i64(33)))
case("eval", "return-register", [S4, M4],
     program("  let a = one();\n  a * 100 + f(59)", "Int64",
             extra="@@\nfn one() -> Int64 {\n  return 1;\n}\n\n@@\nfn id(v: Int64) -> Int64 {\n  v\n}\n\n"
                   "@@\nfn f(x: Int64) -> Int64 {\n  let a = id(x);\n  return a + 1;\n}\n\n"), returned(i64(160)))
case("eval", "not-operator", [S4, B2], program("  not (1 > 2) and not false", "Bool"), returned(boolean(True)))
case("eval", "concat-seq", [S4, B2], program("  [1] ++ [2, 3]", "Seq<Int64>"),
     returned({"type": "Seq<Int64>", "items": [i64(1), i64(2), i64(3)]}))
case("eval", "string-concat", [S4], program("  string.scalar_length(\"Привет, \" ++ \"😀\")", "Int64", "use std.string"),
     returned(i64(9)))

# ====================================================================== data (L2)
case("data", "map-entries-in-key-order", [C11, D6], program("  Map { \"b\" => 2, \"a\" => 1, \"ab\" => 3 }", "Map<String, Int64>"),
     returned({"type": "Map<String,Int64>", "entries": [[string("a"), i64(1)], [string("ab"), i64(3)], [string("b"), i64(2)]]}))
case("data", "map-duplicate-key-fault", [S4, M5], program("  Map { 1 => 10, 2 => 20, 0 + 1 => 30 }", "Map<Int64, Int64>"),
     {"outcome": "FAULT", "code": "DUPLICATE_KEY", "data": {"first": 0, "second": 2}})
case("data", "structural-equality", [D6, S4],
     program("  Point { x: 1, y: 2 } == Point { y: 2, x: 1 } and [Some(1), None] == [Some(1), None]"
             " and Map { 1 => \"a\" } == Map { 1 => \"a\" }", "Bool", extra=POINT), returned(boolean(True)))
case("data", "key-order", [D6], program("  false < true and \"Z\" < \"a\" and \"ab\" > \"a\" and [1, 2] < [1, 3] and [1] < [1, 0]"
                                        " and None < Some(-5) and Point { x: 1, y: 9 } < Point { x: 2, y: 0 }", "Bool",
                                        extra=POINT), returned(boolean(True)))
case("data", "bytes-observation", [C11], program("  b\"\\x00\\xff\" ++ b\"A\"", "Bytes"),
     returned({"type": "Bytes", "hex": "00ff41"}))
case("data", "nested-observation", [C11],
     program("  [Shape.Rect(Point { x: 1, y: 2 }), Shape.Dot]", "Seq<Shape>", extra=POINT + SHAPE),
     returned({"type": "Seq<main.Shape>", "items": [
         tag("main.Shape", "Rect", {"type": "main.Point", "fields": {"x": i64(1), "y": i64(2)}}), tag("main.Shape", "Dot")]}))
case("data", "opaque-observation", [C11], program("  Id(\"k\")", "Id", extra="@@\ntype Id = opaque String\n\n"),
     returned({"type": "main.Id", "value": string("k")}))

# ====================================================================== stdlib (L2, acceptance.md)
def sa(name, num, body, ret, value, uses):
    case("stdlib", name, [SA, M5], program(body, ret, uses), returned(value), note=f"SA-{num:03d}")


BOUNDS = "std.data.BoundsError"
sa("i64-eq", 2, "  i64.eq(-9223372036854775808, 9223372036854775807)", "Bool", boolean(False), "use std.i64")
sa("i64-lt", 3, "  i64.lt(-9223372036854775808, 9223372036854775807)", "Bool", boolean(True), "use std.i64")
sa("i64-mul-overflow", 6, "  i64.mul(-9223372036854775808, -1)", "Result<Int64, i64.ArithmeticError>",
   tag(RES, "Err", tag(AE, "Overflow")), "use std.i64")
sa("i64-neg-min", 9, "  i64.neg(-9223372036854775808)", "Result<Int64, i64.ArithmeticError>",
   tag(RES, "Err", tag(AE, "Overflow")), "use std.i64")
sa("i64-parse-syntax-first", 10, "  i64.parse_decimal(\"99999999999999999999x\")", "Result<Int64, i64.ParseIntError>",
   tag("Result<Int64,std.i64.ParseIntError>", "Err", tag("std.i64.ParseIntError", "InvalidSyntax", {
       "type": "std.i64.ParseSyntax", "fields": {"index": i64(20), "reason": tag("std.i64.ParseSyntaxReason", "InvalidDigit")}})),
   "use std.i64")
sa("i64-format-min", 11, "  i64.format_decimal(-9223372036854775808)", "String", string("-9223372036854775808"), "use std.i64")
sa("value-equal-maps", 12, "  let m: Map<Int64, Option<Int64>> = Map { 1 => None };\n  value.equal(m, m)", "Bool",
   boolean(True), "use std.value")
sa("value-compare", 13, "  value.compare(-1, 0)", "Int64", i64(-1), "use std.value")
sa("option-is-some", 14, "  let n: Option<Int64> = None;\n  option.is_some(n)", "Bool", boolean(False), "use std.option")
sa("option-value-or", 15, "  option.value_or(Some(5), 9)", "Int64", i64(5), "use std.option")
sa("result-is-ok", 17, "  let r: Result<String, Int64> = Err(7);\n  result.is_ok(r)", "Bool", boolean(False), "use std.result")
sa("seq-length-empty", 20, "  let xs: Seq<Int64> = [];\n  seq.length(xs)", "Int64", i64(0), "use std.seq")
sa("seq-get-negative", 21, "  seq.get([10, 20], -1)", "Option<Int64>", tag("Option<Int64>", "None"), "use std.seq")
sa("seq-append", 22, "  seq.append([10], 20)", "Seq<Int64>", {"type": "Seq<Int64>", "items": [i64(10), i64(20)]}, "use std.seq")
sa("seq-concat", 23, "  seq.concat([1, 2], [3])", "Seq<Int64>", {"type": "Seq<Int64>", "items": [i64(1), i64(2), i64(3)]},
   "use std.seq")
sa("seq-slice-empty", 24, "  seq.slice([1, 2], 2, 2)", "Result<Seq<Int64>, data.BoundsError>",
   tag(f"Result<Seq<Int64>,{BOUNDS}>", "Ok", {"type": "Seq<Int64>", "items": []}), "use std.seq\nuse std.data")
sa("seq-map-identity", 25, "  seq.map([1, 2], fn(x) => x)", "Seq<Int64>", {"type": "Seq<Int64>", "items": [i64(1), i64(2)]},
   "use std.seq")
sa("seq-fold", 26, "  seq.fold([1, 2], 10, fn(acc, x) => 10 * acc + x)", "Int64", i64(1012), "use std.seq")
DE = "std.data.DataError"
sa("map-build-duplicate", 27, "  map.build([map.Entry { key: 2, value: \"a\" }, map.Entry { key: 1, value: \"b\" },"
   " map.Entry { key: 2, value: \"c\" }])", "Result<Map<Int64, String>, data.DataError>",
   tag(f"Result<Map<Int64,String>,{DE}>", "Err", {"type": DE, "fields": {
       "code": tag("std.data.DataErrorCode", "DuplicateKey"), "first": i64(0), "second": i64(2)}}), "use std.map\nuse std.data")
sa("map-get-absent", 28, "  map.get(Map { 1 => \"a\", 3 => \"c\" }, 2)", "Option<String>", tag("Option<String>", "None"),
   "use std.map")
sa("map-length-empty", 29, "  let m: Map<Int64, Int64> = Map {};\n  map.length(m)", "Int64", i64(0), "use std.map")
sa("map-entries-ordered", 30, "  map.entries(Map { 3 => \"c\", 1 => \"a\" })", "Seq<map.Entry<Int64, String>>",
   {"type": "Seq<std.map.Entry<Int64,String>>", "items": [
       {"type": "std.map.Entry<Int64,String>", "fields": {"key": i64(1), "value": string("a")}},
       {"type": "std.map.Entry<Int64,String>", "fields": {"key": i64(3), "value": string("c")}}]}, "use std.map")
sa("map-put-replace", 31, "  map.put(Map { 1 => \"a\", 3 => \"c\" }, 1, \"new\")", "Map<Int64, String>",
   {"type": "Map<Int64,String>", "entries": [[i64(1), string("new")], [i64(3), string("c")]]}, "use std.map")
sa("map-remove-absent", 32, "  map.remove(Map { 1 => \"a\", 3 => \"c\" }, 2) == Map { 1 => \"a\", 3 => \"c\" }", "Bool",
   boolean(True), "use std.map")
sa("string-scalar-length", 33, "  string.scalar_length(\"😀\")", "Int64", i64(1), "use std.string")
sa("string-scalar-get", 34, "  string.scalar_get(\"A😀\", 1)", "Option<Int64>", tag("Option<Int64>", "Some", i64(128512)),
   "use std.string")
sa("string-slice", 35, "  string.slice(\"A😀B\", 1, 2)", "Result<String, data.BoundsError>",
   tag(f"Result<String,{BOUNDS}>", "Ok", string("😀")), "use std.string\nuse std.data")
sa("string-concat-no-normalization", 36, "  string.scalar_length(string.concat(\"e\", \"\\u{301}\"))", "Int64", i64(2),
   "use std.string")
sa("string-from-scalars-surrogate", 37, "  string.from_scalars([65, 55296, 66])", "Result<String, data.ScalarError>",
   tag("Result<String,std.data.ScalarError>", "Err", {"type": "std.data.ScalarError", "fields": {"index": i64(1), "value": i64(55296)}}),
   "use std.string\nuse std.data")
sa("string-to-scalars", 38, "  string.to_scalars(\"😀\")", "Seq<Int64>", {"type": "Seq<Int64>", "items": [i64(128512)]},
   "use std.string")
sa("bytes-length", 39, "  bytes.length(b\"\\xf0\\x9f\\x98\\x80\")", "Int64", i64(4), "use std.bytes")
sa("bytes-get", 40, "  bytes.get(b\"\\xff\", 0)", "Option<Int64>", tag("Option<Int64>", "Some", i64(255)), "use std.bytes")
sa("bytes-slice", 41, "  bytes.slice(b\"\\xf0\\x9f\\x98\\x80\", 0, 1)", "Result<Bytes, data.BoundsError>",
   tag(f"Result<Bytes,{BOUNDS}>", "Ok", {"type": "Bytes", "hex": "f0"}), "use std.bytes\nuse std.data")
sa("bytes-concat", 42, "  bytes.concat(b\"\\x00\", b\"\\xff\")", "Bytes", {"type": "Bytes", "hex": "00ff"}, "use std.bytes")
sa("bytes-from-octets", 43, "  bytes.from_octets([0, 256, 1])", "Result<Bytes, data.OctetError>",
   tag("Result<Bytes,std.data.OctetError>", "Err", {"type": "std.data.OctetError", "fields": {"index": i64(1), "value": i64(256)}}),
   "use std.bytes\nuse std.data")
sa("bytes-to-octets", 44, "  bytes.to_octets(b\"\\x00\\xff\")", "Seq<Int64>", {"type": "Seq<Int64>", "items": [i64(0), i64(255)]},
   "use std.bytes")
sa("utf8-encode-bom", 45, "  utf8.encode(\"\\u{feff}\")", "Bytes", {"type": "Bytes", "hex": "efbbbf"}, "use std.utf8")
sa("utf8-decode-leading", 46, "  utf8.decode(b\"\\xc0\\x80\")", "Result<String, data.DataError>",
   tag(f"Result<String,{DE}>", "Err", {"type": DE, "fields": {"code": tag("std.data.DataErrorCode", "Utf8Leading"),
                                                              "first": i64(0), "second": i64(-1)}}), "use std.utf8\nuse std.data")
case("stdlib", "seq-slice-bounds-no-clamp", [M5], program("  seq.slice([1, 2], 2, 1)", "Result<Seq<Int64>, data.BoundsError>",
                                                          "use std.seq\nuse std.data"),
     returned(tag(f"Result<Seq<Int64>,{BOUNDS}>", "Err", {"type": BOUNDS, "fields": {"length": i64(2), "start": i64(2), "end": i64(1)}})),
     note="SX-013")
case("stdlib", "json-quote", [M5], program("  json.quote(\"a\\\"b\\\\c\\n\")", "String", "use std.json"),
     returned(string('"a\\"b\\\\c\\u000a"')))

# Векторы DATA-0.1 (models/r07-core/fixtures/data-core.json): Unicode и неверный UTF-8.
DATA = json.loads((ROOT / "models" / "r07-core" / "fixtures" / "data-core.json").read_text(encoding="utf-8"))
for v in DATA["unicode_vectors"]:
    lit = "".join("\\u{%x}" % ord(ch) for ch in v["text"])
    items = [v["scalar_length"], v["byte_length"]] + v["utf8"]
    case("stdlib", f"data-core-{v['id'].lower()}", [M5, SA],
         program(f"  let s = \"{lit}\";\n  let b = utf8.encode(s);\n"
                 "  seq.concat([string.scalar_length(s), bytes.length(b)], bytes.to_octets(b))", "Seq<Int64>",
                 "use std.utf8\nuse std.string\nuse std.bytes\nuse std.seq"),
         returned({"type": "Seq<Int64>", "items": [i64(x) for x in items]}),
         origin=f"model:models/r07-core/fixtures/data-core.json#{v['id']}")
for v in DATA["invalid_utf8_vectors"]:
    lit = "".join("\\x%02x" % x for x in v["bytes"])
    e = v["expected_error"]
    case("stdlib", f"data-core-{v['id'].lower()}", [M5, SA],
         program(f"  utf8.decode(b\"{lit}\")", "Result<String, data.DataError>", "use std.utf8\nuse std.data"),
         returned(tag(f"Result<String,{DE}>", "Err", {"type": DE, "fields": {
             "code": tag("std.data.DataErrorCode", e["code"]), "first": i64(e["first"]), "second": i64(e["second"])}})),
         origin=f"model:models/r07-core/fixtures/data-core.json#{v['id']}")

# Остальные приёмочные примеры: функции высшего порядка и сохранность прежних значений.
sa("option-map-none", 16, "  let n: Option<Int64> = None;\n  option.map(n, fn(x: Int64) => x + 1)", "Option<Int64>",
   tag("Option<Int64>", "None"), "use std.option")
sa("result-map-err", 18, "  let r: Result<Int64, String> = Err(\"e\");\n  result.map(r, fn(x: Int64) => x + 1)",
   "Result<Int64, String>", tag("Result<Int64,String>", "Err", string("e")), "use std.result")
sa("result-map-error-ok", 19, "  let r: Result<Int64, String> = Ok(8);\n  result.map_error(r, fn(e: String) => string.scalar_length(e))",
   "Result<Int64, Int64>", tag("Result<Int64,Int64>", "Ok", i64(8)), "use std.result\nuse std.string")
sa("seq-append-keeps-old", 22, "  let a = [10];\n  let b = seq.append(a, 20);\n  seq.length(a) * 10 + seq.length(b)", "Int64",
   i64(12), "use std.seq")
sa("map-put-keeps-old", 31, "  let m = Map { 1 => \"a\" };\n  let m2 = map.put(m, 1, \"new\");\n  map.get(m, 1)", "Option<String>",
   tag("Option<String>", "Some", string("a")), "use std.map")
case("stdlib", "value-or-default-is-strict", [M5, S4], program("  option.value_or(Some(5), 1 / 0)", "Int64", "use std.option"),
     {"outcome": "FAULT", "code": "DIVISION_BY_ZERO"}, note="SA-015: аргумент по умолчанию вычисляется до вызова")
for s_, idx, reason in (("-", 1, "SignOnly"), ("-01", 2, "LeadingZero"), ("0x", 1, "LeadingZero"), ("+1", 0, "InvalidDigit")):
    case("stdlib", f"parse-decimal-{reason.lower()}-{idx}", [M5, "spec/stdlib/types.md"],
         program(f"  i64.parse_decimal(\"{s_}\")", "Result<Int64, i64.ParseIntError>", "use std.i64"),
         returned(tag("Result<Int64,std.i64.ParseIntError>", "Err", tag("std.i64.ParseIntError", "InvalidSyntax", {
             "type": "std.i64.ParseSyntax", "fields": {"index": i64(idx), "reason": tag("std.i64.ParseSyntaxReason", reason)}}))),
         note="stdlib/types.md §4")

# ====================================================================== outcomes (L2)
case("outcomes", "overflow-fault-site", [M5, O1], program("  9223372036854775807 + 1", "Int64"),
     {"outcome": "FAULT", "code": "ARITHMETIC_OVERFLOW"}, site="9223372036854775807 + 1")
case("outcomes", "remainder-by-zero", [M5], program("  7 % 0", "Int64"), {"outcome": "FAULT", "code": "DIVISION_BY_ZERO"})
case("outcomes", "min-div-minus-one", [M5], program("  -9223372036854775808 / -1", "Int64"),
     {"outcome": "FAULT", "code": "ARITHMETIC_OVERFLOW"})
case("outcomes", "min-rem-minus-one", [M5, S4], program("  -9223372036854775808 % -1", "Int64"), returned(i64(0)))
case("outcomes", "remainder-sign", [M5, S4], program("  (-7 % 3) * 10 + 7 % -3", "Int64"), returned(i64(-9)))
case("outcomes", "budget-exceeded", [M3, O1], program("  spin(0)", "Int64",
                                                      extra="@@\nfn spin(n: Int64) -> Int64 {\n  spin(n)\n}\n\n"),
     {"outcome": "SEMANTIC_STOP", "code": "BUDGET_EXCEEDED"}, fuel=1000)
case("outcomes", "test-assertion-fault", [M5, O1], program("  test.expect(\"нужно true\", 1 > 2)", "()", "use std.test"),
     {"outcome": "FAULT", "code": "TEST_ASSERTION", "data": {"label": "нужно true"}})
case("outcomes", "codec-not-implemented", [M5, O1], program("  codec.encode(1)", "Bytes", "use std.codec"),
     {"outcome": "IMPLEMENTATION_STOP", "code": "NOT_IMPLEMENTED"})
case("outcomes", "unknown-entrypoint", [M6], program("  1", "Int64"),
     {"outcome": "PRELAUNCH", "diagnostics": [{"code": "UNKNOWN_ENTRYPOINT"}]}, entry="main.absent")
case("outcomes", "entrypoint-signature", [M6], program("  1", "Int64", extra="@@\npub fn f(x: Int64) -> Int64 {\n  x\n}\n\n"),
     {"outcome": "PRELAUNCH", "diagnostics": [{"code": "ENTRYPOINT_SIGNATURE"}]}, entry="main.f")
case("outcomes", "effects-outside-transaction", [M6],
     "@@\nmodule main\n\nuse std.store\n\n@@\nstore S {\n  @@ table t: Map<Int64, Int64>\n}\n\n"
     "@@\npub fn main() -> Option<Int64>\n  uses { reads S.t }\n{\n  store.get(S.t, 1)\n}\n",
     {"outcome": "PRELAUNCH", "diagnostics": [{"code": "HOST_EFFECT_OUTSIDE_TRANSACTION"}]})
case("outcomes", "check-errors-prelaunch", [O1], program("  undefined", "Int64"),
     {"outcome": "PRELAUNCH", "diagnostics": [{"code": "UNKNOWN_NAME"}]})


def main() -> None:
    for area in AREAS:
        if (OUT / area).exists():
            shutil.rmtree(OUT / area)
    for area, name, refs, src, expect, origin, levels, run, note in CASES:
        d = OUT / area / name
        d.mkdir(parents=True)
        (d / "main.bag").write_bytes(with_ids(f"{area}/{name}", src).encode("utf-8"))
        c = {"id": f"{area}/{name}", "spec": refs, "origin": origin, "levels": levels, "files": ["main.bag"],
             "run": run, "expect": expect}
        if note:
            c["note"] = note
        (d / "case.json").write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {a: sum(1 for c in CASES if c[0] == a) for a in AREAS}
    print(", ".join(f"{a}: {n}" for a, n in counts.items()))


if __name__ == "__main__":
    main()
