#!/usr/bin/env python3
"""Автор случаев канонического формата (Ф2). Ожидаемый текст написан вручную по spec/language/format.md,
а не получен запуском форматтера, поэтому origin = independent. Повторный запуск перезаписывает
conformance/cases/fmt/.

  python3 conformance/gen/make_fmt_cases.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "conformance" / "cases" / "fmt"
_spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)


def anchor(heading: str) -> str:
    return f"spec/language/format.md#{_conf.slug(heading)}"


FILE, DECL, EXPR, COMM, REFUSE = (anchor(h) for h in ("Файл", "Объявления", "Блоки и выражения",
                                                       "Комментарии", "Отказ"))
H = 'module m\n\n'

CASES: list[tuple[str, list[str], bytes, dict]] = []


def ok(name: str, refs: list[str], src: str | bytes, want: str):
    data = src if isinstance(src, bytes) else src.encode("utf-8")
    CASES.append((name, refs, data, {"phase": "fmt", "outcome": "FORMATTED", "value": {"main.bag": want}}))


# FMT-01…03: LF, один перевод строки в конце, без хвостовых пробелов; порядок и пустые строки верхнего уровня.
ok("file-layout", [FILE],
   b'module m\r\n\r\n\r\nuse std.seq\r\n\r\nuse std.map   \r\n@id("aaaaaa")\r\nfn f() -> Int64 { 1 }'
   b'\r\n\r\n\r\n\r\n@id("bbbbbb") fn g() -> Int64 { 2 }',
   'module m\n\nuse std.seq\nuse std.map\n\n'
   '@id("aaaaaa")\nfn f() -> Int64 {\n  1\n}\n\n'
   '@id("bbbbbb")\nfn g() -> Int64 {\n  2\n}\n')

# FMT-04: документирующий комментарий, атрибут на своей строке; у поля — на той же строке.
ok("attrs-and-docs", [DECL],
   H + '/// Точка.\n@id("aaaaaa") pub type T = record { @id("bbbbbb")\n a: Int64, @id("cccccc") b: Bool }\n',
   H + '/// Точка.\n@id("aaaaaa")\npub type T = record {\n  @id("bbbbbb") a: Int64,\n  @id("cccccc") b: Bool,\n}\n')

# FMT-05/06: части сигнатуры на отдельных строках, «{» на своей строке; атомы ряда упорядочены.
ok("signature-clauses", [DECL],
   H + 'fn f(a: Int64) -> Int64 uses { emits E, writes S.t, reads S.u, reads S.t } implements C.r, C.q '
       'requires D.x { a }\n',
   H + 'fn f(a: Int64) -> Int64\n  uses { reads S.t, reads S.u, writes S.t, emits E }\n'
       '  implements C.r, C.q\n  requires D.x\n{\n  a\n}\n')

ok("effect-row-variable", [DECL],
   H + 'fn h<T, !e>(g: fn(T) -> T uses e) -> () uses {host Clock.now, reads S.a | e} { () }\n\n'
       'fn k<!e>(g: fn() -> () uses {| e}) -> () uses e { g() }\n',
   H + 'fn h<T, !e>(g: fn(T) -> T uses e) -> ()\n  uses { reads S.a, host Clock.now | e }\n{\n  ()\n}\n\n'
       'fn k<!e>(g: fn() -> () uses e) -> ()\n  uses e\n{\n  g()\n}\n')

# FMT-05/12: перенос после «(» в параметрах сохраняется; единственный параметр handler — в строку.
ok("broken-params", [DECL, EXPR],
   H + 'fn f(\na: Int64, b: Map<Int64,Bool>) -> Int64 { a }\n\nhandler on_e(\n  e: E) { () }\n',
   H + 'fn f(\n  a: Int64,\n  b: Map<Int64, Bool>,\n) -> Int64 {\n  a\n}\n\nhandler on_e(e: E) {\n  ()\n}\n')

# FMT-07: тела объявлений — по элементу на строке; запятые только после полей и вариантов.
ok("decl-bodies", [DECL],
   H + 'type E = enum { A, B(Int64) }\n'
       'type R = record {}\n'
       'store S { table t: Map<Int64, Bool> table d: Seq<Int64> derived_from X }\n'
       'event Ev { a: Int64 }\n'
       'entity X { purpose "смысл" terms ["a","b"] }\n'
       'contract C about X { rule r "текст" }\n',
   H + 'type E = enum {\n  A,\n  B(Int64),\n}\n\n'
       'type R = record {}\n\n'
       'store S {\n  table t: Map<Int64, Bool>\n  table d: Seq<Int64> derived_from X\n}\n\n'
       'event Ev {\n  a: Int64,\n}\n\n'
       'entity X {\n  purpose "смысл"\n  terms ["a", "b"]\n}\n\n'
       'contract C about X {\n  rule r "текст"\n}\n')

# FMT-08/09: блоки многострочны, пустые строки сжимаются до одной, «;» у блокового оператора сохраняется.
ok("blocks", [EXPR],
   H + 'fn f() -> Int64 { let x: Int64 = 1;\n\n\n  { x }; if x == 1 { 2 } else { 3 }\n  {}\n  x }\n',
   H + 'fn f() -> Int64 {\n  let x: Int64 = 1;\n\n  {\n    x\n  };\n  if x == 1 {\n    2\n  } else {\n    3\n  }\n'
       '  {}\n  x\n}\n')

# FMT-10: else if на одной строке со скобкой; у каждой ветви match запятая, включая ветвь-блок.
ok("if-match", [EXPR],
   H + 'fn f(o: Option<Int64>) -> Int64 {\n  if a { 1 } else if b { 2 } else { 3 };\n'
       '  match o { Some(v) => { v } None => 0 }\n}\n',
   H + 'fn f(o: Option<Int64>) -> Int64 {\n  if a {\n    1\n  } else if b {\n    2\n  } else {\n    3\n  };\n'
       '  match o {\n    Some(v) => {\n      v\n    },\n    None => 0,\n  }\n}\n')

# FMT-11: пробелы вокруг бинарных операторов, унарный минус слитно, скобки выражений сохраняются,
# лишние скобки в типах снимаются, а нужные (функциональный результат перед uses) — ставятся.
ok("spacing", [EXPR],
   H + 'fn f(g: fn(Int64)->((Int64))) -> (fn() -> Int64) uses e {\n'
       '  let y=- x+h( a ,b )?.c*(2) ;\n  let z = not  (a)and b;\n'
       '  let r = T{a:1,..s};\n  let e = T{};\n  let q = [ 1,2 ];\n  let m = Map{1=>2};\n'
       '  emit Ev{a:1};\n  fn( x , y:Int64 )=>x\n}\n',
   H + 'fn f(g: fn(Int64) -> Int64) -> (fn() -> Int64)\n  uses e\n{\n'
       '  let y = -x + h(a, b)?.c * (2);\n  let z = not (a) and b;\n'
       '  let r = T { a: 1, ..s };\n  let e = T {};\n  let q = [1, 2];\n  let m = Map { 1 => 2 };\n'
       '  emit Ev { a: 1 };\n  fn(x, y: Int64) => x\n}\n')

# FMT-12: решение автора о переносе — аргументы, литералы, цепочки операторов.
ok("author-breaks", [EXPR],
   H + 'fn f() -> String {\n  let a = g(\n    1, 2);\n  let b = g(1,\n    2);\n'
       '  let s = [\n1];\n  let r = T {\n a: 1 };\n  "x" ++ y\n    ++ "z" ++\n  w\n}\n',
   H + 'fn f() -> String {\n  let a = g(\n    1,\n    2,\n  );\n  let b = g(1, 2);\n'
       '  let s = [\n    1,\n  ];\n  let r = T {\n    a: 1,\n  };\n  "x" ++ y\n    ++ "z"\n    ++ w\n}\n')

# FMT-13: литералы сохраняют исходное написание.
ok("literals", [EXPR],
   H + 'fn f() -> () {\n  g(0x1F_ff, 1_000, "a\\u{41}\\n", b"\\x00z", -9223372036854775808)\n}\n',
   H + 'fn f() -> () {\n  g(0x1F_ff, 1_000, "a\\u{41}\\n", b"\\x00z", -9223372036854775808)\n}\n')

# FMT-14: комментарии на отдельных строках перед якорем; хвост строки и комментарий внутри выражения —
# перед своим оператором; комментарий перед «}» остаётся внутри блока.
ok("comments", [COMM],
   H + '// о функции\nfn f() -> Int64 { // после скобки\n  let x = g(1, // аргумент\n    2); // хвост\n'
       '  x // хвост хвоста\n  // перед закрытием\n}\n// в конце\n',
   H + '// о функции\nfn f() -> Int64 {\n  // после скобки\n  // аргумент\n  // хвост\n  let x = g(1, 2);\n'
       '  // хвост хвоста\n  x\n  // перед закрытием\n}\n// в конце\n')

# FMT-14 (регрессии ревью m2): комментарий не становится кодом и не удваивается; /// остаётся у своей декларации.
ok("comments-not-code", [COMM, DECL],
   H + 'entity E {\n  // terms ["evil"]\n  purpose "a"\n}\n\ncontract C about E {\n  rule r // пояснение\n    "текст"\n}\n\n'
       'fn a() -> Int64 { - // знак\n 9223372036854775808 } /// о b\nfn b() -> () {}\n',
   H + 'entity E {\n  // terms ["evil"]\n  purpose "a"\n}\n\ncontract C about E {\n  // пояснение\n  rule r "текст"\n}\n\n'
       'fn a() -> Int64 {\n  // знак\n  -9223372036854775808\n}\n\n/// о b\nfn b() -> () {}\n')

# FMT-15: файл с синтаксической ошибкой не форматируется; диагностики — как у bag parse.
src = (H + 'fn f( -> Int64 { 1 }\n').encode("utf-8")
i = src.index(b"->")
CASES.append(("refuse-syntax-error", [REFUSE], src,
              {"phase": "fmt", "outcome": "PRELAUNCH",
               "diagnostics": [{"code": "UNEXPECTED_TOKEN", "file": "main.bag", "span": [i, i + 2]}]}))


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    for name, refs, data, expect in CASES:
        d = OUT / name
        d.mkdir(parents=True)
        (d / "main.bag").write_bytes(data)
        case = {"id": f"fmt/{name}", "spec": refs, "origin": "independent", "levels": ["L2"],
                "files": ["main.bag"], "expect": expect}
        (d / "case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"fmt: {len(CASES)} случаев")


if __name__ == "__main__":
    main()
