#!/usr/bin/env python3
"""Автор случаев лексики и разбора (Ф1). Ожидания выводятся из lexical.md / surface.md / grammar.ebnf:
диапазон вычисляется поиском отмеченного фрагмента в исходнике, а не запуском реализации, поэтому
origin = independent. Повторный запуск перезаписывает conformance/cases/{lex,parse}/.

  python3 conformance/gen/make_lexparse_cases.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "conformance" / "cases"
_spec = importlib.util.spec_from_file_location("bagaev_conformance", ROOT / "conformance" / "run.py")
_conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_conf)


def anchor(path: str, heading: str) -> str:
    return f"{path}#{_conf.slug(heading)}"


LEX1 = anchor("spec/language/lexical.md", "1. Кодировка и символы")
LEX3 = anchor("spec/language/lexical.md", "3. Идентификаторы и ключевые слова")
LEX4 = anchor("spec/language/lexical.md", "4. Литералы")
LEX5 = anchor("spec/language/lexical.md", "5. Пунктуация и операторы")
LEX2 = anchor("spec/language/lexical.md", "2. Пробелы и комментарии")
LEX6 = anchor("spec/language/lexical.md", "6. Координаты")
SURF6 = anchor("spec/language/surface.md", "6. Правила разбора, которые грамматика не выражает")
SURF2 = anchor("spec/language/surface.md", "2. Файл, модуль, имена")
GRAM = "spec/language/grammar.ebnf"
HEAD = b"module m\n"


def span(src: bytes, marker: bytes, nth: int = 0, empty_after: bool = False) -> list[int]:
    i = -1
    for _ in range(nth + 1):
        i = src.index(marker, i + 1)
    return [i + len(marker), i + len(marker)] if empty_after else [i, i + len(marker)]


CASES: list[tuple[str, str, list[str], bytes, dict]] = []


def neg(area, name, refs, src, code, marker=None, nth=0, empty_after=False, data=None):
    d = {"code": code, "file": "main.bag"}
    if marker is not None:
        d["span"] = span(src, marker, nth, empty_after)
    if data:
        d["data"] = data
    CASES.append((area, name, refs, src, {"phase": "parse", "outcome": "PRELAUNCH", "diagnostics": [d]}))


def pos(area, name, refs, src):
    CASES.append((area, name, refs, src, {"phase": "parse", "outcome": "ACCEPTED"}))


# ---------------------------------------------------------------- лексика, отказы
neg("lex", "bom", [LEX1, LEX6], b"\xef\xbb\xbf" + HEAD, "SOURCE_BOM", b"\xef\xbb\xbf")
neg("lex", "invalid-utf8", [LEX1], HEAD + b"// \xff\n", "INVALID_UTF8", b"\xff")
neg("lex", "not-nfc", [LEX1], HEAD + "fn f() -> String { \"e\u0301\" }\n".encode(), "SOURCE_NOT_NFC", "e\u0301".encode())
neg("lex", "forbidden-control", [LEX1], HEAD + b"fn f() -> Int64 {\x07 1 }\n", "FORBIDDEN_CHARACTER", b"\x07")
neg("lex", "bidi-in-string", [LEX1], HEAD + "fn f() -> String { \"a\u202eb\" }\n".encode(),
    "BIDI_CONTROL_IN_SOURCE", "\u202e".encode())
neg("lex", "bidi-in-comment", [LEX1, LEX2], "// \u2066 x\n".encode() + HEAD, "BIDI_CONTROL_IN_SOURCE", "\u2066".encode())
neg("lex", "stray-cr", [LEX1], b"module m\rfn f() -> Int64 { 1 }\n", "STRAY_CR", b"\r")
neg("lex", "unterminated-string", [LEX4], HEAD + b"fn f() -> String { \"abc\n}\n", "UNTERMINATED_STRING", b"\"abc")
neg("lex", "invalid-escape", [LEX4], HEAD + b"fn f() -> String { \"a\\qb\" }\n", "INVALID_ESCAPE", b"\\q")
neg("lex", "surrogate-escape", [LEX4], HEAD + b"fn f() -> String { \"\\u{D800}\" }\n", "INVALID_ESCAPE", b"\\u{D800}")
neg("lex", "bytes-non-ascii", [LEX4], HEAD + "fn f() -> Bytes { b\"я\" }\n".encode(), "INVALID_BYTE_LITERAL", "я".encode())
neg("lex", "double-underscore", [LEX4], HEAD + b"fn f() -> Int64 { 1__0 }\n", "MALFORMED_NUMBER", b"1__0")
neg("lex", "trailing-underscore", [LEX4], HEAD + b"fn f() -> Int64 { 10_ }\n", "MALFORMED_NUMBER", b"10_")
neg("lex", "leading-zero", [LEX4], HEAD + b"fn f() -> Int64 { 007 }\n", "LEADING_ZERO", b"007")
neg("lex", "int-out-of-range", [LEX4], HEAD + b"fn f() -> Int64 { 9223372036854775808 }\n",
    "INT_LITERAL_OUT_OF_RANGE", b"9223372036854775808")
neg("lex", "float-literal", [LEX4], HEAD + b"fn f() -> Int64 { 1.5 }\n", "UNSUPPORTED_FEATURE", b"1.5",
    data={"feature_id": "V1-P01"})
neg("lex", "unexpected-character", [LEX5], HEAD + b"fn f() -> Int64 { $ }\n", "UNEXPECTED_CHARACTER", b"$")

neg("lex", "nbsp-outside-string", [LEX1], HEAD + "fn f() -> Int64 {\u00a01 }\n".encode(), "FORBIDDEN_CHARACTER", "\u00a0".encode())
neg("lex", "control-in-string", [LEX1, LEX4], HEAD + b"fn f() -> String { \"a\x01b\" }\n", "FORBIDDEN_CHARACTER", b"\x01")
neg("lex", "control-in-bytes", [LEX1, LEX4], HEAD + b"fn f() -> Bytes { b\"a\x7fb\" }\n", "FORBIDDEN_CHARACTER", b"\x7f")
neg("lex", "line-separator-in-comment", [LEX1, LEX2], HEAD + "// a\u2028b\n".encode(), "FORBIDDEN_CHARACTER", "\u2028".encode())
neg("lex", "stray-cr-in-comment", [LEX1, LEX2], HEAD + b"// a\rb\n", "STRAY_CR", b"\r")
neg("lex", "non-ascii-digit", [LEX4], HEAD + "fn f() -> Int64 { \u0663 }\n".encode(), "UNEXPECTED_CHARACTER", "\u0663".encode())
neg("lex", "superscript-after-name", [LEX3], HEAD + "fn f(x: Int64) -> Int64 { x\u00b2 }\n".encode(), "UNEXPECTED_CHARACTER", "\u00b2".encode())
neg("lex", "number-then-letters", [LEX4], HEAD + b"fn f() -> Int64 { 123abc }\n", "MALFORMED_NUMBER", b"123abc")
neg("lex", "zero-underscore", [LEX4], HEAD + b"fn f() -> Int64 { 0_1 }\n", "LEADING_ZERO", b"0_1")
neg("lex", "escape-too-long", [LEX4], HEAD + b"fn f() -> String { \"\\u{1234567}\" }\n", "INVALID_ESCAPE", b"\\u{1234567}")
neg("lex", "first-error-by-offset", [LEX1, LEX6], HEAD + "fn f() -> String { \"\u202e\" } // e\u0301\n".encode(),
    "BIDI_CONTROL_IN_SOURCE", "\u202e".encode())
neg("parse", "min-after-binary-minus", [LEX4], HEAD + b"fn f(x: Int64) -> Int64 { x - 9223372036854775808 }\n",
    "INT_LITERAL_OUT_OF_RANGE", b"9223372036854775808")
neg("lex", "literal-above-min", [LEX4], HEAD + b"fn f() -> Int64 { -9223372036854775809 }\n", "INT_LITERAL_OUT_OF_RANGE", b"9223372036854775809")

# ---------------------------------------------------------------- лексика, допустимое
pos("lex", "min-int", [LEX4], HEAD + b"fn f() -> Int64 { -9223372036854775808 }\n")
pos("lex", "hex-underscore", [LEX4], HEAD + b"fn f() -> Int64 { 0x7fff_ffff }\n")
pos("lex", "hex-min", [LEX4], HEAD + b"fn f() -> Int64 { -0x8000_0000_0000_0000 }\n")
pos("lex", "format-chars-in-string", [LEX1, LEX4], HEAD + "fn f() -> String { \"a\u00a0b\u200bc\" }\n".encode())
pos("lex", "unicode-identifier", [LEX3], HEAD + "fn сумма(имя: Int64) -> Int64 { let итог = имя; итог }\n".encode())
pos("lex", "string-escapes", [LEX4], HEAD + b"fn f() -> String { \"\\n\\t\\r\\0\\\\\\\"\\u{1F600}\" }\n")
pos("lex", "bytes-escapes", [LEX4], HEAD + b"fn f() -> Bytes { b\"ab\\x00\\xff\\n\" }\n")
pos("lex", "comments", [LEX2], b"// \xd0\xbe\xd0\xb1\xd1\x8b\xd1\x87\xd0\xbd\xd1\x8b\xd0\xb9\n/// doc\n" + HEAD
    + b"/// \xd0\xbe \xd1\x84\xd1\x83\xd0\xbd\xd0\xba\xd1\x86\xd0\xb8\xd0\xb8\nfn f() -> Int64 { 1 } // \xd1\x85\xd0\xb2\xd0\xbe\xd1\x81\xd1\x82\n")
pos("lex", "crlf", [LEX1], b"module m\r\nfn f() -> Int64 {\r\n  1\r\n}\r\n")
pos("lex", "contextual-words-as-names", [LEX3],
    HEAD + b"fn f(table: Int64, type: Int64, test: Int64) -> Int64 { let query = table + type; query + test }\n")

# ---------------------------------------------------------------- разбор, отказы
neg("parse", "unexpected-token", [GRAM, SURF6], HEAD + b"fn f() -> Int64 { 1 + }\n", "UNEXPECTED_TOKEN", b"}", nth=0)
neg("parse", "unexpected-eof", [GRAM, SURF6], HEAD + b"fn f() -> Int64 { 1", "UNEXPECTED_EOF", b"{ 1", empty_after=True)
neg("lex", "stray-cr-in-string", [LEX1, LEX4], HEAD + b'fn f() -> String { "a\rb" }\n', "STRAY_CR", b"\r")
neg("lex", "private-use-character", [LEX1], HEAD + "fn f() -> Int64 { \ue000 1 }\n".encode(), "UNEXPECTED_CHARACTER",
    "\ue000".encode())
neg("parse", "empty-enum", [GRAM, SURF6], HEAD + b"type E = enum {}\n", "UNEXPECTED_TOKEN", b"}")
neg("parse", "empty-attribute-arguments", [GRAM], b"@id()\n" + HEAD, "UNEXPECTED_TOKEN", b")")
neg("parse", "empty-use-group", [GRAM, SURF2], HEAD + b"use a.{}\n", "UNEXPECTED_TOKEN", b"}")
neg("parse", "empty-generics", [GRAM], HEAD + b"fn f<>() -> () {}\n", "UNEXPECTED_TOKEN", b">")
neg("parse", "empty-type-arguments", [GRAM], HEAD + b"fn f(x: Option<>) -> () {}\n", "UNEXPECTED_TOKEN", b">")
neg("parse", "effect-parameter-in-type", [GRAM], HEAD + b"type R<!e> = record { f: Int64 }\n", "UNEXPECTED_TOKEN", b"!")
neg("parse", "record-literal-not-after-path", [SURF6], HEAD + b"fn f() -> () {\n  let x = g() { a: 1 };\n}\n",
    "RECORD_LITERAL_NOT_AFTER_PATH", b"{", nth=1)
neg("parse", "mixed-record-entries", [SURF6], HEAD + b"fn f() -> () {\n  let x = T { a: 1, 2 => 3 };\n}\n",
    "MIXED_RECORD_ENTRIES", b"2 => 3")
neg("parse", "record-update-without-fields", [SURF6], HEAD + b"fn f(p: P) -> P {\n  P { ..p }\n}\n",
    "RECORD_UPDATE_WITHOUT_FIELDS", b"..p")
neg("parse", "true-is-reserved", [LEX4, LEX3], HEAD + b"fn f() -> Int64 {\n  let true = 1;\n  1\n}\n",
    "RESERVED_WORD_AS_NAME", b"true")
pos("parse", "unit-is-two-tokens", [LEX4], HEAD + b"fn f() -> ( ) {\n  ( )\n}\n")
neg("parse", "reserved-word-as-name", [LEX3, SURF6], HEAD + b"fn f() -> Int64 { let match = 1; 2 }\n",
    "RESERVED_WORD_AS_NAME", b"match")
neg("parse", "mixed-and-or", [SURF6], HEAD + b"fn f(a: Bool, b: Bool, c: Bool) -> Bool { a and b or c }\n",
    "MIXED_AND_OR", b"or")
neg("parse", "nonassoc-comparison", [SURF6], HEAD + b"fn f(a: Int64, b: Int64, c: Int64) -> Bool { a < b < c }\n",
    "NONASSOC_COMPARISON", b"<", nth=1)
neg("parse", "missing-comma-in-match", [SURF6],
    HEAD + b"fn f(x: Option<Int64>) -> Int64 { match x { Some(v) => v None => 0 } }\n",
    "MISSING_COMMA_IN_MATCH", b"=> v", empty_after=True)
neg("parse", "record-literal-in-condition", [SURF6],
    HEAD + b"fn f(p: Point) -> Int64 { if p == Point { x: 0 } { 1 } else { 2 } }\n",
    "RECORD_LITERAL_IN_CONDITION", b"{", nth=1)
neg("parse", "nested-pattern", [GRAM], HEAD + b"fn f(r: Result<Int64, E>) -> Int64 { match r { Err(E.A) => 1, Ok(_) => 0 } }\n",
    "UNEXPECTED_TOKEN", b".")
neg("parse", "use-group-not-last", [SURF2], HEAD.replace(b"\n", b"\nuse a.{b}.c\n"), "INVALID_USE_GROUP", b"}.", nth=0)
CASES[-1][4]["diagnostics"][0]["span"] = [CASES[-1][4]["diagnostics"][0]["span"][0] + 1, CASES[-1][4]["diagnostics"][0]["span"][0] + 2]

# ---------------------------------------------------------------- разбор, допустимое
pos("parse", "trailing-commas", [GRAM], HEAD + b"""type P = record { x: Int64, y: Int64, }
type E = enum { A, B(Int64), }
fn f<T, U,>(a: T, b: U,) -> Seq<Int64,> { [1, 2, 3,] }
fn g() -> Int64 { match f(1, 2,) { Some(v) => v, None => 0, } }
""")
pos("parse", "block-like-statements", [GRAM, SURF6], HEAD + b"""fn f(x: Bool, o: Option<Int64>) -> () {
  if x { return }
  match o { Some(_) => (), None => () }
  { let y = 1; }
}
""")
pos("parse", "match-block-arm-without-comma", [SURF6], HEAD + b"""fn f(x: Option<Int64>) -> Int64 {
  match x {
    Some(v) => {
      v + 1
    }
    None => 0,
  }
}
""")
pos("parse", "fn-type-uses-binding", [GRAM, SURF6], HEAD + b"""fn twice<!e>(f: fn(Int64) -> Int64 uses e) -> (fn(Int64) -> Int64 uses e) uses {} {
  fn(x) => f(f(x))
}
""")
pos("parse", "record-literal-in-parens", [SURF6], HEAD + b"fn f(p: Point) -> Int64 { if (p == Point { x: 0, y: 0 }) { 1 } else { 2 } }\n")
pos("parse", "items-and-links", [GRAM, SURF2], b"""@id("a0b1c2")
module m
use std.seq
use a.b.{C, D as E}
@id("a0b1c3") entity A { purpose "p" terms ["x", "y"] not_about [] }
@id("a0b1c4") contract K about A { @id("a0b1c5") rule r "text" }
@id("a0b1c6") pub store S { @id("a0b1c7") table t: Map<Int64, Int64> derived_from A }
@id("a0b1c8") pub event Ev { @id("a0b1c9") n: Int64 }
@id("a0b1ca") pub command c(n: Int64) -> Result<(), Int64> uses { reads S.t, writes S.t, emits Ev } implements K.r { Ok(()) }
@id("a0b1cb") pub query q() -> Int64 uses { reads S.t } requires K.r { 0 }
@id("a0b1cc") handler h(ev: Ev) uses { writes S.t } { () }
@id("a0b1cd") migration mg on S.t (old: Int64) -> Result<Int64, Int64> { Ok(old) }
@id("a0b1ce") test t1 checks K.r { () }
@id("a0b1cf") fn old_api() -> Int64 supersedes "a0b1cg" { 1 }
""")


def main() -> None:
    for area in ("lex", "parse"):
        shutil.rmtree(OUT / area, ignore_errors=True)
    for area, name, refs, src, expect in CASES:
        d = OUT / area / name
        d.mkdir(parents=True)
        (d / "main.bag").write_bytes(src)
        case = {"id": f"{area}/{name}", "spec": refs, "origin": "independent", "levels": ["L2"],
                "files": ["main.bag"], "expect": expect}
        (d / "case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(CASES)} случаев записано в {OUT.relative_to(ROOT)}/{{lex,parse}}")


if __name__ == "__main__":
    main()
