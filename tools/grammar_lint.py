#!/usr/bin/env python3
"""Проверка грамматики bagaev и распознавание программ прямо по ней.

  python3 tools/grammar_lint.py                       проверить spec/language/grammar.ebnf
  python3 tools/grammar_lint.py --parse F.bag ...     + токенизировать (lexical.md) и распознать файлы
  python3 tools/grammar_lint.py --parse-dir examples  + все *.bag в каталоге
  python3 tools/grammar_lint.py --lex F.bag           вывести токены (отладка)

Проверки грамматики: каждое правило определено ровно один раз и достижимо из @start; терминалы —
пунктуация LEX-14, зарезервированные или контекстные слова, классы @tokens; каждый LL(1)-конфликт
перечислен в @acknowledged со ссылкой на объяснение @resolved, и наоборот.

Распознавание — Earley по той же грамматике. Это независимая от ref/ проверка, что примеры
синтаксически принадлежат языку; она не заменяет парсер эталона и его диагностики.
Только стандартная библиотека Python.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR = ROOT / "spec" / "language" / "grammar.ebnf"
PUNCT = ["..", "->", "=>", "==", "!=", "<=", ">=", "++",
         "{", "}", "(", ")", "[", "]", ",", ";", ":", ".", "=", "<", ">",
         "+", "-", "*", "/", "%", "?", "@", "|", "!", "_"]
BIDI = {0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)}


# ============================================================================ EBNF
@dataclass(frozen=True)
class Sym:
    kind: str   # "nt" | "lit" | "tok"
    name: str


class Grammar:
    def __init__(self, text: str):
        self.directives: dict[str, list[str]] = {}
        self.resolved: dict[str, str] = {}
        for body in re.findall(r"\(\*(.*?)\*\)", text, re.S):
            for m in re.finditer(r"@(start|tokens|reserved|contextual|acknowledged)\s+([^@*]+)", body):
                self.directives.setdefault(m.group(1), []).extend(m.group(2).split())
            for m in re.finditer(r"@resolved\s+(\w+):", body):
                self.resolved[m.group(1)] = body
        src = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
        self.tokens = list(re.finditer(r'"(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z0-9_]*|[=|;\[\]{}()]', src))
        self.pos = 0
        self.rules: dict[str, object] = {}
        self.order: list[str] = []
        self.dupes: list[str] = []
        while self.pos < len(self.tokens):
            name = self.next()
            if self.next() != "=":
                raise SyntaxError(f"ожидалось '=' после {name}")
            expr = self.alt()
            if self.next() != ";":
                raise SyntaxError(f"ожидалось ';' в конце правила {name}")
            if name in self.rules:
                self.dupes.append(name)
            self.rules[name] = expr
            self.order.append(name)
        self.token_classes = set(self.directives.get("tokens", []))
        self.reserved = set(self.directives.get("reserved", []))
        self.contextual = set(self.directives.get("contextual", []))
        self.start = self.directives.get("start", ["File"])[0]

    def peek(self):
        return self.tokens[self.pos].group(0) if self.pos < len(self.tokens) else None

    def next(self):
        t = self.peek()
        self.pos += 1
        return t

    def alt(self):
        opts = [self.seq()]
        while self.peek() == "|":
            self.next()
            opts.append(self.seq())
        return ("alt", opts) if len(opts) > 1 else opts[0]

    def seq(self):
        items = []
        while self.peek() not in (None, "|", ";", ")", "]", "}"):
            items.append(self.atom())
        return ("seq", items)

    def atom(self):
        t = self.next()
        if t == "(":
            e = self.alt(); assert self.next() == ")"; return e
        if t == "[":
            e = self.alt(); assert self.next() == "]"; return ("opt", e)
        if t == "{":
            e = self.alt(); assert self.next() == "}"; return ("rep", e)
        if t.startswith('"'):
            return ("lit", t[1:-1])
        return ("ref", t)

    # --- в BNF: {нетерминал: [[Sym]]}, owner — исходное правило каждого служебного нетерминала
    def to_bnf(self):
        self.bnf: dict[str, list[list[Sym]]] = {}
        self.owner: dict[str, str] = {}
        counter = [0]

        def fresh(owner):
            counter[0] += 1
            n = f"{owner}#{counter[0]}"
            self.owner[n] = owner
            return n

        def conv(e, owner) -> list[list[Sym]]:
            k = e[0]
            if k == "alt":
                return [p for o in e[1] for p in conv(o, owner)]
            if k == "seq":
                prods = [[]]
                for it in e[1]:
                    sym = conv_sym(it, owner)
                    prods = [p + [sym] for p in prods]
                return prods
            return [[conv_sym(e, owner)]]

        def conv_sym(e, owner) -> Sym:
            k = e[0]
            if k == "lit":
                return Sym("lit", e[1])
            if k == "ref":
                return Sym("tok", e[1]) if e[1] in self.token_classes else Sym("nt", e[1])
            n = fresh(owner)
            if k == "opt":
                self.bnf[n] = conv(e[1], owner) + [[]]
            elif k == "rep":
                self.bnf[n] = [p + [Sym("nt", n)] for p in conv(e[1], owner)] + [[]]
            else:  # группа
                self.bnf[n] = conv(e, owner)
            return Sym("nt", n)

        for name in self.order:
            self.owner[name] = name
            self.bnf[name] = conv(self.rules[name], name)
        return self.bnf


def first_follow(bnf, start):
    nullable, first = set(), {n: set() for n in bnf}
    changed = True
    while changed:
        changed = False
        for n, prods in bnf.items():
            for p in prods:
                if all(s.kind == "nt" and s.name in nullable for s in p) and n not in nullable:
                    nullable.add(n); changed = True
                for s in p:
                    add = {s.name if s.kind == "tok" else '"' + s.name + '"'} if s.kind != "nt" else first.get(s.name, set())
                    if not add <= first[n]:
                        first[n] |= add; changed = True
                    if not (s.kind == "nt" and s.name in nullable):
                        break
    follow = {n: set() for n in bnf}
    follow[start].add("EOF")
    changed = True
    while changed:
        changed = False
        for n, prods in bnf.items():
            for p in prods:
                for i, s in enumerate(p):
                    if s.kind != "nt":
                        continue
                    acc, rest_nullable = set(), True
                    for t in p[i + 1:]:
                        acc |= ({t.name if t.kind == "tok" else '"' + t.name + '"'} if t.kind != "nt" else first[t.name])
                        if not (t.kind == "nt" and t.name in nullable):
                            rest_nullable = False
                            break
                    if rest_nullable:
                        acc |= follow[n]
                    if not acc <= follow[s.name]:
                        follow[s.name] |= acc; changed = True
    return nullable, first, follow


def prod_first(p, nullable, first, follow_n):
    acc = set()
    for s in p:
        acc |= ({s.name if s.kind == "tok" else '"' + s.name + '"'} if s.kind != "nt" else first[s.name])
        if not (s.kind == "nt" and s.name in nullable):
            return acc
    return acc | follow_n


def lint_grammar(g: Grammar) -> tuple[list[str], list[str]]:
    errs, info = [], []
    if g.dupes:
        errs.append(f"правила определены повторно: {g.dupes}")
    bnf = g.to_bnf()
    refs = {s.name for prods in bnf.values() for p in prods for s in p if s.kind == "nt"}
    undefined = sorted(r for r in refs if r not in bnf)
    if undefined:
        errs.append(f"не определены: {undefined}")
    seen, todo = set(), [g.start]
    while todo:
        n = todo.pop()
        if n in seen or n not in bnf:
            continue
        seen.add(n)
        todo += [s.name for p in bnf[n] for s in p if s.kind == "nt"]
    unreachable = [n for n in g.order if n not in seen]
    if unreachable:
        errs.append(f"недостижимы из {g.start}: {unreachable}")
    words = g.reserved | g.contextual
    for n, prods in bnf.items():
        for p in prods:
            for s in p:
                if s.kind == "lit" and s.name not in PUNCT and s.name not in words:
                    errs.append(f"{g.owner[n]}: терминал \"{s.name}\" не пунктуация LEX-14 и не объявленное слово")
                if s.kind == "tok" and s.name not in g.token_classes:
                    errs.append(f"{g.owner[n]}: неизвестный класс токенов {s.name}")
    if undefined:
        return errs, info
    nullable, first, follow = first_follow(bnf, g.start)
    conflicts: dict[str, set[str]] = {}
    for n, prods in bnf.items():
        sets = [prod_first(p, nullable, first, follow[n]) for p in prods]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                common = sets[i] & sets[j]
                if common:
                    conflicts.setdefault(g.owner[n], set()).update(common)
    ack = {}
    for a in g.directives.get("acknowledged", []):
        rule, _, res = a.partition(":")
        ack[rule] = res
    for rule, toks in sorted(conflicts.items()):
        if rule not in ack:
            errs.append(f"LL(1)-конфликт в {rule} по {sorted(toks)[:6]} не перечислен в @acknowledged")
        elif any(r not in g.resolved for r in ack[rule].split("+")):
            errs.append(f"@acknowledged {rule}:{ack[rule]} ссылается на несуществующий @resolved")
    for rule in ack:
        if rule not in conflicts:
            errs.append(f"@acknowledged {rule}: конфликта нет — уберите запись")
    info.append(f"{len(g.order)} правил, {len(bnf)} нетерминалов BNF, {len(conflicts)} LL(1)-конфликтов, "
                f"объяснений @resolved: {len(g.resolved)}")
    return errs, info


# ============================================================================ лексер (lexical.md)
@dataclass
class Tok:
    kind: str     # IDENT KW INT STRING BYTES PUNCT EOF
    text: str
    start: int
    end: int


class LexError(Exception):
    def __init__(self, code, start, end, msg=""):
        super().__init__(f"{code} [{start},{end}) {msg}")
        self.code, self.start, self.end = code, start, end


LEX_RULE = {"SOURCE_BOM": 1, "INVALID_UTF8": 1, "SOURCE_NOT_NFC": 2, "FORBIDDEN_CHARACTER": 3,
            "BIDI_CONTROL_IN_SOURCE": 3, "STRAY_CR": 4}
ASCII_DIGITS = "0123456789"


def _nfc_error(src: str, off: list[int]):
    nfc = unicodedata.normalize("NFC", src)
    if nfc == src:
        return None
    i = next((k for k, (a, b) in enumerate(zip(src, nfc)) if a != b), min(len(src), len(nfc)))
    s = i
    while s > 0 and unicodedata.combining(src[s]) != 0:
        s -= 1
    e = s + 1
    while e < len(src) and unicodedata.combining(src[e]) != 0:
        e += 1
    return LexError("SOURCE_NOT_NFC", off[s], off[e])


def lex(data: bytes, reserved: set[str]) -> list[Tok]:
    """Лексер по lexical.md. Первая ошибка — минимальная по смещению (LEX-16), при равенстве — по номеру правила."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise LexError("SOURCE_BOM", 0, 3)
    try:
        src = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        raise LexError("INVALID_UTF8", e.start, e.start + 1) from None
    off = [0]
    for ch in src:                      # байтовые смещения символов
        off.append(off[-1] + len(ch.encode()))
    candidates = []
    nfc = _nfc_error(src, off)
    if nfc:
        candidates.append(nfc)
    try:
        toks = _lex_main(src, off, reserved)
    except LexError as e:
        candidates.append(e)
        toks = None
    if candidates:
        raise min(candidates, key=lambda e: (e.start, LEX_RULE.get(e.code, 9)))
    return toks


def _check_char(src, off, k, in_literal):
    ch = src[k]
    cp = ord(ch)
    if cp in BIDI:
        raise LexError("BIDI_CONTROL_IN_SOURCE", off[k], off[k + 1])
    if (unicodedata.category(ch) == "Cc" and ch not in "\t\n\r") or cp in (0x2028, 0x2029):
        raise LexError("FORBIDDEN_CHARACTER", off[k], off[k + 1])
    if ch == "\r" and not (k + 1 < len(src) and src[k + 1] == "\n"):
        raise LexError("STRAY_CR", off[k], off[k + 1])


def _lex_main(src: str, off: list[int], reserved: set[str]) -> list[Tok]:
    toks, i, n = [], 0, len(src)

    def err(code, a, b):
        raise LexError(code, off[a], off[min(b, n)])

    while i < n:
        c = src[i]
        _check_char(src, off, i, False)
        if c in " \t\n":
            i += 1; continue
        if c == "\r":                  # только в паре CRLF (проверено выше)
            i += 1; continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                _check_char(src, off, k, True)
            i = j; continue
        if c == '"' or (c == "b" and src.startswith('b"', i)):
            is_bytes = c == "b"
            j = i + (2 if is_bytes else 1)
            while True:
                if j >= n or src[j] == "\n":
                    err("UNTERMINATED_STRING", i, j)
                ch = src[j]
                _check_char(src, off, j, True)
                if ch == "\r":
                    err("UNTERMINATED_STRING", i, j)
                if ch == '"':
                    break
                if ch == "\\":
                    if j + 1 >= n:
                        err("INVALID_ESCAPE", j, j + 1)
                    e = src[j + 1]
                    if e in 'nrt\\"0':
                        j += 2; continue
                    if e == "x" and is_bytes:
                        if not re.fullmatch(r"[0-9a-fA-F]{2}", src[j + 2:j + 4]):
                            err("INVALID_ESCAPE", j, min(n, j + 4))
                        j += 4; continue
                    if e == "u" and not is_bytes:
                        m = re.match(r"\{([0-9a-fA-F]{1,6})\}", src[j + 2:])
                        if not m:
                            m2 = re.match(r"\{[^}\n]*\}", src[j + 2:])
                            err("INVALID_ESCAPE", j, j + 2 + (m2.end() if m2 else 0))
                        v = int(m.group(1), 16)
                        if v > 0x10FFFF or 0xD800 <= v <= 0xDFFF:
                            err("INVALID_ESCAPE", j, j + 2 + m.end())
                        j += 2 + m.end(); continue
                    err("INVALID_ESCAPE", j, j + 2)
                if is_bytes and not (0x20 <= ord(ch) <= 0x7E):
                    err("INVALID_BYTE_LITERAL", j, j + 1)
                j += 1
            toks.append(Tok("BYTES" if is_bytes else "STRING", src[i:j + 1], off[i], off[j + 1]))
            i = j + 1; continue
        if c in ASCII_DIGITS:
            m = re.match(r"0x[0-9a-fA-F_]*|[0-9][0-9_]*", src[i:])
            t = m.group(0)
            j = i + len(t)
            if re.match(r"\.[0-9]|[eE][+-]?[0-9]", src[j:]) and not t.startswith("0x"):
                fm = re.match(r"[0-9_]+(\.[0-9][0-9_]*)?([eE][+-]?[0-9]+)?", src[i:])
                err("UNSUPPORTED_FEATURE", i, i + fm.end())
            if j < n and (src[j].isalnum() or src[j] == "_" or ("x" + src[j]).isidentifier()):
                k = j
                while k < n and ("x" + src[k]).isidentifier():
                    k += 1
                err("MALFORMED_NUMBER", i, k)
            digits = t[2:] if t.startswith("0x") else t
            if not t.startswith("0x") and len(t) > 1 and t[0] == "0":
                err("LEADING_ZERO", i, j)
            if not digits or digits.startswith("_") or digits.endswith("_") or "__" in digits:
                err("MALFORMED_NUMBER", i, j)
            v = int(digits.replace("_", ""), 16 if t.startswith("0x") else 10)
            if v > 2**63:
                err("INT_LITERAL_OUT_OF_RANGE", i, j)
            toks.append(Tok("INT", t, off[i], off[j]))
            i = j; continue
        if c == "_" or ("x" + c).isidentifier() and (c.isidentifier() or c == "_"):
            j = i + 1
            while j < n and ("x" + src[j]).isidentifier():
                j += 1
            t = src[i:j]
            if t == "_":
                toks.append(Tok("PUNCT", "_", off[i], off[j]))
            else:
                toks.append(Tok("KW" if t in reserved else "IDENT", t, off[i], off[j]))
            i = j; continue
        for p in PUNCT:
            if src.startswith(p, i):
                toks.append(Tok("PUNCT", p, off[i], off[i + len(p)]))
                i += len(p); break
        else:
            cat = unicodedata.category(c)
            err("FORBIDDEN_CHARACTER" if cat in ("Zs", "Zl", "Zp", "Cf") else "UNEXPECTED_CHARACTER", i, i + 1)
    toks.append(Tok("EOF", "", off[n], off[n]))
    return toks


EXPR_END = {")", "]", "}", "?", "_"}


def int_min_errors(toks: list[Tok]) -> list[LexError]:
    """LEX-11, фаза parse: литерал 2^63 допустим только как операнд унарного минуса."""
    out = []
    for k, t in enumerate(toks):
        if t.kind != "INT":
            continue
        d = t.text[2:] if t.text.startswith("0x") else t.text
        if int(d.replace("_", ""), 16 if t.text.startswith("0x") else 10) != 2**63:
            continue
        prev = toks[k - 1] if k else None
        before = toks[k - 2] if k >= 2 else None
        unary = prev is not None and prev.text == "-" and (
            before is None or not (before.kind in ("IDENT", "INT", "STRING", "BYTES")
                                   or before.text in EXPR_END or before.text in ("true", "false")))
        if not unary:
            out.append(LexError("INT_LITERAL_OUT_OF_RANGE", t.start, t.end))
    return out


# ============================================================================ Earley
def recognize(g: Grammar, toks: list[Tok]) -> tuple[bool, int, set[str]]:
    """Распознать поток токенов. Возвращает (принят, индекс самого дальнего токена, ожидаемые там терминалы)."""
    bnf = g.bnf
    nullable, _, _ = first_follow(bnf, g.start)

    def match(sym: Sym, t: Tok) -> bool:
        if sym.kind == "tok":
            return t.kind == sym.name if sym.name != "EOF" else t.kind == "EOF"
        if t.kind in ("PUNCT", "KW"):
            return t.text == sym.name
        return t.kind == "IDENT" and t.text == sym.name and sym.name in g.contextual

    START = "$S"
    prods = {n: [tuple(p) for p in ps] for n, ps in bnf.items()}
    prods[START] = [(Sym("nt", g.start),)]
    nullable = set(nullable)
    sets = [dict() for _ in range(len(toks) + 1)]   # item -> None; item = (lhs, prod_idx, dot, origin)

    def add(k, item, work):
        if item not in sets[k]:
            sets[k][item] = None
            work.append(item)

    work0 = []
    add(0, (START, 0, 0, 0), work0)
    furthest, expected = 0, set()
    for k in range(len(toks) + 1):
        work = list(sets[k].keys()) if k else work0
        while work:
            lhs, pi, dot, origin = work.pop()
            p = prods[lhs][pi]
            if dot < len(p):
                s = p[dot]
                if s.kind == "nt":
                    for j in range(len(prods[s.name])):
                        add(k, (s.name, j, 0, k), work)
                    if s.name in nullable:
                        add(k, (lhs, pi, dot + 1, origin), work)
                elif k < len(toks) and match(s, toks[k]):
                    sets[k + 1][(lhs, pi, dot + 1, origin)] = None
            else:
                for (l2, p2, d2, o2) in list(sets[origin].keys()):
                    q = prods[l2][p2]
                    if d2 < len(q) and q[d2].kind == "nt" and q[d2].name == lhs:
                        add(k, (l2, p2, d2 + 1, o2), work)
        if sets[k]:
            furthest = k
            expected = set()
            for (l, pi, d, _o) in sets[k]:
                q = prods[l][pi]
                if d < len(q) and q[d].kind != "nt":
                    expected.add(q[d].name)
        if k < len(toks) and not sets[k + 1]:
            return False, k, expected
    ok = (START, 0, 1, 0) in sets[len(toks)]
    return ok, furthest, expected


def check_file(g: Grammar, path: Path) -> str | None:
    data = path.read_bytes()
    try:
        toks = lex(data, g.reserved)
    except LexError as e:
        return f"{e.code} [{e.start},{e.end})"
    for e in int_min_errors(toks):
        return f"{e.code} [{e.start},{e.end})"
    ok, k, expected = recognize(g, toks)
    if ok:
        return None
    t = toks[min(k, len(toks) - 1)]
    line = data[:t.start].count(b"\n") + 1
    return f"UNEXPECTED_TOKEN {t.text or 'EOF'!r} [{t.start},{t.end}) строка {line}; ожидалось: {sorted(expected)[:12]}"


ITEM_WORDS = {"type", "entity", "contract", "store", "event", "command", "handler", "query", "migration", "test"}


def missing_ids(toks: list[Tok]) -> list[Tok]:
    """SURF-07 без типов: заголовок модуля, декларации верхнего уровня, поля record/event, варианты enum,
    таблицы и правила обязаны нести @id. Возвращает токены имён, у которых его нет."""
    out, depth, i = [], 0, 0
    member_bodies: dict[int, str] = {}       # глубина тела → вид: "fields" | "variants" | "store" | "contract"
    pending_id = False
    prev = None
    n = len(toks)
    while i < n:
        tk = toks[i]
        if tk.text == "@" and tk.kind == "PUNCT" and i + 1 < n:
            is_id = toks[i + 1].text == "id"
            j = i + 2
            if j < n and toks[j].text == "(":
                d = 0
                while j < n:
                    d += toks[j].text == "("
                    d -= toks[j].text == ")"
                    j += 1
                    if d == 0:
                        break
            pending_id = pending_id or is_id
            prev, i = toks[j - 1], j
            continue
        if tk.kind == "KW" and tk.text == "pub":
            prev, i = tk, i + 1
            continue
        nxt = toks[i + 1] if i + 1 < n else None
        if depth == 0 and nxt is not None and nxt.kind == "IDENT" and (
                (tk.kind == "KW" and tk.text in ("module", "fn")) or (tk.kind == "IDENT" and tk.text in ITEM_WORDS)):
            if not pending_id:
                out.append(nxt)
            kind = {"event": "fields", "store": "store", "contract": "contract"}.get(tk.text)
            if kind:                                   # тело начнётся с ближайшего «{»
                j = i + 1
                while j < n and toks[j].text != "{":
                    j += 1
                member_bodies[1] = kind
        body = member_bodies.get(depth)
        if body and tk.kind == "IDENT" and prev is not None and prev.text in ("{", ",", ")") and (
                (body in ("fields", "variants") and nxt is not None and nxt.text in (":", "(", ",", "}"))
                or (body == "store" and tk.text == "table") or (body == "contract" and tk.text == "rule")):
            if body in ("fields", "variants") and prev.text == ")" and not pending_id:
                pass                                   # ")" не от атрибута — это не начало элемента
            elif not pending_id:
                out.append(tk if body in ("fields", "variants") else (nxt or tk))
        if tk.text in ("record", "enum") and tk.kind == "IDENT" and nxt is not None and nxt.text == "{":
            member_bodies[depth + 1] = "fields" if tk.text == "record" else "variants"
        if tk.text in ("{", "(", "["):
            depth += 1
        elif tk.text in ("}", ")", "]"):
            member_bodies.pop(depth, None)
            depth -= 1
        pending_id = False
        prev, i = tk, i + 1
    return out


# Коды, которые грамматика сознательно не различает: их ловит проверка после разбора (SURF-50…SURF-57).
SEMANTIC_PARSE_CODES = {"MIXED_AND_OR", "MISSING_COMMA_IN_MATCH", "INVALID_USE_GROUP",
                        "RECORD_LITERAL_NOT_AFTER_PATH", "MIXED_RECORD_ENTRIES", "RECORD_UPDATE_WITHOUT_FIELDS"}
GRAMMAR_REJECT_CODES = {"UNEXPECTED_TOKEN", "UNEXPECTED_EOF", "RESERVED_WORD_AS_NAME", "NONASSOC_COMPARISON"}
# Грамматика отвергает, но парсер выдаёт уточнённый код в другой точке (SURF-52: «{» после условия).
REFINED_REJECT_CODES = {"RECORD_LITERAL_IN_CONDITION"}


def check_corpus(g: Grammar, cases_dir: Path) -> tuple[int, int, list[str]]:
    """Сверить случаи фазы parse с независимым лексером и распознавателем этого инструмента."""
    import json
    ok, total, problems = 0, 0, []
    for cf in sorted(cases_dir.rglob("case.json")):
        c = json.loads(cf.read_text(encoding="utf-8"))
        x = c.get("expect", {})
        if x.get("phase") != "parse":
            continue
        total += 1
        src = (cf.parent / c["files"][0]).read_bytes()
        want = (x.get("diagnostics") or [{}])[0]
        try:
            toks = lex(src, g.reserved)
            lex_err = (int_min_errors(toks) or [None])[0]
        except LexError as e:
            lex_err = e
        if lex_err:
            same = want.get("code") == lex_err.code and ("span" not in want or want["span"] == [lex_err.start, lex_err.end])
            if same:
                ok += 1
            else:
                problems.append(f"{c['id']}: лексер инструмента даёт {lex_err.code} [{lex_err.start},{lex_err.end}), ожидание {want}")
            continue
        accepted, k, _ = recognize(g, toks)
        if x.get("outcome") == "ACCEPTED" or want.get("code") in SEMANTIC_PARSE_CODES:
            if accepted:
                ok += 1
            else:
                problems.append(f"{c['id']}: грамматика отвергает на токене {toks[k].text!r} [{toks[k].start},{toks[k].end})")
        elif want.get("code") in GRAMMAR_REJECT_CODES:
            at = [toks[k].start, toks[k].end]
            if not accepted and ("span" not in want or want["span"] == at):
                ok += 1
            else:
                problems.append(f"{c['id']}: ожидался отказ в {want.get('span')}, инструмент: "
                                f"{'принято' if accepted else f'отказ в {at}'}")
        elif want.get("code") in REFINED_REJECT_CODES:
            if not accepted:
                ok += 1
            else:
                problems.append(f"{c['id']}: грамматика принимает программу, которую {want['code']} отвергает")
        else:
            problems.append(f"{c['id']}: лексер инструмента не нашёл ожидаемый {want.get('code')}")
    return ok, total, problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parse", nargs="*", type=Path, default=[])
    ap.add_argument("--parse-dir", nargs="*", type=Path, default=[])
    ap.add_argument("--lex", type=Path)
    ap.add_argument("--expect-fail", action="store_true", help="файлы обязаны НЕ распознаваться")
    ap.add_argument("--check-corpus", type=Path, help="сверить случаи фазы parse каталога с лексером и грамматикой")
    a = ap.parse_args()
    g = Grammar(GRAMMAR.read_text(encoding="utf-8"))
    errs, info = lint_grammar(g)
    for e in errs:
        print(f"[grammar] {e}", file=sys.stderr)
    for i in info:
        print(f"[grammar] {i}", file=sys.stderr)
    if a.lex:
        for t in lex(a.lex.read_bytes(), g.reserved):
            print(t.kind, repr(t.text), t.start, t.end)
        return 0
    if a.check_corpus:
        ok, total, problems = check_corpus(g, a.check_corpus)
        for pr in problems:
            print(f"[corpus] {pr}", file=sys.stderr)
        print(f"[corpus] {ok}/{total} случаев parse согласованы с лексером и грамматикой", file=sys.stderr)
        if problems:
            return 1
    files = list(a.parse) + [p for d in a.parse_dir for p in sorted(d.rglob("*.bag"))]
    bad = 0
    ids: dict[str, str] = {}
    for f in files if not a.expect_fail else []:     # SURF-07: наличие у обязательных мест
        try:
            for tk in missing_ids(lex(f.read_bytes(), g.reserved)):
                bad += 1
                print(f"[id] {f}: MISSING_ENTITY_ID у {tk.text!r} [{tk.start},{tk.end})", file=sys.stderr)
        except LexError:
            pass
    for f in files if not a.expect_fail else []:     # SURF-07: форма и уникальность @id
        for m in re.finditer(r'@id\("([^"]*)"\)', f.read_text(encoding="utf-8")):
            v = m.group(1)
            if not re.fullmatch(r"[0-9a-hjkmnp-tv-z]{6}", v):
                bad += 1
                print(f"[id] {f}: MALFORMED_ENTITY_ID {v!r}", file=sys.stderr)
            elif v in ids:
                bad += 1
                print(f"[id] {f}: DUPLICATE_ENTITY_ID {v} (уже в {ids[v]})", file=sys.stderr)
            else:
                ids[v] = str(f)
    for f in files:
        r = check_file(g, f)
        if (r is None) == a.expect_fail:
            bad += 1
            print(f"[parse] {f}: {r or 'распознан, а ожидался отказ'}", file=sys.stderr)
    if files:
        print(f"[parse] {len(files) - bad}/{len(files)} файлов {'отвергнуты' if a.expect_fail else 'распознаны'}",
              file=sys.stderr)
    return 1 if errs or bad else 0


if __name__ == "__main__":
    sys.exit(main())
