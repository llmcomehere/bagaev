"""Статическая проверка эталона (spec/language/checking.md): примеры принимаются, порча ловится, каскада нет.

Запуск: `cd ref && python3 -m unittest discover -s tests -q`.
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.sema.check import check_project  # noqa: E402
from bagaev_ref.syntax.lexer import lex  # noqa: E402
from bagaev_ref.syntax.parser import parse  # noqa: E402

PROJECTS = [ROOT / "examples" / "basics", ROOT / "examples" / "authorship"]


def load(root: Path) -> dict:
    return {f.relative_to(root).as_posix(): f.read_bytes() for f in sorted(root.rglob("*.bag"))}


def codes(files: dict) -> list:
    return [d.code for d in check_project(sorted(files.items()))]


class Examples(unittest.TestCase):
    def test_examples_are_accepted(self):
        for root in PROJECTS:
            self.assertEqual(codes(load(root)), [], root)

    def test_corruptions_are_caught(self):
        """Мутации примеров: число → строка и обращение к имени → неизвестное имя дают диагностику.

        Переименование самой декларации законно, поэтому мутации имён в позиции объявления пропускаются."""
        rnd = random.Random(20261023)
        tried = caught = 0
        for root in PROJECTS:
            files = load(root)
            for name, data in files.items():
                toks, _ = lex(data)
                tree, _, _ = parse(data, name)
                decl_names = {it.decl.name.start for it in tree.items}
                cand = [t for t in toks if t.kind == "INT" or (t.kind == "IDENT" and t.start not in decl_names)]
                for t in rnd.sample(cand, min(6, len(cand))):
                    repl = b'"s"' if t.kind == "INT" else b"zz_unknown"
                    new = data[:t.start] + repl + data[t.end:]
                    if parse(new, name)[2]:
                        continue
                    tried += 1
                    caught += bool(codes(dict(files, **{name: new})))
        self.assertGreater(tried, 60)
        self.assertGreaterEqual(caught / tried, 0.95, f"{caught}/{tried}")


class NoCascade(unittest.TestCase):
    """CHK-03: одна причина — одна диагностика."""

    PROGRAMS = {
        "unknown-name-in-chain": "fn f() -> Bool {\n  missing.a.b + 1 == 2\n}\n",
        "bad-argument-then-use": "fn g(x: Int64) -> Int64 {\n  x\n}\n\n@id(\"bbbbbb\")\nfn f() -> Int64 {\n"
                                 "  let y = g(\"s\");\n  y + 1\n}\n",
        "unknown-type-in-param": "fn f(p: Missing) -> Int64 {\n  p.x + p.y\n}\n",
        "wrong-arity-call": "fn g(x: Int64) -> Int64 {\n  x\n}\n\n@id(\"bbbbbb\")\nfn f() -> Bool {\n"
                            "  g(1, 2) == 3\n}\n",
    }

    def test_single_diagnostic(self):
        for name, body in self.PROGRAMS.items():
            src = '@id("zzzzzz")\nmodule main\n\n@id("aaaaaa")\n' + body
            got = check_project([("main.bag", src.encode("utf-8"))])
            self.assertEqual(len(got), 1, f"{name}: {[d.code for d in got]}")


if __name__ == "__main__":
    unittest.main()
