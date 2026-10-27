"""Генератор программ по spec/language/grammar.ebnf для тестов парсера и форматтера.

Ограничение: выражения-блоки (if/match/{…}) порождаются только как операторы блока, потому что
в начале оператора их разбор задаёт правило BlockLikeStatement, а не EBNF.
"""
import importlib.util
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_grammar_lint():
    if "bagaev_grammar_lint" in sys.modules:
        return sys.modules["bagaev_grammar_lint"]
    spec = importlib.util.spec_from_file_location("bagaev_grammar_lint", ROOT / "tools" / "grammar_lint.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bagaev_grammar_lint"] = mod
    spec.loader.exec_module(mod)
    return mod


def generate_programs(n: int, seed: int = 20261023, sep: str = " ") -> list[str]:
    gl = load_grammar_lint()
    g = gl.Grammar(gl.GRAMMAR.read_text(encoding="utf-8"))
    bnf = g.to_bnf()
    cost = {k: 10**9 for k in bnf}
    changed = True
    while changed:                       # минимальная глубина вывода каждого нетерминала
        changed = False
        for k, prods in bnf.items():
            for p in prods:
                c = 1 + max([0] + [cost[s.name] for s in p if s.kind == "nt"])
                if c < cost[k]:
                    cost[k], changed = c, True
    rnd = random.Random(seed)

    def tok_for(s):
        if s.kind == "lit":
            return s.name
        return {"IDENT": rnd.choice(["a", "b", "x", "имя", "Item", "seq"]), "INT": rnd.choice(["0", "7", "0x1f"]),
                "STRING": '"s"', "BYTES": 'b"z"', "EOF": ""}[s.name]

    def gen(k, depth, out):
        prods = bnf[k]
        if g.owner.get(k) == "Primary":
            prods = [p for p in prods if not (len(p) == 1 and p[0].kind == "nt" and p[0].name == "BlockLikeExpr")]
        if depth > 7:
            prods = [min(prods, key=lambda p: max([0] + [cost[s.name] for s in p if s.kind == "nt"]))]
        for s in rnd.choice(prods):
            if s.kind == "nt":
                gen(s.name, depth + 1, out)
            else:
                out.append(tok_for(s))

    res = []
    for _ in range(n):
        out = []
        gen(g.start, 0, out)
        res.append(sep.join(t for t in out if t))
    return res
