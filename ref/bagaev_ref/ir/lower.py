"""Понижение проверенного AST в BIR-1 (spec/ir/bir.md §2). Читает разрешения, которые записала проверка
(Project.ann, Project.types), и не разрешает имена заново.
"""
from __future__ import annotations

from bagaev_ref.ir import bir as B
from bagaev_ref.machine.values import NONE, Var
from bagaev_ref.sema import types as T
from bagaev_ref.sema.check import (BUILTIN_SUMS, LocalRef, TableRef, TypeRef, ValRef, VariantRef, flatten,
                                   is_primitive)
from bagaev_ref.sema.project import FnInfo, TypeInfo
from bagaev_ref.stdlib.prims import HOST_OPS, PRIMS
from bagaev_ref.syntax import ast as A

ARITH = {"+": "op.add@1", "-": "op.sub@1", "*": "op.mul@1", "/": "op.div@1", "%": "op.rem@1"}
COMPARE = {"==": "op.eq@1", "!=": "op.ne@1", "<": "op.lt@1", "<=": "op.le@1", ">": "op.gt@1", ">=": "op.ge@1"}


def prim_name(info: FnInfo) -> str:
    return f"{info.module.name}.{info.name}@1"


def ordinal(sum_, tag: str) -> int:
    if isinstance(sum_, str):
        return [t for t, _ in BUILTIN_SUMS[sum_]].index(tag)
    return [t for t, _ in sum_.variants].index(tag)


class Program:
    """Понижённый проект: функции модулей по FnInfo."""

    def __init__(self, project):
        self.project = project
        self.functions: dict = {}


class Lowerer:
    def __init__(self, project):
        self.p = project
        self.prog = Program(project)
        for m in project.modules.values():
            for info in m.values.values():
                if isinstance(info, FnInfo) and not (m.is_std and is_primitive(info)):
                    arity = len(info.params)
                    self.prog.functions[info] = B.Function(info.qname, arity, info)
        for info, fn in self.prog.functions.items():
            self.fn, self.counter, self.file = fn, 0, info.module.file
            d = info.decl
            params = list(getattr(d, "params", [])) + ([d.param] if hasattr(d, "param") else [])
            self.scope = [p.name.text for p in params]
            fn.body = self.expr(d.body)
            from bagaev_ref.machine.values import Clo
            fn.closure = Clo(fn.body, fn.arity, None, info.qname)

    # ------------------------------------------------------------ служебное
    def nid(self) -> str:
        self.counter += 1
        return f"{self.fn.qname}#{self.counter}"

    def site(self, node) -> tuple:
        return (self.file, node.start, node.end)

    def local(self, name: str, node) -> B.Local:
        i = len(self.scope) - 1 - max(k for k, n in enumerate(self.scope) if n == name)
        return B.Local(self.nid(), self.site(node), i, name)

    def ty(self, node):
        return T.zonk(self.p.types.get(id(node), T.TError()))

    # ------------------------------------------------------------ выражения
    def expr(self, e):
        m = getattr(self, "x_" + type(e).__name__)
        node = m(e)
        if getattr(node, "ty", None) is None:
            node.ty = self.ty(e)
        return node

    def x_Lit(self, e):
        return B.Const(self.nid(), self.site(e), None if e.kind == "unit" else e.value)

    def x_Paren(self, e):
        return self.expr(e.inner)

    def x_Var(self, e):
        return self.path(e)

    def x_FieldAccess(self, e):
        return self.path(e)

    def path(self, e):
        ann = self.p.ann.get(id(e))
        names = flatten(e)
        if ann is None:                                 # поле результата выражения: f(x).name
            target = self.expr(e.target)
            return B.Field(self.nid(), self.site(e), target, self.field_index(self.ty(e.target), e.name.text))
        _, ref, k = ann
        node, t = self.ref_value(ref, names, k, e)
        for nm in names[k:]:
            node = B.Field(self.nid(), self.site(e), node, self.field_index(t, nm.text))
            t = self.field_type(t, nm.text)
        return node

    def ref_value(self, ref, names, k, e):
        if isinstance(ref, LocalRef):
            return self.local(names[0].text, e), T.zonk(ref.type)
        if isinstance(ref, ValRef):
            return self.fn_value(ref.info, e), None
        if isinstance(ref, VariantRef):
            tag, ordn = ref.tag, ordinal(ref.sum, ref.tag)
            if self.has_payload(ref.sum, tag):
                body = B.Variant(self.nid(), self.site(e), tag, ordn, B.Local(self.nid(), self.site(e), 0, "$x"))
                return B.Lambda(self.nid(), self.site(e), 1, body), None
            return B.Const(self.nid(), self.site(e), Var(ordn, tag)), None
        if isinstance(ref, TypeRef):                    # конструктор opaque как значение
            body = B.Variant(self.nid(), self.site(e), ref.info.name, -1, B.Local(self.nid(), self.site(e), 0, "$x"))
            return B.Lambda(self.nid(), self.site(e), 1, body), None
        raise AssertionError(f"ссылка {ref!r} вне аргумента Table")

    @staticmethod
    def has_payload(sum_, tag) -> bool:
        if isinstance(sum_, str):
            return dict(BUILTIN_SUMS[sum_])[tag] is not None
        return dict(sum_.variants)[tag] is not None

    def fn_value(self, info: FnInfo, e):
        if info in self.prog.functions:
            return B.Global(self.nid(), self.site(e), self.prog.functions[info])
        n = len(info.params)                           # примитив std как значение — лямбда над ним
        args = [B.Local(self.nid(), self.site(e), n - 1 - i, f"$a{i}") for i in range(n)]
        return B.Lambda(self.nid(), self.site(e), n, self.prim(info, args, e))

    def prim(self, info: FnInfo, args, e, resource=None):
        name = prim_name(info)
        if name[:-2] in HOST_OPS:
            return B.Perform(self.nid(), self.site(e), name, resource, args)
        return B.Prim(self.nid(), self.site(e), name, args, PRIMS[name])

    @staticmethod
    def field_index(t, name: str) -> int:
        t = T.prune(t)
        return [n for n, _ in t.info.fields].index(name)

    @staticmethod
    def field_type(t, name: str):
        t = T.prune(t)
        return T.zonk(T.subst(dict(t.info.fields)[name], t.info.mapping(t.args)))

    def x_Call(self, e):
        ann = self.p.ann[id(e)]
        if ann[0] == "fn":
            info = ann[1]
            resource, args = None, []
            for a in e.args:
                aa = self.p.ann.get(id(a))
                if aa and aa[0] == "table":
                    resource = aa[1].qname
                    continue
                args.append(self.expr(a))
            if info in self.prog.functions:
                return B.Call(self.nid(), self.site(e), B.Global(self.nid(), self.site(e.fn), self.prog.functions[info]),
                              args)
            return self.prim(info, args, e, resource)
        if ann[0] == "construct":
            ref = ann[1]
            payload = self.expr(e.args[0])
            if isinstance(ref, TypeRef):
                return B.Variant(self.nid(), self.site(e), ref.info.name, -1, payload)
            return B.Variant(self.nid(), self.site(e), ref.tag, ordinal(ref.sum, ref.tag), payload)
        return B.Call(self.nid(), self.site(e), self.expr(e.fn), [self.expr(a) for a in e.args])

    def x_Block(self, b):
        saved = len(self.scope)
        node = self.block_rest(b, 0)
        del self.scope[saved:]
        return node

    def block_rest(self, b, i):
        """SURF-23: операторы — цепочка Let; блок без хвоста даёт ()."""
        if i == len(b.stmts):
            if b.tail is not None:
                return self.expr(b.tail)
            unit = B.Const(self.nid(), self.site(b), None)
            unit.ty = T.UNIT
            return unit
        st = b.stmts[i]
        if isinstance(st, A.Let):
            value, name = self.expr(st.value), st.name.text
        else:
            value, name = self.expr(st.expr), "_"
        nid = self.nid()
        self.scope.append(name)
        body = self.block_rest(b, i + 1)
        node = B.Let(nid, self.site(st), name, value, body)
        node.ty = body.ty if getattr(body, "ty", None) is not None else T.UNIT
        return node

    def x_If(self, e):
        els = self.expr(e.else_) if e.else_ is not None else B.Const(self.nid(), self.site(e), None)
        return B.If(self.nid(), self.site(e), self.expr(e.cond), self.expr(e.then), els)

    def x_Match(self, e):
        _, sum_ = self.p.ann[id(e)]
        scrut = self.expr(e.scrutinee)
        arms = {}
        for arm in e.arms:
            tag = self.p.ann[id(arm)]
            b = arm.pattern.binder
            bind = b is not None and b.text != "_"
            if bind:
                self.scope.append(b.text)
            arms[tag] = (bind, self.expr(arm.body))
            if bind:
                self.scope.pop()
        opaque = isinstance(sum_, TypeInfo) and sum_.kind == "opaque"
        return B.Match(self.nid(), self.site(e), scrut, arms, opaque)

    def x_Lambda(self, e):
        saved = len(self.scope)
        self.scope += [p.name.text for p in e.params]
        body = self.expr(e.body)
        del self.scope[saved:]
        return B.Lambda(self.nid(), self.site(e), len(e.params), body)

    def x_RecordLit(self, e):
        _, info = self.p.ann[id(e)]
        if info == "Map":
            items = []
            for en in e.entries:
                items += [self.expr(en.key), self.expr(en.value)]
            return B.MapBuild(self.nid(), self.site(e), items)
        return self.record(info, e.entries, e)

    def record(self, info: TypeInfo, entries, e):
        """SURF-26/27: значения полей в исходном порядке; с базой — сначала база, затем явные поля."""
        names = [n for n, _ in info.fields]
        base = next((en for en in entries if en.kind == "base"), None)
        if base is None:
            fields = [(names.index(en.name.text), self.expr(en.value)) for en in entries]
            return B.Record(self.nid(), self.site(e), fields, len(names))
        base_node, nid = self.expr(base.value), self.nid()
        self.scope.append("$base")
        explicit = [(names.index(en.name.text), self.expr(en.value)) for en in entries if en.kind == "field"]
        given = {s for s, _ in explicit}
        rest = [(s, B.Field(self.nid(), self.site(e), self.local("$base", e), s))
                for s in range(len(names)) if s not in given]
        self.scope.pop()
        return B.Let(nid, self.site(e), "$base", base_node, B.Record(self.nid(), self.site(e), explicit + rest,
                                                                      len(names)))

    def x_SeqLit(self, e):
        return B.SeqLit(self.nid(), self.site(e), [self.expr(x) for x in e.items])

    def x_Unary(self, e):
        if e.op == "-":
            if isinstance(e.operand, A.Lit) and e.operand.kind == "int" and e.operand.value is not None \
                    and e.operand.value >= 0:              # литерал MIN уже свёрнут разбором: −MIN — операция
                return B.Const(self.nid(), self.site(e), -e.operand.value)     # SURF-35: −N — константа
            return B.Prim(self.nid(), self.site(e), "op.neg@1", [self.expr(e.operand)], PRIMS["op.neg@1"])
        return B.Prim(self.nid(), self.site(e), "op.not@1", [self.expr(e.operand)], PRIMS["op.not@1"])

    def x_Binary(self, e):
        op = e.op
        if op == "and":                                 # SURF-33
            return B.If(self.nid(), self.site(e), self.expr(e.left), self.expr(e.right),
                        B.Const(self.nid(), self.site(e), False))
        if op == "or":
            return B.If(self.nid(), self.site(e), self.expr(e.left), B.Const(self.nid(), self.site(e), True),
                        self.expr(e.right))
        if op in ARITH:
            name = ARITH[op]
        elif op == "++":
            t = T.prune(self.ty(e.left))
            name = {"String": "op.concat_string@1", "Bytes": "op.concat_bytes@1", "Seq": "op.concat_seq@1"}[t.name]
        else:
            name = COMPARE[op]
        return B.Prim(self.nid(), self.site(e), name, [self.expr(e.left), self.expr(e.right)], PRIMS[name])

    def x_Try(self, e):
        """SURF-39: e? — Match с Return в ветви ошибки."""
        t = T.prune(self.ty(e.operand))
        scrut = self.expr(e.operand)
        x = B.Local(self.nid(), self.site(e), 0, "$x")
        if t.name == "Result":
            ret = B.Return(self.nid(), self.site(e), B.Variant(self.nid(), self.site(e), "Err", 1,
                                                                  B.Local(self.nid(), self.site(e), 0, "$y")))
            arms = {"Ok": (True, x), "Err": (True, ret)}
        else:
            arms = {"Some": (True, x), "None": (False, B.Return(self.nid(), self.site(e),
                                                                B.Const(self.nid(), self.site(e), NONE)))}
        return B.Match(self.nid(), self.site(e), scrut, arms)

    def x_Return(self, e):
        v = self.expr(e.value) if e.value is not None else B.Const(self.nid(), self.site(e), None)
        return B.Return(self.nid(), self.site(e), v)

    def x_Emit(self, e):
        _, info = self.p.ann[id(e)]
        rec = self.record(info, e.entries, e)
        return B.Perform(self.nid(), self.site(e), "event.emit@1", info.qname, [rec])


def lower(project) -> Program:
    return Lowerer(project).prog
