"""Парсер bagaev по spec/language/grammar.ebnf и правилам разбора surface.md §6 (SURF-50…SURF-59).

Рекурсивный спуск для деклараций и Pratt-подобная лестница приоритетов для выражений. Условие if и
выражение match разбираются в режиме cond — без литерала записи на верхнем уровне (SURF-52).
Ошибка внутри декларации записывается, разбор продолжается со следующей декларации верхнего уровня.
"""
from __future__ import annotations

from bagaev_ref.diag import Diagnostic
from bagaev_ref.syntax import ast as A
from bagaev_ref.syntax.lexer import Token, lex

ITEM_WORDS = {"type", "entity", "contract", "store", "event", "command", "handler", "query", "migration", "test"}
CMP_OPS = {"==", "!=", "<", "<=", ">", ">="}
LINK_WORDS = {"implements", "requires", "checks"}
EFFECT_WORDS = {"reads", "writes", "emits", "host"}
EXPR_START_KW = {"if", "match", "true", "false", "not", "fn", "return", "emit"}
INT_MIN_MAGNITUDE = 2**63


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, toks: list[Token], file: str):
        self.toks, self.file, self.i = toks, file, 0
        self.diags: list[Diagnostic] = []
        depth, self.depth = 0, []
        for t in toks:
            if t.text in ("}", ")", "]") and t.kind == "PUNCT":
                depth = max(0, depth - 1)
            self.depth.append(depth)
            if t.text in ("{", "(", "[") and t.kind == "PUNCT":
                depth += 1

    # ------------------------------------------------------------ токены
    @property
    def tok(self) -> Token:
        return self.toks[self.i]

    def peek(self, k: int = 1) -> Token:
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def at(self, text: str) -> bool:
        return self.tok.is_(text)

    def at_word(self, text: str) -> bool:
        return self.tok.kind == "IDENT" and self.tok.text == text

    def advance(self) -> Token:
        t = self.tok
        if t.kind != "EOF":
            self.i += 1
        return t

    def diag(self, code: str, start: int, end: int, **data):
        self.diags.append(Diagnostic(code, "parse", self.file, start, end, data))

    def fail(self, expected: list[str]):
        t = self.tok
        if t.kind == "EOF":
            self.diag("UNEXPECTED_EOF", t.start, t.start, expected=expected)
        else:
            self.diag("UNEXPECTED_TOKEN", t.start, t.end, expected=expected)
        raise ParseError()

    def expect(self, text: str) -> Token:
        if self.at(text):
            return self.advance()
        if text == ">" and self.tok.text == ">=" and self.tok.kind == "PUNCT":   # TypeArgsClose
            t = self.tok
            self.toks[self.i] = Token("PUNCT", "=", t.start + 1, t.end, None, [])
            return Token("PUNCT", ">", t.start, t.start + 1, None, t.leading)
        self.fail([text])

    def expect_word(self, text: str) -> Token:
        if self.at_word(text):
            return self.advance()
        self.fail([text])

    def name(self) -> A.Name:
        t = self.tok
        if t.kind == "IDENT":
            self.advance()
            return A.Name(t.start, t.end, t.text)
        if t.kind == "KW":
            self.diag("RESERVED_WORD_AS_NAME", t.start, t.end, word=t.text)
            self.advance()
            return A.Name(t.start, t.end, t.text)
        self.fail(["IDENT"])

    def path(self) -> list[A.Name]:
        out = [self.name()]
        while self.at(".") and self.peek().kind in ("IDENT", "KW"):
            self.advance()
            out.append(self.name())
        return out

    def comma_list(self, close: str, item):
        out = []
        while not self.at(close):
            out.append(item())
            if self.at(","):
                self.advance()
                continue
            break
        return out

    # ------------------------------------------------------------ файл
    def parse_file(self) -> A.File:
        start = self.tok.start
        module = self.module_header()
        uses = []
        while self.at("use"):
            try:
                uses.append(self.use_decl())
            except ParseError:
                self.recover()
        items = []
        while self.tok.kind != "EOF":
            try:
                items.append(self.item())
            except ParseError:
                self.recover()
        return A.File(start, self.tok.end, module, uses, items)

    def recover(self):
        """Пропустить токены до начала следующей декларации верхнего уровня."""
        self.advance()
        while self.tok.kind != "EOF":
            t = self.tok
            if self.depth[self.i] == 0 and (t.is_("@") or t.is_("pub") or t.is_("fn") or t.is_("use")
                                            or (t.kind == "IDENT" and t.text in ITEM_WORDS
                                                and self.peek().kind == "IDENT")):
                return
            self.advance()

    def docs(self, tok: Token) -> list[str]:
        return [tv.text[3:].strip() for tv in tok.leading if tv.kind == "doc"]

    def attrs(self) -> list[A.Attr]:
        out = []
        while self.at("@"):
            at = self.advance()
            nm = self.name()
            self.expect("(")
            args = []
            if self.at(")"):
                self.fail(["STRING", "INT", "IDENT"])          # AttrArg хотя бы один (GRAMMAR-1)
            while not self.at(")"):
                t = self.tok
                if t.kind in ("STRING", "INT", "IDENT"):
                    self.advance()
                    args.append((t.kind, t.value if t.kind != "IDENT" else t.text, t.start, t.end))
                else:
                    self.fail(["STRING", "INT", "IDENT"])
                if self.at(","):
                    self.advance()
                    continue
                break
            end = self.expect(")").end
            out.append(A.Attr(at.start, end, nm, args))
        return out

    def module_header(self) -> A.ModuleHeader:
        first = self.tok
        try:
            attrs = self.attrs()
            kw = self.expect("module")
            path = self.path()
            return A.ModuleHeader(first.start, path[-1].end, attrs, path, self.docs(first))
        except ParseError:
            self.recover()
            return A.ModuleHeader(first.start, first.start, [], [], [])

    def use_decl(self) -> A.UseDecl:
        kw = self.advance()
        path = [self.name()]
        group, alias, end = None, None, path[-1].end
        while self.at("."):
            dot = self.advance()
            if group is not None:
                self.diag("INVALID_USE_GROUP", dot.start, dot.end)
            if self.at("{"):
                self.advance()
                if self.at("}"):
                    self.fail(["IDENT"])                       # UseName хотя бы одно
                group = self.comma_list("}", self.use_name)
                end = self.expect("}").end
            else:
                nm = self.name()
                path.append(nm)
                end = nm.end
        if self.at("as"):
            as_tok = self.advance()
            if group is not None:
                self.diag("INVALID_USE_GROUP", as_tok.start, as_tok.end)
            alias = self.name()
            end = alias.end
        return A.UseDecl(kw.start, end, path, group, alias)

    def use_name(self) -> A.UseName:
        nm = self.name()
        alias = None
        if self.at("as"):
            self.advance()
            alias = self.name()
        return A.UseName(nm.start, (alias or nm).end, nm, alias)

    # ------------------------------------------------------------ декларации
    def item(self) -> A.Item:
        first = self.tok
        attrs = self.attrs()
        pub, pub_at = False, -1
        if self.at("pub"):
            pub_at = self.advance().start
            pub = True
        t = self.tok
        if t.is_("fn"):
            decl = self.fn_decl()
        elif t.kind == "IDENT" and t.text in ITEM_WORDS and self.peek().kind in ("IDENT", "KW"):
            decl = getattr(self, f"{t.text}_decl")()
        else:
            self.fail(["fn", *sorted(ITEM_WORDS)])
        return A.Item(first.start, decl.end, attrs, pub, self.docs(first), decl, pub_at)

    def generics(self, effects: bool = True) -> list[A.GenericParam]:
        """Обобщения функции; effects=False — параметры типа объявления type (эффект-переменных нет)."""
        if not self.at("<"):
            return []
        self.advance()
        if self.at(">"):
            self.fail(["!", "IDENT"] if effects else ["IDENT"])

        def one():
            s = self.tok.start
            if self.at("!") and effects:
                self.advance()
                nm = self.name()
                return A.GenericParam(s, nm.end, nm, [], True)
            nm = self.name()
            bounds = []
            if self.at(":"):
                self.advance()
                bounds.append(self.name())
                while self.at("+"):
                    self.advance()
                    bounds.append(self.name())
            return A.GenericParam(s, (bounds[-1] if bounds else nm).end, nm, bounds, False)
        out = self.comma_list(">", one)
        self.expect(">")
        return out

    def param(self) -> A.Param:
        nm = self.name()
        self.expect(":")
        ty = self.type_expr()
        return A.Param(nm.start, ty.end, nm, ty)

    def params(self) -> list[A.Param]:
        self.expect("(")
        out = self.comma_list(")", self.param)
        self.expect(")")
        return out

    def uses(self):
        if not self.at_word("uses"):
            return None
        self.advance()
        return self.effect_row()

    def effect_row(self) -> A.EffectRow:
        s = self.tok.start
        if self.tok.kind == "IDENT" and not self.at("{"):
            nm = self.name()
            return A.EffectRow(s, nm.end, [], nm)
        self.expect("{")
        items, var = [], None
        while self.tok.kind == "IDENT" and self.tok.text in EFFECT_WORDS:
            k = self.advance()
            p = self.path()
            items.append(A.EffectItem(k.start, p[-1].end, k.text, p))
            if self.at(","):
                self.advance()
                continue
            break
        if self.at("|"):
            self.advance()
            var = self.name()
        end = self.expect("}").end
        return A.EffectRow(s, end, items, var)

    def links(self) -> list[A.LinkClause]:
        out = []
        while self.tok.kind == "IDENT" and self.tok.text in LINK_WORDS | {"supersedes"}:
            k = self.advance()
            targets, end = [], k.end
            while True:
                if k.text == "supersedes":
                    t = self.tok
                    if t.kind != "STRING":
                        self.fail(["STRING"])
                    self.advance()
                    targets.append((t.value, t.start, t.end))
                    end = t.end
                else:
                    p = self.path()
                    targets.append(p)
                    end = p[-1].end
                if self.at(","):
                    self.advance()
                    continue
                break
            out.append(A.LinkClause(k.start, end, k.text, targets))
        return out

    def fn_decl(self) -> A.FnDecl:
        kw = self.advance()
        nm = self.name()
        gens = self.generics()
        ps = self.params()
        self.expect("->")
        ret = self.type_expr()
        row = self.uses()
        links = self.links()
        body = self.block()
        return A.FnDecl(kw.start, body.end, nm, gens, ps, ret, row, links, body)

    def _entry(self, kind: str) -> A.EntryDecl:
        kw = self.advance()
        nm = self.name()
        ps = self.params()
        self.expect("->")
        ret = self.type_expr()
        row = self.uses()
        links = self.links()
        body = self.block()
        return A.EntryDecl(kw.start, body.end, kind, nm, ps, ret, row, links, body)

    def command_decl(self):
        return self._entry("command")

    def query_decl(self):
        return self._entry("query")

    def handler_decl(self) -> A.HandlerDecl:
        kw = self.advance()
        nm = self.name()
        self.expect("(")
        p = self.param()
        self.expect(")")
        row = self.uses()
        links = self.links()
        body = self.block()
        return A.HandlerDecl(kw.start, body.end, nm, p, row, links, body)

    def migration_decl(self) -> A.MigrationDecl:
        kw = self.advance()
        nm = self.name()
        self.expect_word("on")
        table = self.path()
        self.expect("(")
        p = self.param()
        self.expect(")")
        self.expect("->")
        ret = self.type_expr()
        body = self.block()
        return A.MigrationDecl(kw.start, body.end, nm, table, p, ret, body)

    def test_decl(self) -> A.TestDecl:
        kw = self.advance()
        nm = self.name()
        row = self.uses()
        links = self.links()
        body = self.block()
        return A.TestDecl(kw.start, body.end, nm, row, links, body)

    def type_decl(self) -> A.TypeDecl:
        kw = self.advance()
        nm = self.name()
        params = self.generics(effects=False)
        self.expect("=")
        fields, variants, rep = [], [], None
        if self.at_word("record"):
            self.advance()
            self.expect("{")
            fields = self.comma_list("}", self.field_decl)
            end = self.expect("}").end
            kind = "record"
        elif self.at_word("enum"):
            self.advance()
            self.expect("{")
            if self.at("}"):
                self.fail(["@", "IDENT"])                      # хотя бы один вариант (SURF-10)
            variants = self.comma_list("}", self.variant_decl)
            end = self.expect("}").end
            kind = "enum"
        elif self.at_word("opaque"):
            self.advance()
            rep = self.type_expr()
            end = rep.end
            kind = "opaque"
        else:
            self.fail(["record", "enum", "opaque"])
        return A.TypeDecl(kw.start, end, nm, params, kind, fields, variants, rep)

    def field_decl(self) -> A.FieldDecl:
        s = self.tok.start
        attrs = self.attrs()
        nm = self.name()
        self.expect(":")
        ty = self.type_expr()
        return A.FieldDecl(s, ty.end, attrs, nm, ty)

    def variant_decl(self) -> A.VariantDecl:
        s = self.tok.start
        attrs = self.attrs()
        nm = self.name()
        payload, end = None, nm.end
        if self.at("("):
            self.advance()
            payload = self.type_expr()
            end = self.expect(")").end
        return A.VariantDecl(s, end, attrs, nm, payload)

    def string_list(self) -> list[str]:
        self.expect("[")
        out = []
        while not self.at("]"):
            t = self.tok
            if t.kind != "STRING":
                self.fail(["STRING"])
            self.advance()
            out.append(t.value)
            if self.at(","):
                self.advance()
                continue
            break
        self.expect("]")
        return out

    def entity_decl(self) -> A.EntityDecl:
        kw = self.advance()
        nm = self.name()
        self.expect("{")
        purpose, terms, not_about = None, [], []
        while not self.at("}"):
            if self.at_word("purpose"):
                self.advance()
                t = self.tok
                if t.kind != "STRING":
                    self.fail(["STRING"])
                self.advance()
                purpose = t.value
            elif self.at_word("terms"):
                self.advance()
                terms = self.string_list()
            elif self.at_word("not_about"):
                self.advance()
                not_about = self.string_list()
            else:
                self.fail(["purpose", "terms", "not_about", "}"])
        end = self.expect("}").end
        return A.EntityDecl(kw.start, end, nm, purpose, terms, not_about)

    def contract_decl(self) -> A.ContractDecl:
        kw = self.advance()
        nm = self.name()
        self.expect_word("about")
        about = self.path()
        self.expect("{")
        rules = []
        while not self.at("}"):
            s = self.tok.start
            attrs = self.attrs()
            self.expect_word("rule")
            rn = self.name()
            t = self.tok
            if t.kind != "STRING":
                self.fail(["STRING"])
            self.advance()
            rules.append(A.RuleDecl(s, t.end, attrs, rn, t.value))
        end = self.expect("}").end
        return A.ContractDecl(kw.start, end, nm, about, rules)

    def store_decl(self) -> A.StoreDecl:
        kw = self.advance()
        nm = self.name()
        self.expect("{")
        tables = []
        while not self.at("}"):
            s = self.tok.start
            attrs = self.attrs()
            self.expect_word("table")
            tn = self.name()
            self.expect(":")
            ty = self.type_expr()
            derived, end = None, ty.end
            if self.at_word("derived_from"):
                self.advance()
                derived = self.path()
                end = derived[-1].end
            tables.append(A.TableDecl(s, end, attrs, tn, ty, derived))
        end = self.expect("}").end
        return A.StoreDecl(kw.start, end, nm, tables)

    def event_decl(self) -> A.EventDecl:
        kw = self.advance()
        nm = self.name()
        self.expect("{")
        fields = self.comma_list("}", self.field_decl)
        end = self.expect("}").end
        return A.EventDecl(kw.start, end, nm, fields)

    # ------------------------------------------------------------ типы
    def type_expr(self):
        t = self.tok
        if t.is_("fn"):
            self.advance()
            self.expect("(")
            ps = self.comma_list(")", self.type_expr)
            self.expect(")")
            self.expect("->")
            ret = self.type_expr()
            row, end = None, ret.end
            if self.at_word("uses"):
                self.advance()
                row = self.effect_row()
                end = row.end
            return A.FnType(t.start, end, ps, ret, row)
        if t.is_("("):
            self.advance()
            if self.at(")"):
                end = self.advance().end
                return A.UnitType(t.start, end)
            inner = self.type_expr()
            self.expect(")")
            return inner
        p = self.path()
        args, end = [], p[-1].end
        if self.at("<"):
            self.advance()
            if self.at(">") or self.tok.text == ">=":
                self.fail(["fn", "(", "IDENT"])                # TypeArgs хотя бы один
            args = self.comma_list(">", self.type_expr)
            end = self.expect(">").end
        return A.TypePath(p[0].start, end, p, args)

    # ------------------------------------------------------------ блоки
    def block(self) -> A.Block:
        lb = self.expect("{")
        stmts, tail = [], None
        while not self.at("}"):
            if self.tok.kind == "EOF":
                self.fail(["}"])
            if self.at("let"):
                stmts.append(self.let())
                continue
            if self.at("if") or self.at("match") or self.at("{"):
                e = self.block_like()
                if self.at(";"):
                    self.advance()
                    stmts.append(A.ExprStmt(e.start, e.end, e, True))
                    continue
                if self.at("}"):
                    tail = e
                    break
                stmts.append(A.ExprStmt(e.start, e.end, e, False))
                continue
            e = self.expr()
            if self.at(";"):
                semi = self.advance()
                stmts.append(A.ExprStmt(e.start, semi.end, e, True))
                continue
            if self.at("}"):
                tail = e
                break
            self.fail([";", "}"])
        rb = self.expect("}")
        return A.Block(lb.start, rb.end, stmts, tail)

    def block_like(self):
        if self.at("if"):
            return self.if_expr()
        if self.at("match"):
            return self.match_expr()
        return self.block()

    def let(self) -> A.Let:
        kw = self.advance()
        if self.at("_"):
            t = self.advance()
            nm = A.Name(t.start, t.end, "_")
        else:
            nm = self.name()
        ty = None
        if self.at(":"):
            self.advance()
            ty = self.type_expr()
        self.expect("=")
        val = self.expr()
        semi = self.expect(";")
        return A.Let(kw.start, semi.end, nm, ty, val)

    # ------------------------------------------------------------ выражения
    def expr(self, cond: bool = False):
        t = self.tok
        if not cond:
            if t.is_("return"):
                self.advance()
                if self.tok.kind == "EOF" or self.tok.text in (";", "}", ",", ")", "]"):
                    return A.Return(t.start, t.end, None)
                v = self.expr()
                return A.Return(t.start, v.end, v)
            if t.is_("emit"):
                self.advance()
                ev = self.path()
                lb = self.tok
                entries, end = self.record_body()
                return A.Emit(t.start, end, ev, entries, lb.start)
            if t.is_("fn"):
                return self.lambda_()
        return self.logic(cond)

    def lambda_(self) -> A.Lambda:
        kw = self.advance()
        self.expect("(")

        def one():
            nm = self.name()
            ty = None
            if self.at(":"):
                self.advance()
                ty = self.type_expr()
            return A.LambdaParam(nm.start, (ty or nm).end, nm, ty)
        ps = self.comma_list(")", one)
        self.expect(")")
        self.expect("=>")
        body = self.expr()
        return A.Lambda(kw.start, body.end, ps, body)

    def logic(self, cond: bool):
        """Цепочка and/or: and связывает сильнее; смешение без скобок → MIXED_AND_OR (SURF-53)."""
        operands = [self.not_(cond)]
        ops = []
        while self.at("and") or self.at("or"):
            op = self.advance()
            ops.append(op)
            operands.append(self.not_(cond))
        if not ops:
            return operands[0]
        kinds = {o.text for o in ops}
        if len(kinds) > 1:
            other = next(o for o in ops if o.text != ops[0].text)
            self.diag("MIXED_AND_OR", other.start, other.end)
        terms, or_ops = [operands[0]], []          # and сильнее or
        for op, rhs in zip(ops, operands[1:]):
            if op.text == "and":
                last = terms[-1]
                terms[-1] = A.Binary(last.start, rhs.end, "and", last, rhs, op.start)
            else:
                or_ops.append(op)
                terms.append(rhs)
        res = terms[0]
        for op, term in zip(or_ops, terms[1:]):
            res = A.Binary(res.start, term.end, "or", res, term, op.start)
        return res

    def not_(self, cond: bool):
        if self.at("not"):
            t = self.advance()
            e = self.not_(cond)
            return A.Unary(t.start, e.end, "not", e)
        return self.cmp(cond)

    def cmp(self, cond: bool):
        left = self.concat(cond)
        if self.tok.kind == "PUNCT" and self.tok.text in CMP_OPS:
            op = self.advance()
            right = self.concat(cond)
            left = A.Binary(left.start, right.end, op.text, left, right, op.start)
            while self.tok.kind == "PUNCT" and self.tok.text in CMP_OPS:
                op2 = self.advance()
                self.diag("NONASSOC_COMPARISON", op2.start, op2.end)
                r2 = self.concat(cond)
                left = A.Binary(left.start, r2.end, op2.text, left, r2, op2.start)
        return left

    def _binary_level(self, ops: set, nxt, cond):
        left = nxt(cond)
        while self.tok.kind == "PUNCT" and self.tok.text in ops:
            op = self.advance()
            right = nxt(cond)
            left = A.Binary(left.start, right.end, op.text, left, right, op.start)
        return left

    def concat(self, cond):
        return self._binary_level({"++"}, self.add, cond)

    def add(self, cond):
        return self._binary_level({"+", "-"}, self.mul, cond)

    def mul(self, cond):
        return self._binary_level({"*", "/", "%"}, self.unary, cond)

    def unary(self, cond):
        if self.at("-"):
            t = self.advance()
            nxt = self.tok
            if nxt.kind == "INT" and nxt.value == INT_MIN_MAGNITUDE:
                self.advance()
                return self.postfix_after(A.Lit(t.start, nxt.end, "int", -INT_MIN_MAGNITUDE), cond)
            e = self.unary(cond)
            return A.Unary(t.start, e.end, "-", e)
        return self.postfix(cond)

    def postfix(self, cond):
        return self.postfix_after(self.primary(cond), cond)

    @staticmethod
    def is_path(e) -> bool:
        while isinstance(e, A.FieldAccess):
            e = e.target
        return isinstance(e, A.Var)

    def postfix_after(self, e, cond):
        while True:
            if self.at("("):
                self.advance()
                args = self.comma_list(")", self.expr)
                end = self.expect(")").end
                e = A.Call(e.start, end, e, args)
            elif self.at(".") and self.peek().kind in ("IDENT", "KW"):
                self.advance()
                nm = self.name()
                e = A.FieldAccess(e.start, nm.end, e, nm)
            elif self.at("?"):
                q = self.advance()
                e = A.Try(e.start, q.end, e)
            elif self.at("{"):
                lb = self.tok
                if cond:
                    a, b = self.peek(1), self.peek(2)
                    if self.is_path(e) and ((a.kind == "IDENT" and b.is_(":")) or a.is_("..")):
                        self.diag("RECORD_LITERAL_IN_CONDITION", lb.start, lb.end)
                    else:
                        return e
                elif not self.is_path(e):
                    self.diag("RECORD_LITERAL_NOT_AFTER_PATH", lb.start, lb.end)
                entries, end = self.record_body()
                e = A.RecordLit(e.start, end, e, entries, lb.start)
            else:
                return e

    def record_body(self):
        self.expect("{")
        entries = []
        kinds = []
        while not self.at("}"):
            s = self.tok.start
            if self.at(".."):
                self.advance()
                v = self.expr()
                ent = A.RecordEntry(s, v.end, "base", None, None, v)
            elif self.tok.kind == "IDENT" and self.peek().is_(":"):
                nm = self.name()
                self.advance()
                v = self.expr()
                ent = A.RecordEntry(s, v.end, "field", nm, None, v)
            else:
                k = self.expr()
                self.expect("=>")
                v = self.expr()
                ent = A.RecordEntry(s, v.end, "pair", None, k, v)
            kind = "map" if ent.kind == "pair" else "record"
            if kinds and kind != kinds[0]:
                self.diag("MIXED_RECORD_ENTRIES", ent.start, ent.end)
            kinds.append(kind)
            entries.append(ent)
            if self.at(","):
                self.advance()
                continue
            break
        end = self.expect("}").end
        if entries and all(e.kind == "base" for e in entries):
            self.diag("RECORD_UPDATE_WITHOUT_FIELDS", entries[0].start, entries[0].end)
        return entries, end

    def primary(self, cond):
        t = self.tok
        if t.kind == "INT":
            self.advance()
            if t.value == INT_MIN_MAGNITUDE:
                self.diag("INT_LITERAL_OUT_OF_RANGE", t.start, t.end)
            return A.Lit(t.start, t.end, "int", t.value)
        if t.kind == "STRING":
            self.advance()
            return A.Lit(t.start, t.end, "string", t.value)
        if t.kind == "BYTES":
            self.advance()
            return A.Lit(t.start, t.end, "bytes", t.value)
        if t.is_("true") or t.is_("false"):
            self.advance()
            return A.Lit(t.start, t.end, "bool", t.text == "true")
        if t.kind == "IDENT":
            self.advance()
            return A.Var(t.start, t.end, A.Name(t.start, t.end, t.text))
        if t.is_("("):
            self.advance()
            if self.at(")"):
                end = self.advance().end
                return A.Lit(t.start, end, "unit", None)
            inner = self.expr()
            end = self.expect(")").end
            return A.Paren(t.start, end, inner)
        if t.is_("["):
            self.advance()
            items = self.comma_list("]", self.expr)
            end = self.expect("]").end
            return A.SeqLit(t.start, end, items)
        if t.is_("{"):
            return self.block()
        if t.is_("if"):
            return self.if_expr()
        if t.is_("match"):
            return self.match_expr()
        self.fail(["выражение"])

    def if_expr(self) -> A.If:
        kw = self.advance()
        c = self.expr(cond=True)
        then = self.block()
        else_, end = None, then.end
        if self.at("else"):
            self.advance()
            else_ = self.if_expr() if self.at("if") else self.block()
            end = else_.end
        return A.If(kw.start, end, c, then, else_)

    def match_expr(self) -> A.Match:
        kw = self.advance()
        scrut = self.expr(cond=True)
        self.expect("{")
        arms = []
        while not self.at("}"):
            pat = self.pattern()
            self.expect("=>")
            body = self.expr()
            arms.append(A.Arm(pat.start, body.end, pat, body))
            if self.at(","):
                self.advance()
                continue
            if self.at("}"):
                break
            if not isinstance(body, A.Block):
                self.diag("MISSING_COMMA_IN_MATCH", body.end, body.end)
        end = self.expect("}").end
        return A.Match(kw.start, end, scrut, arms)

    def pattern(self) -> A.Pattern:
        p = self.path()
        binder, end = None, p[-1].end
        if self.at("("):
            self.advance()
            if self.at("_"):
                t = self.advance()
                binder = A.Name(t.start, t.end, "_")
            else:
                binder = self.name()
            end = self.expect(")").end
        return A.Pattern(p[0].start, end, p, binder)


def parse(data: bytes, file: str = "main.bag"):
    """Лексика и разбор. Возвращает (File | None, токены, диагностики lex+parse)."""
    toks, ldiags = lex(data, file)
    if ldiags and ldiags[0].code in ("SOURCE_BOM", "INVALID_UTF8"):
        return None, toks, ldiags
    p = Parser(toks, file)
    tree = p.parse_file()
    return tree, toks, ldiags + p.diags
