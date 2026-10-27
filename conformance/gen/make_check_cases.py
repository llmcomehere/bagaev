#!/usr/bin/env python3
"""Автор случаев статической проверки (Ф2): области resolve, types, effects.

Ожидания выведены из spec/language/checking.md, surface.md, effects.md и types.md. Диапазон
вычисляется поиском отмеченного фрагмента в исходнике, а не запуском реализации, поэтому
origin = independent. Отрицательный случай содержит одно нарушение; ожидается первая диагностика
по ключу SURF-58. Метка `@@` в исходнике заменяется свежим @id. Повторный запуск перезаписывает
conformance/cases/{resolve,types,effects}/.

  python3 conformance/gen/make_check_cases.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "conformance" / "cases"
AREAS = ("resolve", "types", "effects")
_spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"


def anchor(path: str, heading: str) -> str:
    return f"{path}#{_conf.slug(heading)}"


S2 = anchor("spec/language/surface.md", "2. Файл, модуль, имена")
S3 = anchor("spec/language/surface.md", "3. Объявления и идентичность")
S4 = anchor("spec/language/surface.md", "4. Выражения")
S5 = anchor("spec/language/surface.md", "5. Литералы и числа")
S6 = anchor("spec/language/surface.md", "6. Правила разбора, которые грамматика не выражает")
E1 = anchor("spec/language/effects.md", "1. Атомы")
E2 = anchor("spec/language/effects.md", "2. Ряд эффектов")
E3 = anchor("spec/language/effects.md", "3. Эффект-переменные")
E4 = anchor("spec/language/effects.md", "4. Хранилище, события и точки входа")
T5 = anchor("spec/language/types.md", "5. Специализация и generalization")
T7 = anchor("spec/language/types.md", "7. Синтез и проверка выражений")
T8 = anchor("spec/language/types.md", "8. Полнота Match и типизированные отказы")
T9 = anchor("spec/language/types.md", "9. Eq, Key и Persistable")
C1 = anchor("spec/language/checking.md", "1. Проект")
C2 = anchor("spec/language/checking.md", "2. Встроенные модули std")
C3 = anchor("spec/language/checking.md", "3. Имена и объявления (фаза `resolve`)")
C4 = anchor("spec/language/checking.md", "4. Объявления (фазы `type` и `effect`)")
C5 = anchor("spec/language/checking.md", "5. Тела (фазы `type` и `effect`)")

CASES: list[tuple[str, str, list[str], dict[str, bytes], dict]] = []


def with_ids(case: str, src: str) -> str:
    """Заменить каждую метку @@ свежим @id: 6 символов Crockford base32 из хеша имени случая и номера."""
    out, k = [], 0
    parts = src.split("@@")
    for i, part in enumerate(parts):
        out.append(part)
        if i < len(parts) - 1:
            h = int(hashlib.sha256(f"{case}/{k}".encode()).hexdigest(), 16)
            out.append('@id("' + "".join(CROCKFORD[(h >> (5 * j)) & 31] for j in range(6)) + '")')
            k += 1
    return "".join(out)


def prepare(area: str, name: str, files: dict[str, str]) -> dict[str, bytes]:
    return {f: with_ids(f"{area}/{name}/{f}", src).encode("utf-8") for f, src in files.items()}


def ok(area: str, name: str, refs: list[str], files: dict[str, str], note: str | None = None):
    CASES.append((area, name, refs, prepare(area, name, files), {"phase": "check", "outcome": "ACCEPTED"}, note))


def neg(area: str, name: str, refs: list[str], files: dict[str, str], code: str, file: str, marker: str,
        nth: int = 0, data: dict | None = None, length: int | None = None, skip: int = 0):
    data_files = prepare(area, name, files)
    src = data_files[file]
    m = marker.encode("utf-8")
    i = -1
    for _ in range(nth + 1):
        i = src.index(m, i + 1)
    i += skip
    d = {"code": code, "file": file, "span": [i, i + (len(m) - skip if length is None else length)]}
    if data:
        d["data"] = data
    CASES.append((area, name, refs, data_files, {"phase": "check", "outcome": "PRELAUNCH", "diagnostics": [d]}, None))


def main_mod(body: str, uses: str = "") -> dict[str, str]:
    return {"main.bag": "@@\nmodule main\n" + (uses + "\n" if uses else "") + "\n" + body}


# ====================================================================== resolve
ok("resolve", "namespaces-and-shadowing", [S2, C3], main_mod("""
@@
type Item = record { @@ n: Int64 }

@@
fn Item(n: Int64) -> Item {
  Item { n: n }
}

@@
fn shadow(seq: Int64) -> Int64 {
  let seq = seq + 1;
  seq
}

@@
fn uses_module(xs: Seq<Int64>) -> Int64 {
  seq.length(xs)
}
""", "use std.seq"))

ok("resolve", "imports-group-and-alias", [S2, C3], {
    "lib/people.bag": """@@
module lib.people

@@
pub type PersonId = opaque String

@@
pub fn make(s: String) -> PersonId {
  PersonId(s)
}

@@
pub fn text(p: PersonId) -> String {
  match p {
    PersonId(s) => s,
  }
}
""",
    "main.bag": """@@
module main

use lib.people as ppl
use lib.people.{PersonId as Pid, make}

@@
fn roundtrip(s: String) -> String {
  let p: Pid = make(s);
  ppl.text(p)
}
"""})

neg("resolve", "module-path-mismatch", [S2, C1], {"main.bag": "@@\nmodule other\n"},
    "MODULE_PATH_MISMATCH", "main.bag", "other", data={"module": "other", "path": "main.bag"})

neg("resolve", "unknown-module", [S2, C3], main_mod("", "use nope.deep"), "UNKNOWN_MODULE", "main.bag", "nope.deep",
    data={"name": "nope.deep"})

LIB = {"lib.bag": "@@\nmodule lib\n\n@@\nfn hidden() -> Int64 {\n  1\n}\n\n@@\npub fn open() -> Int64 {\n  2\n}\n"}

neg("resolve", "private-item-in-use", [S2, C3], dict(LIB, **main_mod("", "use lib.{open, hidden}")),
    "PRIVATE_ITEM", "main.bag", "hidden", data={"name": "hidden", "module": "lib"})

neg("resolve", "private-item-in-path", [S2, S3, C3],
    dict(LIB, **main_mod("@@\nfn f() -> Int64 {\n  lib.hidden()\n}\n", "use lib")),
    "PRIVATE_ITEM", "main.bag", "hidden", data={"name": "hidden", "module": "lib"})

neg("resolve", "unknown-name-in-use", [S2, C3], dict(LIB, **main_mod("", "use lib.{absent}")),
    "UNKNOWN_NAME", "main.bag", "absent", data={"name": "absent"})

neg("resolve", "import-cycle", [S2, C3], {
    "a.bag": "@@\nmodule a\n\nuse std.seq\nuse b\n",
    "b.bag": "@@\nmodule b\n\nuse a\n"},
    "MODULE_IMPORT_CYCLE", "a.bag", "b", nth=1, data={"cycle": "a -> b -> a"})

neg("resolve", "duplicate-declaration", [S2, C3],
    main_mod("@@\nfn f() -> Int64 {\n  1\n}\n\n@@\nfn f() -> Int64 {\n  2\n}\n"),
    "DUPLICATE_DECLARATION", "main.bag", "f() -> Int64 {\n  2", length=1, data={"name": "f"})

neg("resolve", "duplicate-with-import", [S2, C3],
    dict(LIB, **main_mod("@@\nfn open() -> Int64 {\n  3\n}\n", "use lib.{open}")),
    "DUPLICATE_DECLARATION", "main.bag", "open", nth=1, data={"name": "open"})

neg("resolve", "duplicate-member", [S2, C3],
    main_mod("@@\ntype P = record {\n  @@ x: Int64,\n  @@ x: Bool,\n}\n"),
    "DUPLICATE_MEMBER", "main.bag", "x: Bool", length=1, data={"name": "x", "decl": "P"})

neg("resolve", "duplicate-parameter", [S3, C3],
    main_mod("@@\nfn f(a: Int64, a: Int64) -> Int64 {\n  a\n}\n"),
    "DUPLICATE_PARAMETER", "main.bag", "a: Int64) ->", length=1, data={"name": "a"})

neg("resolve", "missing-entity-id", [S3, C3], main_mod("fn f() -> Int64 {\n  1\n}\n"),
    "MISSING_ENTITY_ID", "main.bag", "f()", length=1)

neg("resolve", "missing-entity-id-variant", [S3, C3],
    main_mod("@@\ntype E = enum {\n  @@ A,\n  B,\n}\n"), "MISSING_ENTITY_ID", "main.bag", "B")

neg("resolve", "missing-entity-id-module", [S3, C3], {"main.bag": "module main\n"},
    "MISSING_ENTITY_ID", "main.bag", "main")

neg("resolve", "malformed-entity-id", [S3, C3],
    main_mod('@id("ABCDEF")\nfn f() -> Int64 {\n  1\n}\n'), "MALFORMED_ENTITY_ID", "main.bag", '@id("ABCDEF")',
    data={"text": "ABCDEF"})

neg("resolve", "malformed-entity-id-letter-u", [S3, C3],
    main_mod('@id("k3m9qu")\nfn f() -> Int64 {\n  1\n}\n'), "MALFORMED_ENTITY_ID", "main.bag", '@id("k3m9qu")')

neg("resolve", "duplicate-entity-id", [S3, C3], {
    "a.bag": '@id("k3m9qa")\nmodule a\n',
    "b.bag": '@@\nmodule b\n\n@id("k3m9qa")\nfn f() -> Int64 {\n  1\n}\n'},
    "DUPLICATE_ENTITY_ID", "b.bag", '@id("k3m9qa")', data={"id": "k3m9qa"})

neg("resolve", "unknown-attribute", [S3, C3], main_mod('@@\n@doc("x")\nfn f() -> Int64 {\n  1\n}\n'),
    "UNKNOWN_ATTRIBUTE", "main.bag", '@doc("x")', data={"name": "doc"})

neg("resolve", "pub-not-allowed", [S2, S3, C3], main_mod("@@\npub test t {\n  ()\n}\n"),
    "PUB_NOT_ALLOWED", "main.bag", "pub", data={"kind": "test"})

neg("resolve", "unknown-type", [S2, C3], main_mod("@@\nfn f(x: Strin) -> Int64 {\n  1\n}\n"),
    "UNKNOWN_TYPE", "main.bag", "Strin", data={"name": "Strin"})

neg("resolve", "unknown-name", [S2, C3], main_mod("@@\nfn f() -> Int64 {\n  g(1)\n}\n"),
    "UNKNOWN_NAME", "main.bag", "g(", length=1, data={"name": "g"})

neg("resolve", "stdlib-needs-use", [S2, C2, C3], main_mod("@@\nfn f(xs: Seq<Int64>) -> Int64 {\n  seq.length(xs)\n}\n"),
    "UNKNOWN_NAME", "main.bag", "seq.", length=3, data={"name": "seq"})

SHAPE = "@@\ntype Shape = enum {\n  @@ Circle(Int64),\n  @@ Square(Int64),\n}\n\n"

neg("resolve", "unknown-variant", [S2, C3], main_mod(SHAPE + "@@\nfn f() -> Shape {\n  Shape.Triangle(1)\n}\n"),
    "UNKNOWN_VARIANT", "main.bag", "Triangle", data={"type": "main.Shape", "name": "Triangle"})

neg("resolve", "opaque-constructor-outside-module", [S2, S3, C3], {
    "lib.bag": "@@\nmodule lib\n\n@@\npub type Id = opaque String\n",
    "main.bag": "@@\nmodule main\n\nuse lib\n\n@@\nfn f() -> lib.Id {\n  lib.Id(\"x\")\n}\n"},
    "OPAQUE_CONSTRUCTOR_OUTSIDE_MODULE", "main.bag", "lib.Id(", length=6, data={"type": "Id", "module": "lib"})

neg("resolve", "entrypoint-not-callable", [S2, C3],
    main_mod("@@\npub query q() -> Int64 {\n  1\n}\n\n@@\nfn f() -> Int64 {\n  q()\n}\n"),
    "ENTRYPOINT_NOT_CALLABLE", "main.bag", "q()\n}", length=1, data={"name": "q"})

neg("resolve", "irregular-recursive-type", [S3, C3],
    main_mod("@@\ntype Nest<T> = enum {\n  @@ Leaf(T),\n  @@ Deeper(Nest<Seq<T>>),\n}\n"),
    "IRREGULAR_RECURSIVE_TYPE", "main.bag", "Nest<Seq<T>>", data={"type": "Nest"})

ok("resolve", "regular-mutual-recursion", [S3, T9], main_mod("""@@
type List<T> = enum {
  @@ Nil,
  @@ Cons(Node<T>),
}

@@
type Node<T> = record {
  @@ head: T,
  @@ tail: List<T>,
}

@@
fn same(a: List<Int64>, b: List<Int64>) -> Bool {
  a == b
}
"""))

neg("resolve", "invalid-link-target", [S3, C3],
    main_mod("@@\nentity Thing {\n  purpose \"x\"\n}\n\n@@\nfn f() -> Int64\n  implements Thing.rule\n{\n  1\n}\n"),
    "INVALID_LINK_TARGET", "main.bag", "Thing.rule", data={"path": "Thing.rule"})

ok("resolve", "links-to-contract-rules", [S3], main_mod("""@@
entity Thing {
  purpose "x"
}

@@
contract Shape about Thing {
  @@ rule a "первое"
  @@ rule b "второе"
}

@@
fn f() -> Int64
  implements Shape.a, Shape
  requires Thing
{
  1
}

@@
test t
  checks Shape.b
{
  ()
}
"""))

neg("resolve", "float-type-unsupported", [S5, C3], main_mod("@@\nfn f(x: Float) -> () {\n  ()\n}\n"),
    "UNSUPPORTED_FEATURE", "main.bag", "Float", data={"feature_id": "V1-P01"})

neg("resolve", "first-error-by-phase", [S6, C1], {
    "a.bag": "@@\nmodule a\n\n@@\nfn f() -> Int64 {\n  \"не число\"\n}\n",
    "b.bag": "@@\nmodule b\n\n@@\nfn g() -> Int64 {\n  missing\n}\n"},
    "UNKNOWN_NAME", "b.bag", "missing", data={"name": "missing"})

# ====================================================================== types
ok("types", "generics-lambdas-match", [S4, T5, T7, C5], main_mod("""@@
fn twice<T>(x: T, f: fn(T) -> T) -> T {
  f(f(x))
}

@@
fn total(xs: Seq<Int64>) -> Int64 {
  seq.fold(xs, 0, fn(acc, x) => acc + x)
}

@@
fn lengths(xs: Seq<String>) -> Seq<Int64> {
  seq.map(xs, fn(s) => string.scalar_length(s))
}

@@
fn first_or(xs: Seq<Int64>, d: Int64) -> Int64 {
  match seq.get(xs, 0) {
    Some(v) => v,
    None => d,
  }
}

@@
fn parse_sum(a: String, b: String) -> Result<Int64, i64.ParseIntError> {
  let x = i64.parse_decimal(a)?;
  let y = i64.parse_decimal(b)?;
  Ok(twice(x + y, fn(v) => v))
}

@@
fn head(xs: Seq<Int64>) -> Option<Int64> {
  let x = seq.get(xs, 0)?;
  Some(x)
}
""", "use std.seq\nuse std.string\nuse std.i64"))

ok("types", "never-ends-block", [S4, C5], main_mod("""@@
fn early(x: Int64) -> Int64 {
  if x < 0 {
    return 0
  }
  return x;
}
"""), note="D90 (принято 24.10.2026, CHK-13, SURF-23): блок, последний оператор которого — return, имеет тип Never")

ok("types", "records-maps-equality", [S4, T9, C5], main_mod("""@@
type Point = record {
  @@ x: Int64,
  @@ y: Int64,
}

@@
fn moved(p: Point) -> Point {
  Point { ..p, x: p.x + 1 }
}

@@
fn origin(p: Point) -> Bool {
  p == Point { x: 0, y: 0 }
}

@@
fn names() -> Map<Int64, String> {
  Map { 1 => "один", 2 => "два" }
}

@@
fn empty() -> Map<String, Seq<Int64>> {
  Map {}
}
"""))

neg("types", "type-mismatch-let", [S4, T7, C5], main_mod("@@\nfn f() -> () {\n  let s: String = 1;\n}\n"),
    "TYPE_MISMATCH", "main.bag", "1;", length=1, data={"expected": "String", "actual": "Int64"})

neg("types", "type-mismatch-tail", [S4, T7, C5], main_mod("@@\nfn f() -> Bool {\n  42\n}\n"),
    "TYPE_MISMATCH", "main.bag", "42", data={"expected": "Bool", "actual": "Int64"})

neg("types", "type-mismatch-argument", [S4, T7, C5],
    main_mod("@@\nfn g(x: Int64) -> Int64 {\n  x\n}\n\n@@\nfn f() -> Int64 {\n  g(\"7\")\n}\n"),
    "TYPE_MISMATCH", "main.bag", '"7"', data={"expected": "Int64", "actual": "String"})

neg("types", "rigid-type-mismatch", [T5, C5], main_mod("@@\nfn f<T>(x: T) -> Int64 {\n  x\n}\n"),
    "RIGID_TYPE_MISMATCH", "main.bag", "x\n", length=1, data={"param": "T", "actual": "Int64"})

neg("types", "type-arity", [S3, C4], main_mod("@@\nfn f(x: Option<Int64, Int64>) -> () {\n  ()\n}\n"),
    "TYPE_ARITY", "main.bag", "Option<Int64, Int64>", data={"type": "Option", "expected": 1, "actual": 2})

neg("types", "argument-count", [S4, C5],
    main_mod("@@\nfn g(x: Int64) -> Int64 {\n  x\n}\n\n@@\nfn f() -> Int64 {\n  g(1, 2)\n}\n"),
    "ARGUMENT_COUNT", "main.bag", "g(1, 2)", data={"name": "g", "expected": 1, "actual": 2})

neg("types", "function-type-required", [T7, C5], main_mod("@@\nfn f() -> Int64 {\n  let x = 1;\n  x(2)\n}\n"),
    "FUNCTION_TYPE_REQUIRED", "main.bag", "x(2)", length=1)

neg("types", "ambiguous-none", [S4, T5, C5], main_mod("@@\nfn f() -> () {\n  let n = None;\n}\n"),
    "AMBIGUOUS_TYPE_ARGUMENT", "main.bag", "None", data={"param": "T"})

neg("types", "ambiguous-empty-seq", [S4, T5, C5], main_mod("@@\nfn f() -> () {\n  let xs = [];\n}\n"),
    "AMBIGUOUS_TYPE_ARGUMENT", "main.bag", "[]", data={"param": "T"})

neg("types", "parameter-type-required", [S4, T7, C5],
    main_mod("@@\ntype P = record {\n  @@ n: Int64,\n}\n\n@@\nfn f() -> () {\n  let g = fn(p) => p.n;\n}\n"),
    "PARAMETER_TYPE_REQUIRED", "main.bag", "p.n", length=1, data={"name": "p"})

neg("types", "lambda-argument-order", [T7, C5], main_mod("""@@
type P = record {
  @@ n: Int64,
}

@@
fn apply(f: fn(P) -> Int64, xs: Seq<P>) -> Seq<Int64> {
  seq.map(xs, f)
}

@@
fn g<T, U>(f: fn(T) -> U, x: T) -> U {
  f(x)
}

@@
fn h(p: P) -> Int64 {
  g(fn(q) => q.n, p)
}
""", "use std.seq"), "PARAMETER_TYPE_REQUIRED", "main.bag", "q.n", length=1, data={"name": "q"})

neg("types", "not-a-sum-type", [S4, T8, C5],
    main_mod("@@\nfn f(x: Int64) -> Int64 {\n  match x {\n    Some(v) => v,\n  }\n}\n"),
    "NOT_A_SUM_TYPE", "main.bag", "x {", length=1, data={"type": "Int64"})

neg("types", "non-exhaustive-match", [S4, T8, C5],
    main_mod(SHAPE + "@@\nfn f(s: Shape) -> Int64 {\n  match s {\n    Shape.Circle(r) => r,\n  }\n}\n"),
    "NON_EXHAUSTIVE_MATCH", "main.bag", "match", data={"missing": ["Square"]})

neg("types", "duplicate-match-arm", [S4, T8, C5],
    main_mod("@@\nfn f(o: Option<Int64>) -> Int64 {\n  match o {\n    Some(v) => v,\n    None => 0,\n"
             "    Some(w) => w,\n  }\n}\n"),
    "DUPLICATE_MATCH_ARM", "main.bag", "Some(w)", data={"tag": "Some"})

neg("types", "unknown-match-tag", [S4, T8, C5],
    main_mod("@@\nfn f(o: Option<Int64>) -> Int64 {\n  match o {\n    Some(v) => v,\n    None => 0,\n"
             "    Ok(w) => w,\n  }\n}\n"),
    "UNKNOWN_MATCH_TAG", "main.bag", "Ok(w)", data={"tag": "Ok"})

POINT = "@@\ntype Point = record {\n  @@ x: Int64,\n  @@ y: Int64,\n}\n\n"

neg("types", "missing-field", [S4, C5], main_mod(POINT + "@@\nfn f() -> Point {\n  Point { x: 1 }\n}\n"),
    "MISSING_FIELD", "main.bag", "{ x: 1 }", data={"name": "y"})

neg("types", "duplicate-field", [S4, C5],
    main_mod(POINT + "@@\nfn f() -> Point {\n  Point { x: 1, y: 2, x: 3 }\n}\n"),
    "DUPLICATE_FIELD", "main.bag", "x: 3", length=1, data={"name": "x"})

neg("types", "unknown-field", [S4, C5], main_mod(POINT + "@@\nfn f(p: Point) -> Int64 {\n  p.z\n}\n"),
    "UNKNOWN_FIELD", "main.bag", "p.z", skip=2, data={"type": "main.Point", "name": "z"})

neg("types", "bound-eq-function", [S4, T9, C5],
    main_mod("@@\nfn f(g: fn(Int64) -> Int64) -> Bool {\n  g == g\n}\n"),
    "BOUND_NOT_SATISFIED", "main.bag", "g == g", data={"type": "fn(Int64) -> Int64", "bound": "Eq"})

neg("types", "bound-key-map", [S4, T9, C5],
    main_mod("@@\nfn f(a: Map<Int64, Int64>, b: Map<Int64, Int64>) -> Bool {\n  a < b\n}\n"),
    "BOUND_NOT_SATISFIED", "main.bag", "a < b", data={"type": "Map<Int64, Int64>", "bound": "Key"})

neg("types", "bound-generic-call", [T5, T9, C5],
    main_mod("@@\nfn f(g: fn() -> ()) -> Bool {\n  value.equal(g, g)\n}\n", "use std.value"),
    "BOUND_NOT_SATISFIED", "main.bag", "value.equal", data={"bound": "Eq"})

neg("types", "result-discarded", [S6, C5],
    main_mod("@@\nfn f() -> () {\n  i64.add(1, 2);\n}\n", "use std.i64"),
    "RESULT_DISCARDED", "main.bag", "i64.add(1, 2)")

ok("types", "result-explicitly-ignored", [S6], main_mod("@@\nfn f() -> () {\n  let _ = i64.add(1, 2);\n}\n", "use std.i64"))

neg("types", "expected-unit-statement", [S6, C5],
    main_mod("@@\nfn f(b: Bool) -> Int64 {\n  if b {\n    1\n  } else {\n    2\n  }\n  3\n}\n"),
    "EXPECTED_UNIT_STATEMENT", "main.bag", "if b {\n    1\n  } else {\n    2\n  }", data={"actual": "Int64"})

neg("types", "if-without-else-not-unit", [S4, C5],
    main_mod("@@\nfn f(b: Bool) -> () {\n  if b {\n    1\n  }\n}\n"),
    "TYPE_MISMATCH", "main.bag", "1\n", length=1, data={"expected": "()", "actual": "Int64"})

neg("types", "question-mark-context", [S4, C5],
    main_mod("@@\nfn f(o: Option<Int64>) -> Result<Int64, String> {\n  let v = o?;\n  Ok(v)\n}\n"),
    "QUESTION_MARK_CONTEXT", "main.bag", "o?", data={"expected": "Option<_>"})

neg("types", "question-mark-other-error", [S4, C5],
    main_mod("@@\nfn f(s: String) -> Result<Int64, String> {\n  let v = i64.parse_decimal(s)?;\n  Ok(v)\n}\n",
             "use std.i64"),
    "QUESTION_MARK_CONTEXT", "main.bag", "i64.parse_decimal(s)?", data={"expected": "Result<_, std.i64.ParseIntError>"})

neg("types", "concat-needs-sequence", [S4, C5], main_mod("@@\nfn f(a: Int64) -> Int64 {\n  a ++ a\n}\n"),
    "TYPE_MISMATCH", "main.bag", "a ++", length=1, data={"expected": "String | Bytes | Seq<T>", "actual": "Int64"})

neg("types", "concat-same-type", [S4, C5], main_mod("@@\nfn f(a: String, b: Bytes) -> String {\n  a ++ b\n}\n"),
    "TYPE_MISMATCH", "main.bag", "b\n", length=1, data={"expected": "String", "actual": "Bytes"})

neg("types", "duplicate-map-key", [S4, C5], main_mod("@@\nfn f() -> Map<Int64, String> {\n  Map { 1 => \"a\", 2 => \"b\", 1 => \"c\" }\n}\n"),
    "DUPLICATE_MAP_KEY", "main.bag", "1", nth=2, data={"key": "1"})

neg("types", "table-type-not-map", [S3, C4],
    main_mod("@@\nstore S {\n  @@ table t: Seq<Int64>\n}\n"), "TABLE_TYPE_NOT_MAP", "main.bag", "Seq<Int64>",
    data={"name": "t"})

neg("types", "table-value-not-persistable", [S3, T9, C4],
    main_mod("@@\nstore S {\n  @@ table t: Map<Int64, fn() -> ()>\n}\n"), "BOUND_NOT_SATISFIED", "main.bag",
    "Map<Int64, fn() -> ()>", data={"bound": "Persistable"})

neg("types", "command-result-not-result", [S3, C4],
    main_mod("@@\npub command c() -> Int64 {\n  1\n}\n"), "COMMAND_RESULT_NOT_RESULT", "main.bag", "Int64")

neg("types", "event-not-persistable", [S3, C4],
    main_mod("@@\nevent Ev {\n  @@ f: fn() -> (),\n}\n"), "EVENT_NOT_PERSISTABLE", "main.bag", "f:", length=1,
    data={"name": "f"})

neg("types", "migration-type-mismatch", [S3, C4], main_mod("""@@
type V1 = record {
  @@ n: Int64,
}

@@
type V2 = record {
  @@ n: Int64,
  @@ m: Int64,
}

@@
store S {
  @@ table t: Map<Int64, V2>
}

@@
migration up on S.t(old: V1) -> Result<V1, String> {
  Ok(old)
}
"""), "MIGRATION_TYPE_MISMATCH", "main.bag", "Result<V1, String>",
    data={"actual": "Result<main.V1, String>", "table": "S.t", "expected": "main.V2"})

# ====================================================================== effects
STORE = """@@
type Article = record {
  @@ title: String,
}

@@
store Blog {
  @@ table articles: Map<Int64, Article>
}

@@
event Renamed {
  @@ id: Int64,
  @@ title: String,
}

"""

ok("effects", "entrypoints-and-polymorphism", [E1, E2, E3, E4, C5], main_mod(STORE + """@@
fn title_of(id: Int64) -> String
  uses { reads Blog.articles }
{
  match store.get(Blog.articles, id) {
    Some(a) => a.title,
    None => "",
  }
}

@@
fn apply_all<T, U, !e>(xs: Seq<T>, f: fn(T) -> U uses e) -> Seq<U>
  uses e
{
  seq.map(xs, f)
}

@@
pub query titles(ids: Seq<Int64>) -> Seq<String>
  uses { reads Blog.articles }
{
  apply_all(ids, fn(id) => title_of(id))
}

@@
pub command rename(id: Int64, title: String) -> Result<(), String>
  uses { reads Blog.articles, writes Blog.articles, emits Renamed }
{
  match store.get(Blog.articles, id) {
    None => Err("нет статьи"),
    Some(a) => {
      store.put(Blog.articles, id, Article { ..a, title: title });
      emit Renamed { id: id, title: title };
      Ok(())
    },
  }
}

@@
handler on_renamed(ev: Renamed)
  uses { reads Blog.articles }
{
  let _ = title_of(ev.id);
}

@@
test pure_helper {
  test.expect("пусто", seq.length(apply_all([1, 2], fn(x) => x + 1)) == 2)
}
""", "use std.store\nuse std.seq\nuse std.test"))

ok("effects", "store-from-later-module", [E1, C3], {
    "app/api.bag": """@@
module app.api

use std.store
use app.db.{Shop, Ev}

@@
pub query price(name: String) -> Option<Int64>
  uses { reads Shop.items }
{
  store.get(Shop.items, name)
}

@@
pub command touch(name: String) -> Result<(), String>
  uses { emits Ev }
{
  emit Ev { name: name };
  Ok(())
}
""",
    "app/db.bag": """@@
module app.db

@@
pub store Shop {
  @@ table items: Map<String, Int64>
}

@@
pub event Ev {
  @@ name: String,
}
"""})

neg("effects", "undeclared-read", [E1, E2, C5],
    main_mod(STORE + "@@\nfn f(id: Int64) -> Option<Article> {\n  store.get(Blog.articles, id)\n}\n", "use std.store"),
    "UNDECLARED_EFFECT", "main.bag", "store.get(Blog.articles, id)", data={"atoms": ["reads main.Blog.articles"]})

neg("effects", "undeclared-emit", [E1, E2, C5],
    main_mod(STORE + "@@\npub command c() -> Result<(), String> {\n  emit Renamed { id: 1, title: \"t\" };\n  Ok(())\n}\n"),
    "UNDECLARED_EFFECT", "main.bag", 'emit Renamed { id: 1, title: "t" }', data={"atoms": ["emits main.Renamed"]})

neg("effects", "undeclared-through-callee", [E2, C5], main_mod(STORE + """@@
fn read(id: Int64) -> Option<Article>
  uses { reads Blog.articles }
{
  store.get(Blog.articles, id)
}

@@
fn caller() -> Option<Article> {
  read(1)
}
""", "use std.store"), "UNDECLARED_EFFECT", "main.bag", "read(1)", data={"atoms": ["reads main.Blog.articles"]})

neg("effects", "undeclared-through-lambda", [E3, C5], main_mod(STORE + """@@
fn titles(ids: Seq<Int64>) -> Seq<Option<Article>> {
  seq.map(ids, fn(id) => store.get(Blog.articles, id))
}
""", "use std.store\nuse std.seq"), "UNDECLARED_EFFECT", "main.bag", "seq.map(ids, fn(id) => store.get(Blog.articles, id))",
    data={"atoms": ["reads main.Blog.articles"]})

neg("effects", "effect-variable-exact-match", [E3, C5], main_mod(STORE + """@@
fn both<!e>(f: fn() -> () uses e, g: fn() -> () uses e) -> ()
  uses e
{
  f();
  g()
}

@@
fn run(r: fn() -> () uses { reads Blog.articles }, p: fn() -> ()) -> ()
  uses { reads Blog.articles }
{
  both(r, p)
}
"""), "TYPE_MISMATCH", "main.bag", "p)", length=1, data={"expected": "{ reads main.Blog.articles }", "actual": "{}"})

neg("effects", "query-cannot-write", [E4, C4],
    main_mod(STORE + "@@\npub query q() -> ()\n  uses { reads Blog.articles, writes Blog.articles }\n{\n  ()\n}\n"),
    "EFFECT_NOT_ALLOWED_IN_CONTEXT", "main.bag", "writes Blog.articles",
    data={"atom": "writes Blog.articles", "context": "query"})

neg("effects", "migration-is-pure", [E4, C5], main_mod(STORE + """@@
migration up on Blog.articles(old: Article) -> Result<Article, String> {
  match store.get(Blog.articles, 1) {
    Some(a) => Ok(a),
    None => Ok(old),
  }
}
""", "use std.store"), "UNDECLARED_EFFECT", "main.bag", "store.get(Blog.articles, 1)",
    data={"atoms": ["reads main.Blog.articles"]})

neg("effects", "unknown-effect-target", [E1, C4],
    main_mod(STORE + "@@\nfn f() -> ()\n  uses { reads Blog.comments }\n{\n  ()\n}\n"),
    "UNKNOWN_EFFECT_TARGET", "main.bag", "Blog.comments", data={"path": "Blog.comments"})

neg("effects", "emits-not-event", [E1, C4],
    main_mod(STORE + "@@\nfn f() -> ()\n  uses { emits Article }\n{\n  ()\n}\n"),
    "UNKNOWN_EFFECT_TARGET", "main.bag", "Article }", length=7, data={"path": "Article"})

neg("effects", "unknown-host-adapter", [E1, C4],
    main_mod("@@\nfn f() -> ()\n  uses { host clock.now }\n{\n  ()\n}\n"),
    "UNKNOWN_HOST_ADAPTER", "main.bag", "clock.now", data={"name": "clock.now"})

neg("effects", "unknown-effect-variable", [E3, C4],
    main_mod("@@\nfn f(g: fn() -> () uses e) -> () {\n  g()\n}\n"),
    "UNKNOWN_EFFECT_VARIABLE", "main.bag", "e)", length=1, data={"name": "e"})

neg("effects", "table-ref-not-static", [E3, C5], main_mod(STORE + """@@
fn f() -> ()
  uses { reads Blog.articles }
{
  let t = Blog.articles;
}
"""), "TABLE_REF_NOT_STATIC", "main.bag", "Blog.articles;", length=13)

neg("effects", "table-param-only-in-std", [E3, C4],
    main_mod("@@\nfn f(t: Table<Int64, Int64>) -> () {\n  ()\n}\n"),
    "TABLE_PARAM_ONLY_IN_STD", "main.bag", "Table<Int64, Int64>")


# ====================================================================== регрессии ревью m2
neg("types", "never-is-not-expected", [T7, C5], main_mod("@@\nfn f() -> Never {\n  1\n}\n"),
    "TYPE_MISMATCH", "main.bag", "1\n", length=1, data={"expected": "Never", "actual": "Int64"})

OPAQUE = "@@\ntype Cell = opaque Int64\n\n"
neg("types", "opaque-duplicate-arm", [S4, C3], main_mod(OPAQUE + "@@\nfn f(c: Cell) -> Int64 {\n  match c {\n"
                                                         "    Cell(a) => a,\n    Cell(b) => b,\n  }\n}\n"),
    "DUPLICATE_MATCH_ARM", "main.bag", "Cell(b)", data={"tag": "Cell"})
neg("types", "opaque-empty-match", [S4, C3], main_mod(OPAQUE + "@@\nfn f(c: Cell) -> () {\n  match c {}\n}\n"),
    "NON_EXHAUSTIVE_MATCH", "main.bag", "match", data={"missing": ["Cell"]})

neg("resolve", "group-import-skips-private-namesake", [S2, C3], {
    "a.bag": "@@\nmodule a\n\n@@\npub fn X() -> Int64 {\n  1\n}\n\n@@\ntype X = record {\n  @@ secret: Int64,\n}\n",
    "b.bag": "@@\nmodule b\n\nuse a.{X}\n\n@@\nfn f() -> Int64 {\n  let v = X { secret: 5 };\n  1\n}\n"},
    "UNKNOWN_TYPE", "b.bag", "X {", length=1, data={"name": "X"})

neg("resolve", "cycle-of-three", [S2, C3], {
    "a.bag": "@@\nmodule a\n\nuse b\n", "b.bag": "@@\nmodule b\n\nuse c\n", "c.bag": "@@\nmodule c\n\nuse b\nuse a\n"},
    "MODULE_IMPORT_CYCLE", "a.bag", "use b", skip=4, data={"cycle": "a -> b -> c -> a"})

neg("resolve", "std-namespace-reserved", [S2, C1], {"std/seq.bag": "@@\nmodule std.seq\n"},
    "DUPLICATE_DECLARATION", "std/seq.bag", "std.seq", data={"name": "std.seq"})

neg("resolve", "private-contract-in-link", [S3, C3], {
    "a.bag": "@@\nmodule a\n\n@@\npub entity E {\n  purpose \"x\"\n}\n\n@@\ncontract C about E {\n  @@ rule r \"t\"\n}\n",
    "b.bag": "@@\nmodule b\n\nuse a\n\n@@\nfn f() -> Int64\n  implements a.C.r\n{\n  1\n}\n"},
    "PRIVATE_ITEM", "b.bag", "C.r", length=1, data={"name": "C", "module": "a"})

neg("types", "map-key-must-be-key", [T9, C4], main_mod("@@\nfn f(m: Map<fn() -> (), Int64>) -> () {\n  ()\n}\n"),
    "BOUND_NOT_SATISFIED", "main.bag", "Map<fn() -> (), Int64>", data={"bound": "Key"})

neg("types", "type-parameter-bound", [T9, C4],
    main_mod("@@\ntype Box<T: Eq> = record {\n  @@ v: T,\n}\n\n@@\nfn f(b: Box<fn() -> ()>) -> () {\n  ()\n}\n"),
    "BOUND_NOT_SATISFIED", "main.bag", "Box<fn() -> ()>", data={"type": "fn() -> ()", "bound": "Eq"})

neg("types", "and-needs-bool", [S4, C5], main_mod("@@\nfn f(a: Int64) -> Bool {\n  a and true\n}\n"),
    "TYPE_MISMATCH", "main.bag", "a and", length=1, data={"expected": "Bool", "actual": "Int64"})
neg("types", "not-needs-bool", [S4, C5], main_mod("@@\nfn f(a: Int64) -> Bool {\n  not a\n}\n"),
    "TYPE_MISMATCH", "main.bag", "a\n", length=1, data={"expected": "Bool", "actual": "Int64"})
neg("types", "arithmetic-needs-int", [S4, C5], main_mod("@@\nfn f(s: String) -> Int64 {\n  s * 2\n}\n"),
    "TYPE_MISMATCH", "main.bag", "s *", length=1, data={"expected": "Int64", "actual": "String"})

ok("effects", "effect-variable-in-result", [E3, C5], main_mod("""@@
fn wrap<!e>(f: fn() -> Int64 uses e) -> fn() -> Int64 uses e {
  f
}

@@
fn mk<!e>() -> fn() -> Int64 uses e {
  fn() => 1
}

@@
fn g() -> Int64 {
  let h: fn() -> Int64 = wrap(fn() => 1);
  let k: fn() -> Int64 = mk();
  h() + k()
}
"""))

neg("effects", "table-name-misspelled", [E3, S2, C3], main_mod(STORE + """@@
fn f() -> Option<Article>
  uses { reads Blog.articles }
{
  store.get(Blog.artcles, 1)
}
""", "use std.store"), "UNKNOWN_NAME", "main.bag", "artcles", data={"name": "artcles"})

neg("effects", "table-argument-variable", [E3, C5], main_mod(STORE + """@@
fn f(x: Int64) -> Option<Article>
  uses { reads Blog.articles }
{
  store.get(x, 1)
}
""", "use std.store"), "TABLE_REF_NOT_STATIC", "main.bag", "x, 1", length=1)

neg("effects", "private-store-in-row", [E1, S2, C3], {
    "a.bag": "@@\nmodule a\n\n@@\nstore S {\n  @@ table t: Map<Int64, Int64>\n}\n",
    "b.bag": "@@\nmodule b\n\nuse a\n\n@@\nfn f() -> ()\n  uses { reads a.S.t }\n{\n  ()\n}\n"},
    "PRIVATE_ITEM", "b.bag", "S.t", length=1, data={"name": "S", "module": "a"})


def main() -> None:
    for area in AREAS:
        if (OUT / area).exists():
            shutil.rmtree(OUT / area)
    for area, name, refs, files, expect, note in CASES:
        d = OUT / area / name
        for f, data in files.items():
            (d / f).parent.mkdir(parents=True, exist_ok=True)
            (d / f).write_bytes(data)
        case = {"id": f"{area}/{name}", "spec": refs, "origin": "independent", "levels": ["L2"],
                "files": sorted(files), "expect": expect}
        if note:
            case["note"] = note
        (d / "case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {a: sum(1 for c in CASES if c[0] == a) for a in AREAS}
    print(", ".join(f"{a}: {n}" for a, n in counts.items()))


if __name__ == "__main__":
    main()
