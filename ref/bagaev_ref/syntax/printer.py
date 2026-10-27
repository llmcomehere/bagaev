"""Канонический формат исходника по spec/language/format.md (FMT-01…FMT-16).

Печать идёт по AST; литералы берутся из исходника как есть (FMT-13). Комментарии берутся из trivia
токенов и выводятся по правилу FMT-14: перед «якорем» (декларация, `use`, оператор, хвост блока, ветвь
match, элемент тела объявления) печатаются комментарии, стоящие до него, затем комментарии изнутри
якоря вне вложенных блоков, затем комментарий в конце его последней строки.
"""
from __future__ import annotations

import random
import re

from bagaev_ref.syntax import ast as A
from bagaev_ref.syntax.parser import parse

EFFECT_ORDER = {"reads": 0, "writes": 1, "emits": 2, "host": 3}
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"
BLANK_LINE = re.compile(r"\n[ \t\r]*\n")
ID_ATTR = re.compile(r'@id\(\s*"([^"]*)"\s*\)')


class FormatError(Exception):
    """Файл не разобран без ошибок (FMT-15)."""

    def __init__(self, diags):
        super().__init__(diags[0].code if diags else "PARSE")
        self.diags = diags


class Printer:
    def __init__(self, src: bytes, toks):
        self.src = src
        self.comments = []                      # (start, end, text) в порядке исходника
        for t in toks:
            for tv in t.leading:
                if tv.kind in ("comment", "doc"):
                    self.comments.append((tv.start, tv.end, tv.text))
        self.used = [False] * len(self.comments)
        self.toks = [t for t in toks if t.kind != "EOF"]          # тексты токенов без trivia (FMT-13)
        self.out: list[str] = []

    # ------------------------------------------------------------ комментарии
    def text(self, a: int, b: int) -> str:
        return self.src[a:b].decode("utf-8")

    def tokens(self, a: int, b: int) -> list:
        return [t for t in self.toks if a <= t.start and t.end <= b]

    def token_text(self, a: int, b: int) -> str:
        """Исходное написание токенов участка без комментариев и пробелов между ними."""
        return "".join(t.text for t in self.tokens(a, b))

    def take(self, pred) -> list[str]:
        res = []
        for k, (s, e, txt) in enumerate(self.comments):
            if not self.used[k] and pred(s):
                self.used[k] = True
                res.append(txt.rstrip(" \t\r"))
        return res

    def broken(self, first: int) -> bool:
        """Автор перенёс строку сразу после открывающей скобки списка (FMT-12)."""
        k = max(self.src.rfind(b, 0, first) for b in (b"(", b"[", b"{"))
        return b"\n" in self.src[k:first]

    def seq(self, open_: str, close: str, parts: list, broke: bool, ind: str) -> str:
        """Список элементов: в строку или по одному на строке с запятой после каждого."""
        if not broke:
            return open_ + ", ".join(p(ind) for p in parts) + close
        inner = ind + "  "
        return open_ + "\n" + "".join(inner + p(inner) + ",\n" for p in parts) + ind + close

    def trailing_end(self, end: int) -> int:
        """Конец хвостового комментария строки после позиции end, или end, если его нет."""
        j = end
        while j < len(self.src) and self.src[j:j + 1] in (b" ", b"\t", b",", b";"):
            j += 1
        if self.src[j:j + 2] == b"//" and self.src[j:j + 3] != b"///":   # /// относится к следующей декларации
            return j + 1
        return end

    def anchor(self, node, ind: str, nested=(), prev_end: int | None = None, blank_ok: bool = True):
        """Вывести комментарии якоря (FMT-14) и, если нужно, пустую строку перед ним."""
        first = min([node.start] + [s for k, (s, _, _) in enumerate(self.comments)
                                    if not self.used[k] and s < node.start])
        if blank_ok and prev_end is not None and BLANK_LINE.search(self.text(prev_end, first)):
            self.out.append("")
        before = self.take(lambda s: s < node.start)
        tail = self.trailing_end(node.end)
        inside = self.take(lambda s: node.start <= s < tail and not any(a <= s < b for a, b in nested))
        for c in before + inside:
            self.out.append(ind + c)

    def flush(self, end: int, ind: str):
        """Комментарии перед закрывающей скобкой или концом файла."""
        for c in self.take(lambda s: s < end):
            self.out.append(ind + c)

    # ------------------------------------------------------------ файл
    def file(self, f: A.File) -> str:
        m = f.module
        self.anchor(m, "")
        for at in m.attrs:
            self.out.append(self.attr(at))
        self.out.append("module " + self.path(m.path))
        prev = None
        for u in f.uses:
            if prev is None:
                self.out.append("")
            self.anchor(u, "", blank_ok=False)
            self.out.append(self.use(u))
            prev = u
        for it in f.items:
            self.out.append("")
            self.anchor(it, "", nested=self.item_nested(it.decl))
            self.item(it)
        self.flush(len(self.src) + 1, "")
        return "\n".join(self.out) + "\n"

    @staticmethod
    def item_nested(d):
        body = getattr(d, "body", None)
        if isinstance(body, A.Block):
            return [(body.start, body.end)]
        if isinstance(d, (A.TypeDecl, A.EntityDecl, A.ContractDecl, A.StoreDecl, A.EventDecl)):
            if isinstance(d, A.TypeDecl) and d.kind == "opaque":
                return []
            return [(d.name.end, d.end)]
        return []

    def attr(self, at: A.Attr) -> str:
        return "@" + at.name.text + "(" + ", ".join(self.text(s, e) for _, _, s, e in at.args) + ")"

    def attrs_inline(self, attrs) -> str:
        return "".join(self.attr(a) + " " for a in attrs)

    @staticmethod
    def path(p) -> str:
        return ".".join(n.text for n in p)

    def use(self, u: A.UseDecl) -> str:
        s = "use " + self.path(u.path)
        if u.group is not None:
            s += ".{" + ", ".join(g.name.text + (" as " + g.alias.text if g.alias else "") for g in u.group) + "}"
        if u.alias:
            s += " as " + u.alias.text
        return s

    # ------------------------------------------------------------ декларации
    def item(self, it: A.Item):
        for at in it.attrs:
            self.out.append(self.attr(at))
        d = it.decl
        pub = "pub " if it.pub else ""
        if isinstance(d, (A.FnDecl, A.EntryDecl, A.HandlerDecl, A.MigrationDecl, A.TestDecl)):
            head = pub + self.signature(d)
            clauses = []
            if getattr(d, "uses", None) is not None:
                clauses.append("uses " + self.row(d.uses))
            for lk in getattr(d, "links", []):
                clauses.append(self.link(lk))
            if clauses:
                self.out.append(head)
                self.out.extend("  " + c for c in clauses)
                self.out.append(self.block(d.body, "", open_line=False))
            else:
                self.out.append(head + " " + self.block(d.body, ""))
            return
        if isinstance(d, A.TypeDecl):
            head = f"{pub}type {d.name.text}{self.generics(d.params)} = "
            if d.kind == "opaque":
                self.out.append(head + "opaque " + self.type(d.rep))
            elif d.kind == "record":
                self.body(head + "record", d.fields, d.end, self.field, ",")
            else:
                self.body(head + "enum", d.variants, d.end, self.variant, ",")
            return
        if isinstance(d, A.EventDecl):
            self.body(f"{pub}event {d.name.text}", d.fields, d.end, self.field, ",")
        elif isinstance(d, A.StoreDecl):
            self.body(f"{pub}store {d.name.text}", d.tables, d.end, self.table, "")
        elif isinstance(d, A.ContractDecl):
            self.body(f"{pub}contract {d.name.text} about {self.path(d.about)}", d.rules, d.end, self.rule, "")
        elif isinstance(d, A.EntityDecl):
            self.entity(pub, d)

    def body(self, head: str, elems, end: int, show, sep: str):
        if not elems and not self.take_peek(end):
            self.out.append(head + " {}")
            return
        self.out.append(head + " {")
        prev = None
        for e in elems:
            self.anchor(e, "  ", prev_end=prev)
            self.out.append("  " + show(e) + sep)
            prev = e.end
        self.flush(end, "  ")
        self.out.append("}")

    def take_peek(self, end: int) -> bool:
        return any(not self.used[k] and s < end for k, (s, _, _) in enumerate(self.comments))

    def field(self, f: A.FieldDecl) -> str:
        return self.attrs_inline(f.attrs) + f.name.text + ": " + self.type(f.type)

    def variant(self, v: A.VariantDecl) -> str:
        return self.attrs_inline(v.attrs) + v.name.text + (f"({self.type(v.payload)})" if v.payload else "")

    def table(self, t: A.TableDecl) -> str:
        s = self.attrs_inline(t.attrs) + "table " + t.name.text + ": " + self.type(t.type)
        return s + (" derived_from " + self.path(t.derived_from) if t.derived_from else "")

    def rule(self, r: A.RuleDecl) -> str:
        return self.attrs_inline(r.attrs) + "rule " + r.name.text + " " + self.token_text(r.name.end, r.end)

    def entity(self, pub: str, d: A.EntityDecl):
        """Предложения сущности печатаются по токенам (без комментариев), по одному на строку."""
        clauses, cur = [], None
        for t in self.tokens(d.name.end, d.end)[1:-1]:          # без «{» и «}»
            if t.kind == "IDENT" and t.text in ("purpose", "terms", "not_about"):
                cur = [t.text + " "]
                clauses.append(cur)
            elif cur is not None:
                cur.append(t.text + " " if t.text == "," else t.text)
        clauses = ["".join(c) for c in clauses]
        if not clauses and not self.take_peek(d.end):
            self.out.append(f"{pub}entity {d.name.text} {{}}")
            return
        self.out.append(f"{pub}entity {d.name.text} {{")
        self.flush(d.end, "  ")
        self.out.extend("  " + c for c in clauses)
        self.out.append("}")

    def signature(self, d) -> str:
        if isinstance(d, A.FnDecl):
            return (f"fn {d.name.text}{self.generics(d.generics)}({self.params(d.params)}) -> "
                    f"{self.ret_type(d.ret, d.uses)}")
        if isinstance(d, A.EntryDecl):
            return f"{d.kind} {d.name.text}({self.params(d.params)}) -> {self.ret_type(d.ret, d.uses)}"
        if isinstance(d, A.HandlerDecl):
            return f"handler {d.name.text}({self.params([d.param], single=True)})"
        if isinstance(d, A.MigrationDecl):
            return (f"migration {d.name.text} on {self.path(d.table)}({self.params([d.param], single=True)}) -> "
                    f"{self.type(d.ret)}")
        return f"test {d.name.text}"

    def generics(self, gs) -> str:
        if not gs:
            return ""
        parts = []
        for g in gs:
            if g.is_effect:
                parts.append("!" + g.name.text)
            else:
                parts.append(g.name.text + (": " + " + ".join(b.text for b in g.bounds) if g.bounds else ""))
        return "<" + ", ".join(parts) + ">"

    def params(self, ps, single: bool = False) -> str:
        """single — ровно один параметр без запятой (handler, migration): всегда в строку."""
        parts = [lambda _, p=p: p.name.text + ": " + self.type(p.type) for p in ps]
        return self.seq("", "", parts, not single and bool(ps) and self.broken(ps[0].start), "")

    def row(self, r: A.EffectRow) -> str:
        if not r.items and r.var is not None:
            return r.var.text
        items = sorted(r.items, key=lambda i: (EFFECT_ORDER[i.kind], [n.text for n in i.path]))
        parts = [i.kind + " " + self.path(i.path) for i in items]
        s = ", ".join(parts)
        if r.var is not None:
            s += " | " + r.var.text
        return "{ " + s + " }" if s else "{}"

    def link(self, lk: A.LinkClause) -> str:
        if lk.kind == "supersedes":
            return "supersedes " + ", ".join(self.text(s, e) for _, s, e in lk.targets)
        return lk.kind + " " + ", ".join(self.path(t) for t in lk.targets)

    def ret_type(self, t, row) -> str:
        """Результат перед `uses`: функциональный тип без ряда берётся в скобки, иначе ряд перейдёт к нему."""
        if isinstance(t, A.FnType) and t.row is None and row is not None:
            return "(" + self.type(t) + ")"
        return self.type(t)

    def type(self, t) -> str:
        if isinstance(t, A.UnitType):
            return "()"
        if isinstance(t, A.FnType):
            s = "fn(" + ", ".join(self.type(p) for p in t.params) + ") -> " + self.ret_type(t.ret, t.row)
            return s + (" uses " + self.row(t.row) if t.row is not None else "")
        s = self.path(t.path)
        return s + ("<" + ", ".join(self.type(a) for a in t.args) + ">" if t.args else "")

    # ------------------------------------------------------------ блоки
    def block(self, b: A.Block, ind: str, open_line: bool = True) -> str:
        """Блок с отступом ind; при open_line=False «{» стоит на своей строке (FMT-05)."""
        lead = "{" if open_line else ind + "{"
        if not b.stmts and b.tail is None and not self.take_peek(b.end):
            return lead + "}"
        saved, self.out = self.out, []
        inner = ind + "  "
        prev = None
        for st in b.stmts:
            self.anchor(st, inner, nested=self.nested(st), prev_end=prev)
            self.out.append(inner + self.stmt(st, inner))
            prev = st.end
        if b.tail is not None:
            self.anchor(b.tail, inner, nested=self.nested(b.tail), prev_end=prev)
            self.out.append(inner + self.expr(b.tail, inner))
        self.flush(b.end, inner)
        lines, self.out = self.out, saved
        return lead + "\n" + "\n".join(lines) + "\n" + ind + "}"

    @staticmethod
    def nested(node):
        """Диапазоны вложенных блоков и тел match: их комментарии печатают их собственные якоря."""
        res = []

        def walk(n):
            if isinstance(n, A.Block):
                res.append((n.start, n.end))
                return
            if isinstance(n, A.Match):
                walk(n.scrutinee)
                res.append((n.scrutinee.end, n.end))
                return
            if isinstance(n, A.Node):
                for v in vars(n).values():
                    if isinstance(v, A.Node):
                        walk(v)
                    elif isinstance(v, list):
                        for x in v:
                            if isinstance(x, A.Node):
                                walk(x)
        walk(node)
        return res

    def stmt(self, st, ind: str) -> str:
        if isinstance(st, A.Let):
            ty = ": " + self.type(st.type) if st.type is not None else ""
            return f"let {st.name.text}{ty} = {self.expr(st.value, ind)};"
        return self.expr(st.expr, ind) + (";" if st.semi else "")

    # ------------------------------------------------------------ выражения
    def expr(self, e, ind: str) -> str:
        if isinstance(e, A.Lit):
            if e.kind == "unit":
                return "()"
            return self.token_text(e.start, e.end)
        if isinstance(e, A.Var):
            return e.name.text
        if isinstance(e, A.FieldAccess):
            return self.expr(e.target, ind) + "." + e.name.text
        if isinstance(e, A.Call):
            return self.expr(e.fn, ind) + self.exprs("(", ")", e.args, ind)
        if isinstance(e, A.RecordLit):
            return self.expr(e.type, ind) + " " + self.entries(e.entries, ind)
        if isinstance(e, A.SeqLit):
            return self.exprs("[", "]", e.items, ind)
        if isinstance(e, A.Unary):
            return ("not " if e.op == "not" else "-") + self.expr(e.operand, ind)
        if isinstance(e, A.Binary):
            if b"\n" in self.src[e.left.end:e.right.start]:        # перенос перед оператором (FMT-12)
                cont = ind + "  "
                return self.expr(e.left, ind) + "\n" + cont + e.op + " " + self.expr(e.right, cont)
            return self.expr(e.left, ind) + " " + e.op + " " + self.expr(e.right, ind)
        if isinstance(e, A.Try):
            return self.expr(e.operand, ind) + "?"
        if isinstance(e, A.Paren):
            return "(" + self.expr(e.inner, ind) + ")"
        if isinstance(e, A.Block):
            return self.block(e, ind)
        if isinstance(e, A.If):
            s = "if " + self.expr(e.cond, ind) + " " + self.block(e.then, ind)
            if e.else_ is not None:
                s += " else " + self.expr(e.else_, ind)
            return s
        if isinstance(e, A.Match):
            return self.match(e, ind)
        if isinstance(e, A.Return):
            return "return" + (" " + self.expr(e.value, ind) if e.value is not None else "")
        if isinstance(e, A.Emit):
            return "emit " + self.path(e.event) + " " + self.entries(e.entries, ind)
        if isinstance(e, A.Lambda):
            ps = ", ".join(p.name.text + (": " + self.type(p.type) if p.type is not None else "") for p in e.params)
            return "fn(" + ps + ") => " + self.expr(e.body, ind)
        raise TypeError(type(e).__name__)

    def exprs(self, open_: str, close: str, xs, ind: str) -> str:
        parts = [lambda i, x=x: self.expr(x, i) for x in xs]
        return self.seq(open_, close, parts, bool(xs) and self.broken(xs[0].start), ind)

    def entry(self, en, ind: str) -> str:
        if en.kind == "base":
            return ".." + self.expr(en.value, ind)
        if en.kind == "field":
            return en.name.text + ": " + self.expr(en.value, ind)
        return self.expr(en.key, ind) + " => " + self.expr(en.value, ind)

    def entries(self, es, ind: str) -> str:
        if not es:
            return "{}"
        parts = [lambda i, en=en: self.entry(en, i) for en in es]
        if self.broken(es[0].start):
            return self.seq("{", "}", parts, True, ind)
        return "{ " + ", ".join(p(ind) for p in parts) + " }"

    def match(self, m: A.Match, ind: str) -> str:
        head = "match " + self.expr(m.scrutinee, ind) + " {"
        if not m.arms and not self.take_peek(m.end):
            return head + "}"
        saved, self.out = self.out, []
        inner = ind + "  "
        prev = None
        for arm in m.arms:
            self.anchor(arm, inner, nested=self.nested(arm.body), prev_end=prev)
            p = arm.pattern
            pat = self.path(p.path) + (f"({p.binder.text})" if p.binder is not None else "")
            self.out.append(inner + pat + " => " + self.expr(arm.body, inner) + ",")
            prev = arm.end
        self.flush(m.end, inner)
        lines, self.out = self.out, saved
        return head + "\n" + "\n".join(lines) + "\n" + ind + "}"


def format_source(data: bytes, file: str = "main.bag") -> str:
    """Отформатировать файл; при ошибках разбора — FormatError с диагностиками (FMT-15)."""
    tree, toks, diags = parse(data, file)
    if diags or tree is None:
        raise FormatError(diags)
    return Printer(data, toks).file(tree)


# ------------------------------------------------------------ назначение ID (FMT-16)
def id_sites(tree: A.File):
    """Места, где SURF-07 требует @id: (узел с attrs, смещение начала строки вставки, встроенный ли атрибут)."""
    sites = [(tree.module, False)]
    for it in tree.items:
        sites.append((it, False))
        d = it.decl
        if isinstance(d, A.TypeDecl):
            sites += [(x, True) for x in d.fields + d.variants]
        elif isinstance(d, A.EventDecl):
            sites += [(x, True) for x in d.fields]
        elif isinstance(d, A.StoreDecl):
            sites += [(x, True) for x in d.tables]
        elif isinstance(d, A.ContractDecl):
            sites += [(x, True) for x in d.rules]
    return sites


def fresh_id(rng, taken: set) -> str:
    while True:
        v = "".join(rng.choice(CROCKFORD) for _ in range(6))
        if v not in taken:
            taken.add(v)
            return v


def assign_ids(data: bytes, file: str = "main.bag", taken: set | None = None, rng=None) -> bytes:
    """Вставить @id("…") во все обязательные места без него; taken — ID всего проекта (дополняется)."""
    tree, _, diags = parse(data, file)
    if diags or tree is None:
        raise FormatError(diags)
    rng = rng or random.SystemRandom()
    taken = taken if taken is not None else set()
    taken |= set(ID_ATTR.findall(data.decode("utf-8")))
    inserts = []
    for node, inline in id_sites(tree):
        if any(a.name.text == "id" for a in node.attrs):
            continue
        tag = f'@id("{fresh_id(rng, taken)}")'
        inserts.append((node.start, tag + (" " if inline else "\n")))
    out = data
    for pos, s in sorted(inserts, reverse=True):
        out = out[:pos] + s.encode("utf-8") + out[pos:]
    return out
