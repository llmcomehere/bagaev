"""Синтаксис эталона: lossless-лексика, разбор примеров, сверка с независимым лексером, грамматический фаззинг.

Запуск: `cd ref && python3 -m unittest discover -s tests -q`.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.syntax.lexer import lex, reconstruct  # noqa: E402
from bagaev_ref.syntax.parser import parse  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuzzgen import generate_programs, load_grammar_lint  # noqa: E402


SOURCES = sorted((ROOT / "examples").rglob("*.bag")) + sorted((ROOT / "conformance" / "cases").rglob("*.bag"))
SEMANTIC_PARSE = {"MIXED_AND_OR", "MISSING_COMMA_IN_MATCH", "RECORD_LITERAL_NOT_AFTER_PATH", "MIXED_RECORD_ENTRIES",
                  "RECORD_UPDATE_WITHOUT_FIELDS", "INVALID_USE_GROUP", "INT_LITERAL_OUT_OF_RANGE"}


class Lossless(unittest.TestCase):
    def test_reconstruct_all_sources(self):
        """LEX-15: trivia + тексты токенов = исходник (для декодируемых файлов)."""
        n = 0
        for f in SOURCES:
            data = f.read_bytes()
            toks, diags = lex(data, f.name)
            if diags and diags[0].code in ("SOURCE_BOM", "INVALID_UTF8"):
                continue
            self.assertEqual(reconstruct(toks), data.decode("utf-8"), f)
            n += 1
        self.assertGreater(n, 60)


class Examples(unittest.TestCase):
    def test_examples_parse_without_diagnostics(self):
        for f in sorted((ROOT / "examples").rglob("*.bag")):
            tree, _, diags = parse(f.read_bytes(), f.name)
            self.assertEqual([d.code for d in diags], [], f)
            self.assertIsNotNone(tree)


class DifferentialLexer(unittest.TestCase):
    """Две независимые реализации lexical.md: эталон и tools/grammar_lint.py."""

    def test_token_streams_agree(self):
        gl = load_grammar_lint()
        g = gl.Grammar(gl.GRAMMAR.read_text(encoding="utf-8"))
        compared = 0
        for f in SOURCES:
            data = f.read_bytes()
            mine, diags = lex(data, f.name)
            try:
                theirs = gl.lex(data, g.reserved)
            except gl.LexError as e:
                self.assertTrue(diags, f"{f}: инструмент нашёл {e.code}, эталон — нет")
                self.assertEqual((diags[0].code, diags[0].start, diags[0].end), (e.code, e.start, e.end), f)
                continue
            self.assertFalse(diags, f"{f}: эталон нашёл {diags[:1]}, инструмент — нет")
            self.assertEqual([(t.kind, t.text, t.start, t.end) for t in mine],
                             [(t.kind, t.text, t.start, t.end) for t in theirs], f)
            compared += 1
        self.assertGreater(compared, 40)


class GrammarFuzz(unittest.TestCase):
    """Программы, порождённые по grammar.ebnf, разбираются без UNEXPECTED_TOKEN/EOF."""

    def test_generated_programs_parse(self):
        bad = []
        for src in generate_programs(300):
            tree, _, diags = parse(src.encode("utf-8"), "fuzz.bag")
            syntax = [d for d in diags if d.code not in SEMANTIC_PARSE]
            if syntax:
                bad.append((src[:300], syntax[0].code, syntax[0].start))
        self.assertEqual(bad[:3], [], f"{len(bad)} из 300 сгенерированных программ не разобраны")


class DifferentialAcceptance(unittest.TestCase):
    """Ревью m2: порченые программы (удаление, перестановка, вставка токена) эталон принимает или отвергает
    так же, как независимый распознаватель Earley по grammar.ebnf. Коды проверок после разбора не считаются."""

    def test_mutants_agree_with_grammar(self):
        import random
        gl = load_grammar_lint()
        g = gl.Grammar(gl.GRAMMAR.read_text(encoding="utf-8"))
        g.to_bnf()
        rnd = random.Random(20261024)
        compared, diff = 0, []
        for src in generate_programs(200, seed=99):
            toks = src.split(" ")
            for _ in range(3):
                t = list(toks)
                k, op = rnd.randrange(len(t)), rnd.choice("dsi")
                if op == "d":
                    del t[k]
                elif op == "s" and k + 1 < len(t):
                    t[k], t[k + 1] = t[k + 1], t[k]
                else:
                    t.insert(k, rnd.choice(t))
                data = " ".join(t).encode("utf-8")
                try:
                    gt = gl.lex(data, g.reserved)
                except gl.LexError:
                    continue
                _, _, diags = parse(data, "m.bag")
                if any(d.phase == "lex" for d in diags):
                    continue
                accepted, _, _ = gl.recognize(g, gt)
                mine = not [d for d in diags if d.code not in SEMANTIC_PARSE | {"RECORD_UPDATE_WITHOUT_FIELDS"}]
                compared += 1
                if accepted != mine:
                    diff.append((accepted, data.decode()[:200]))
        self.assertGreater(compared, 400)
        self.assertEqual(diff[:3], [], f"{len(diff)} расхождений из {compared}")


if __name__ == "__main__":
    unittest.main()
