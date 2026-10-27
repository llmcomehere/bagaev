"""Форматтер (spec/language/format.md): смысл сохраняется, комментарии не теряются, вывод идемпотентен.

Запуск: `cd ref && python3 -m unittest discover -s tests -q`.
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bagaev_ref.syntax import ast as A  # noqa: E402
from bagaev_ref.syntax.lexer import lex  # noqa: E402
from bagaev_ref.syntax.parser import parse  # noqa: E402
from bagaev_ref.syntax.printer import FormatError, ID_ATTR, assign_ids, format_source  # noqa: E402
from fuzzgen import generate_programs  # noqa: E402

POSITION_FIELDS = {"start", "end", "op_start", "brace", "doc", "pub_at"}


def shape(n):
    """AST без диапазонов; атомы рядов эффектов — множеством (FMT-06)."""
    if isinstance(n, A.EffectRow):
        items = sorted((i.kind, tuple(x.text for x in i.path)) for i in n.items)
        return ("EffectRow", tuple(items), shape(n.var))
    if isinstance(n, A.Node):
        return (type(n).__name__,) + tuple((k, shape(v)) for k, v in vars(n).items() if k not in POSITION_FIELDS)
    if isinstance(n, (list, tuple)):
        if n and isinstance(n[0], tuple) and len(n[0]) in (3, 4) and isinstance(n[0][-1], int):
            return tuple(x[:-2] for x in n)          # аргументы атрибутов и цели supersedes без диапазонов
        return tuple(shape(x) for x in n)
    return n


def comments(data: bytes) -> list[str]:
    toks, _ = lex(data)
    return sorted(tv.text.rstrip() for t in toks for tv in t.leading if tv.kind in ("comment", "doc"))


def clean_sources():
    out = []
    for f in sorted((ROOT / "examples").rglob("*.bag")) + sorted((ROOT / "conformance" / "cases").rglob("*.bag")):
        data = f.read_bytes()
        tree, _, diags = parse(data, f.name)
        if tree is not None and not diags:
            out.append((str(f), data))
    return out


class Roundtrip(unittest.TestCase):
    def check(self, name, data):
        out = format_source(data, "x.bag").encode("utf-8")
        tree2, _, diags2 = parse(out, "x.bag")
        self.assertEqual(diags2, [], f"{name}: вывод не разбирается\n{out.decode()}")
        self.assertEqual(shape(parse(data, "x.bag")[0]), shape(tree2), name)
        self.assertEqual(comments(data), comments(out), name)
        self.assertEqual(format_source(out, "x.bag").encode("utf-8"), out, f"{name}: не идемпотентен")
        self.assertTrue(out.endswith(b"\n") and not out.endswith(b"\n\n"), name)
        self.assertFalse(any(line != line.rstrip() for line in out.decode().split("\n")), name)

    def test_corpus(self):
        srcs = clean_sources()
        self.assertGreater(len(srcs), 30)
        for name, data in srcs:
            self.check(name, data)

    def test_generated_flat_and_broken(self):
        """Порождённые программы: токены через пробел (всё в строку) и через перевод строки (всё перенесено)."""
        n = 0
        for sep in (" ", "\n"):
            for k, src in enumerate(generate_programs(150, seed=7 + len(sep), sep=sep)):
                data = src.encode("utf-8")
                tree, _, diags = parse(data, "g.bag")
                if diags:
                    continue
                self.check(f"gen{sep!r}#{k}", data)
                n += 1
        self.assertGreater(n, 100)

    def test_examples_are_canonical(self):
        for f in sorted((ROOT / "examples").rglob("*.bag")):
            self.assertEqual(format_source(f.read_bytes(), f.name), f.read_text(encoding="utf-8"), f)


class Comments(unittest.TestCase):
    SRC = """// до модуля
@id("aaaaaa")
module m // хвост модуля

// перед use
use std.seq // хвост use

/// док функции
@id("bbbbbb")
/// док после атрибута
pub fn f(
  a: Int64, // хвост параметра
) -> Int64 {
  // перед let
  let x = g(a, // внутри вызова
    1);


  match x { // после скобки
    // перед ветвью
    A => 1, // хвост ветви
    B => {
      // в блоке ветви
      2
    },
    // перед закрытием match
  }
  // перед закрытием блока
}

@id("cccccc")
type T = record {
  // перед полем
  @id("dddddd") a: Int64, // хвост поля
}
// конец файла
"""

    def test_torture(self):
        data = self.SRC.encode("utf-8")
        out = format_source(data)
        self.assertEqual(comments(data), comments(out.encode("utf-8")))
        self.assertEqual(format_source(out.encode("utf-8")), out)
        self.assertEqual(out, self.EXPECTED)

    EXPECTED = """// до модуля
// хвост модуля
@id("aaaaaa")
module m

// перед use
// хвост use
use std.seq

/// док функции
/// док после атрибута
// хвост параметра
@id("bbbbbb")
pub fn f(
  a: Int64,
) -> Int64 {
  // перед let
  // внутри вызова
  let x = g(a, 1);

  match x {
    // после скобки
    // перед ветвью
    // хвост ветви
    A => 1,
    B => {
      // в блоке ветви
      2
    },
    // перед закрытием match
  }
  // перед закрытием блока
}

@id("cccccc")
type T = record {
  // перед полем
  // хвост поля
  @id("dddddd") a: Int64,
}
// конец файла
"""


class Refusal(unittest.TestCase):
    def test_syntax_error_is_not_formatted(self):
        with self.assertRaises(FormatError) as cm:
            format_source(b'@id("aaaaaa")\nmodule m\nfn f( -> Int64 { 1 }\n')
        self.assertEqual(cm.exception.diags[0].code, "UNEXPECTED_TOKEN")


class AssignIds(unittest.TestCase):
    SRC = b"""module m

pub type T = record {
  @id("keep01") a: Int64,
  b: Int64,
}

type E = enum { X, Y(Int64) }

store S {
  table t: Map<Int64, T>
}

event Ev { a: Int64 }

contract C about Thing {
  rule r "text"
}

fn f() -> Int64 {
  1
}
"""

    def test_assigns_all_required_sites(self):
        out = assign_ids(self.SRC, rng=random.Random(1))
        tree, _, diags = parse(out)
        self.assertEqual(diags, [])
        ids = ID_ATTR.findall(out.decode())
        # модуль, 6 деклараций, поля a b, варианты X Y, таблица t, поле события a, правило r
        self.assertEqual(len(ids), 14)
        self.assertEqual(len(set(ids)), 14)
        self.assertIn("keep01", ids)
        self.assertTrue(all(len(i) == 6 and set(i) <= set("0123456789abcdefghjkmnpqrstvwxyz")
                            for i in ids if i != "keep01"))
        self.assertEqual(assign_ids(out, rng=random.Random(2)), out, "повторный запуск ничего не меняет")
        self.assertEqual(format_source(format_source(out).encode()).encode(), format_source(out).encode())

    def test_avoids_project_ids(self):
        class Fixed:
            seq = iter("aaaaaa" "bbbbbb" "cccccc" * 20)

            def choice(self, _):
                return next(self.seq)
        taken = {"aaaaaa"}
        out = assign_ids(b"module m\n", taken=taken, rng=Fixed())
        self.assertEqual(ID_ATTR.findall(out.decode()), ["bbbbbb"])


if __name__ == "__main__":
    unittest.main()
