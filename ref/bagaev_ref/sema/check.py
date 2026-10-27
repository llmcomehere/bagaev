"""Проверка тел: разрешение имён в выражениях, типы (TYPES-0.1 §5–§9), эффекты (EFFECTS-1 EFF-04…EFF-09).

Порядок, границы финализации и диапазоны диагностик — spec/language/checking.md §5–§7.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from bagaev_ref.diag import make
from bagaev_ref.sema import types as T
from bagaev_ref.sema.project import (FnInfo, ModuleInfo, Project, Scope, StoreInfo, TableInfo, TypeInfo,
                                     span_of)
from bagaev_ref.syntax import ast as A

BUILTIN_SUMS = {"Option": [("None", None), ("Some", 0)], "Result": [("Ok", 0), ("Err", 1)]}
BUILTIN_SUM_PARAMS = {"Option": ["T"], "Result": ["T", "E"]}
BUILTIN_VARIANT_OF = {"None": "Option", "Some": "Option", "Ok": "Result", "Err": "Result"}
ENTRY = {"command", "query", "handler", "migration", "test"}


# ------------------------------------------------------------ результаты разрешения путей
@dataclass
class LocalRef:
    type: object


@dataclass
class ValRef:
    info: object                   # FnInfo | StoreInfo


@dataclass
class TableRef:
    table: TableInfo


@dataclass
class TypeRef:
    info: object                   # TypeInfo | "Option" | "Result"


@dataclass
class VariantRef:
    sum: object                    # TypeInfo | "Option" | "Result"
    tag: str


@dataclass
class Ctx:
    """Объемлющая функция или лямбда: тип результата для return/? и фактические эффекты с местами."""
    ret: object
    effects: list = field(default_factory=list)       # (атом, start, end)


def flatten(e):
    names = []
    while isinstance(e, A.FieldAccess):
        names.insert(0, e.name)
        e = e.target
    if isinstance(e, A.Var):
        names.insert(0, e.name)
        return names
    return None


def sum_name(sum_) -> str:
    return sum_ if isinstance(sum_, str) else sum_.qname


class Checker:
    def __init__(self, project: Project, m: ModuleInfo):
        self.p, self.m = project, m
        self.pending: list = []
        self.locals: dict = {}
        self.scope = Scope()
        self.ctx = Ctx(T.UNIT)

    def err(self, code: str, start: int, end: int, **data):
        self.p.diags.append(make(code, self.m.file, start, end, **data))

    def unify_at(self, exp, act, node) -> bool:
        try:
            T.unify(exp, act, (node.start, node.end))
            return True
        except T.UnifyError as e:
            self.err(e.code, node.start, node.end, **e.data)
            return False

    # ------------------------------------------------------------ объявления модуля
    def check_module(self):
        for it in self.m.tree.items:
            info = self.m.values.get(getattr(it.decl, "name", A.Name(0, 0, "")).text)
            if isinstance(info, FnInfo) and info.decl is it.decl:
                if self.m.is_std and is_primitive(info):
                    continue                                # тело std `{}` — примитив машины (MACHINE-1)
                self.check_fn(info)

    def check_fn(self, info: FnInfo):
        d = info.decl
        self.scope = Scope({p.name: p for p in info.tparams}, dict(info.eparams))
        params = list(getattr(d, "params", [])) + ([d.param] if hasattr(d, "param") else [])
        self.locals = {p.name.text: t for p, t in zip(params, info.params)}
        self.ctx = Ctx(info.ret)
        mark = len(self.pending)
        self.infer(d.body, info.ret)
        self.finalize(mark)
        actual = self.ctx.effects
        if info.kind == "handler":
            actual = actual + [(a, d.param.start, d.param.end) for a in info.row.atoms if a[0] == "consumes"]
        self.require_effects(actual, info.row.atoms)
        info.actual = frozenset(a for a, _, _ in actual)

    def require_effects(self, actual: list, declared: frozenset):
        """EFF-04: фактические атомы ⊆ объявленных; место — первое по исходнику место лишнего атома."""
        extra = [(a, s, e) for a, s, e in actual if a not in declared]
        if extra:
            atoms = T.sorted_atoms({a for a, _, _ in extra})
            _, s, e = min(extra, key=lambda x: (x[1], x[2]))
            self.err("UNDECLARED_EFFECT", s, e, atoms=[T.show_atom(a) for a in atoms])

    # ------------------------------------------------------------ финализация (TYPES-0.1 §5, §7)
    def new_meta(self, start: int, end: int, param: str) -> T.TMeta:
        mt = T.TMeta(site=(start, end, param))
        self.pending.append(("meta", mt))
        return mt

    def need_bound(self, t, bound: str, node):
        self.pending.append(("bound", t, bound, node.start, node.end))

    def finalize(self, mark: int):
        items, self.pending[mark:] = self.pending[mark:], []
        sites = set()
        for it in items:
            if it[0] == "meta":
                mt = it[1]
                if isinstance(T.prune(mt), T.TMeta):
                    s, e, param = mt.site
                    if (s, e) not in sites:
                        sites.add((s, e))
                        self.err("AMBIGUOUS_TYPE_ARGUMENT", s, e, param=param)
                    T.prune(mt).ref = T.TError()
            elif it[0] == "lambda":
                mt = it[1]
                if isinstance(T.prune(mt), T.TMeta):
                    name, s, e = mt.lambda_param
                    self.err("PARAMETER_TYPE_REQUIRED", s, e, name=name)
                    T.prune(mt).ref = T.TError()
            elif it[0] == "row":
                self.solve_row(it[1])                           # ρ(e), не заданная аргументами, пуста (EFF-06)
            elif it[0] == "bound":
                _, t, bound, s, e = it
                if T.satisfies(t, bound) is False:
                    self.err("BOUND_NOT_SATISFIED", s, e, type=T.show(T.zonk(t)), bound=bound)

    def known(self, t, node) -> object:
        """Операнд, тип которого должен быть известен (TYPES-0.1 §7): meta параметра лямбды → PARAMETER_TYPE_REQUIRED."""
        t = T.prune(t)
        if isinstance(t, T.TMeta) and t.lambda_param is not None:
            name = t.lambda_param[0]
            self.err("PARAMETER_TYPE_REQUIRED", node.start, node.end, name=name)
            t.ref = T.TError()
            return t.ref
        return t

    # ------------------------------------------------------------ пути
    def resolve(self, names):
        """SURF-06: разрешить префикс пути. Возвращает (ссылка, число поглощённых сегментов) или (None, 0)."""
        first = names[0]
        ref, k = None, 1
        if first.text in self.locals:
            return LocalRef(self.locals[first.text]), 1
        val = self.p.lookup(self.m, "values", first.text)
        typ = self.p.lookup(self.m, "types", first.text)
        if val is not None:
            ref = ValRef(val)
        elif typ is not None:
            ref = TypeRef(typ)
        elif first.text in self.m.aliases:
            target = self.m.aliases[first.text]
            if len(names) < 2:
                self.err("UNKNOWN_NAME", first.start, first.end, name=first.text)
                return None, 0
            nm = names[1]
            info = target.values.get(nm.text) or target.types.get(nm.text)
            if info is None:
                self.err("UNKNOWN_NAME", nm.start, nm.end, name=nm.text)
                return None, 0
            if not info.pub:
                self.err("PRIVATE_ITEM", nm.start, nm.end, name=nm.text, module=target.name)
                return None, 0
            ref, k = (TypeRef(info) if isinstance(info, TypeInfo) else ValRef(info)), 2
        elif first.text in BUILTIN_VARIANT_OF:
            ref = VariantRef(BUILTIN_VARIANT_OF[first.text], first.text)
        elif first.text in BUILTIN_SUMS:
            ref = TypeRef(first.text)
        else:
            self.err("UNKNOWN_NAME", first.start, first.end, name=first.text)
            return None, 0
        while k < len(names):
            nm = names[k]
            if isinstance(ref, ValRef) and isinstance(ref.info, StoreInfo):
                tbl = ref.info.tables.get(nm.text)
                if tbl is None:
                    self.err("UNKNOWN_NAME", nm.start, nm.end, name=nm.text)
                    return None, 0
                ref, k = TableRef(tbl), k + 1
                continue
            if isinstance(ref, TypeRef):
                tags = self.tags(ref.info)
                if nm.text not in tags:
                    self.err("UNKNOWN_VARIANT", nm.start, nm.end, type=sum_name(ref.info), name=nm.text)
                    return None, 0
                ref, k = VariantRef(ref.info, nm.text), k + 1
                continue
            break
        return ref, k

    def tags(self, sum_) -> list:
        if isinstance(sum_, str):
            return [t for t, _ in BUILTIN_SUMS[sum_]]
        return [t for t, _ in sum_.variants] if sum_.kind == "enum" else []

    def fresh_sum(self, sum_, node):
        if isinstance(sum_, str):
            args = [self.new_meta(node.start, node.end, p) for p in BUILTIN_SUM_PARAMS[sum_]]
            return T.TCon(sum_, args)
        args = [self.new_meta(node.start, node.end, p.name) for p in sum_.params]
        return T.TNom(sum_, args)

    @staticmethod
    def payload(sum_, tag: str, st):
        """Тип полезной нагрузки варианта tag у типа суммы st (None — варианта без нагрузки)."""
        st = T.prune(st)
        if isinstance(sum_, str):
            idx = dict(BUILTIN_SUMS[sum_])[tag]
            return None if idx is None else st.args[idx]
        pt = dict(sum_.variants)[tag]
        return None if pt is None else T.subst(pt, sum_.mapping(st.args))

    def ref_type(self, ref, node):
        """Тип ссылки в позиции значения."""
        if isinstance(ref, LocalRef):
            return ref.type
        if isinstance(ref, ValRef):
            info = ref.info
            if isinstance(info, StoreInfo):
                self.err("TABLE_REF_NOT_STATIC", node.start, node.end)
                return T.TError()
            if info.kind in ENTRY:
                self.err("ENTRYPOINT_NOT_CALLABLE", node.start, node.end, name=info.name)
                return T.TError()
            params, ret, row = self.instantiate(info, node)
            return T.TFn(params, ret, row)
        if isinstance(ref, TableRef):
            self.err("TABLE_REF_NOT_STATIC", node.start, node.end)
            return T.TError()
        if isinstance(ref, VariantRef):
            st = self.fresh_sum(ref.sum, node)
            pt = self.payload(ref.sum, ref.tag, st)
            return st if pt is None else T.TFn([pt], st, T.PURE)
        if isinstance(ref, TypeRef):
            info = ref.info
            if isinstance(info, TypeInfo) and info.kind == "opaque":
                if self.opaque_ok(info, node):
                    st = self.fresh_sum(info, node)
                    return T.TFn([T.subst(info.rep, info.mapping(st.args))], st, T.PURE)
                return T.TError()
            self.err("UNKNOWN_NAME", node.start, node.end, name=sum_name(info).split(".")[-1])
            return T.TError()
        return T.TError()

    def opaque_ok(self, info: TypeInfo, node) -> bool:
        if info.module is not self.m:
            self.err("OPAQUE_CONSTRUCTOR_OUTSIDE_MODULE", node.start, node.end, type=info.name, module=info.module.name)
            return False
        return True

    def instantiate(self, info: FnInfo, node):
        m = {p.uid: self.new_meta(node.start, node.end, p.name) for p in info.tparams}
        rows = {uid: T.RowMeta(name) for name, uid in info.eparams}
        for rm in rows.values():
            self.pending.append(("row", rm))
        for p in info.tparams:
            for b in p.bounds:
                self.need_bound(m[p.uid], b, node)
        params = [T.subst(t, m, rows) for t in info.params]
        return params, T.subst(info.ret, m, rows), T.subst_row(info.row, rows)

    def path_span(self, names, k):
        return A.Node(names[0].start, names[k - 1].end)

    # ------------------------------------------------------------ выражения
    def infer(self, e, exp=None):
        t = self._infer(e, exp)
        if exp is not None and not self.unify_at(exp, t, e):
            t = T.TError()
        self.p.types[id(e)] = t
        return t

    def _infer(self, e, exp):
        if isinstance(e, A.Lit):
            return {"int": T.INT, "string": T.STRING, "bytes": T.BYTES, "bool": T.BOOL, "unit": T.UNIT}[e.kind]
        if isinstance(e, (A.Var, A.FieldAccess)):
            return self.path_expr(e)
        if isinstance(e, A.Paren):
            return self.infer(e.inner, exp)
        if isinstance(e, A.Call):
            return self.call(e, exp)
        if isinstance(e, A.Block):
            return self.block(e, exp)
        if isinstance(e, A.If):
            return self.if_(e, exp)
        if isinstance(e, A.Match):
            return self.match(e, exp)
        if isinstance(e, A.Lambda):
            return self.lambda_(e, exp)
        if isinstance(e, A.RecordLit):
            return self.record_lit(e, exp)
        if isinstance(e, A.SeqLit):
            elem = T.prune(exp).args[0] if isinstance(T.prune(exp), T.TCon) and T.prune(exp).name == "Seq" \
                else self.new_meta(e.start, e.end, "T")
            t = T.TCon("Seq", [elem])
            failed = exp is not None and not self.unify_at(exp, t, e)
            for x in e.items:
                self.infer(x, elem)
            return T.TError() if failed else t
        if isinstance(e, A.Unary):
            if e.op == "not":
                self.infer(e.operand, T.BOOL)
                return T.BOOL
            self.infer(e.operand, T.INT)
            return T.INT
        if isinstance(e, A.Binary):
            return self.binary(e, exp)
        if isinstance(e, A.Try):
            return self.try_(e)
        if isinstance(e, A.Return):
            if e.value is not None:
                self.infer(e.value, self.ctx.ret)
            else:
                self.unify_at(self.ctx.ret, T.UNIT, e)
            return T.NEVER
        if isinstance(e, A.Emit):
            return self.emit(e)
        raise TypeError(type(e).__name__)

    def path_expr(self, e):
        names = flatten(e)
        if names is None:                               # поле результата выражения: f(x).name
            t = self.infer(e.target)
            return self.field(t, e.name, e.target)
        ref, k = self.resolve(names)
        if ref is None:
            return T.TError()
        self.p.ann[id(e)] = ("path", ref, k)
        t = self.ref_type(ref, self.path_span(names, k))
        for i in range(k, len(names)):
            t = self.field(t, names[i], A.Node(names[0].start, names[i - 1].end))
        return t

    def field(self, t, nm: A.Name, target):
        t = self.known(t, target)
        if isinstance(t, T.TError):
            return t
        if isinstance(t, T.TNom) and t.info.kind in ("record", "event"):
            for name, ft in t.info.fields:
                if name == nm.text:
                    return T.subst(ft, t.info.mapping(t.args))
        self.err("UNKNOWN_FIELD", nm.start, nm.end, type=T.show(t), name=nm.text)
        return T.TError()

    # ------------------------------------------------------------ вызов
    def call(self, e: A.Call, exp):
        names = flatten(e.fn)
        ref = None
        if names is not None:
            ref, k = self.resolve(names)
            if ref is None:
                for a in e.args:
                    self.infer(a)
                return T.TError()
            if k < len(names):
                ref = None                              # поле значения: вызов значения fn-типа
        if isinstance(ref, ValRef) and isinstance(ref.info, FnInfo) and ref.info.kind == "fn":
            self.p.ann[id(e)] = ("fn", ref.info)
            return self.call_fn(e, ref.info, exp, self.path_span(names, k))
        if isinstance(ref, VariantRef) or (isinstance(ref, TypeRef) and isinstance(ref.info, TypeInfo)
                                           and ref.info.kind == "opaque"):
            self.p.ann[id(e)] = ("construct", ref)
            return self.construct(e, ref, exp)
        self.p.ann[id(e)] = ("value",)
        if isinstance(ref, TypeRef):
            self.err("FUNCTION_TYPE_REQUIRED", e.fn.start, e.fn.end)
            for a in e.args:
                self.infer(a)
            return T.TError()
        ft = self.known(self.infer(e.fn), e.fn)
        if isinstance(ft, T.TError):
            for a in e.args:
                self.infer(a)
            return ft
        if not isinstance(ft, T.TFn):
            self.err("FUNCTION_TYPE_REQUIRED", e.fn.start, e.fn.end)
            for a in e.args:
                self.infer(a)
            return T.TError()
        if len(ft.params) != len(e.args):
            self.err("ARGUMENT_COUNT", e.start, e.end, name=self.callee_name(e.fn), expected=len(ft.params),
                     actual=len(e.args))
            for a in e.args:
                self.infer(a)
            return T.TError()
        failed = exp is not None and not self.unify_at(exp, ft.ret, e)
        for a, pt in zip(e.args, ft.params):
            self.infer(a, pt)
        for atom in ft.row.resolved().atoms:
            self.ctx.effects.append((atom, e.start, e.end))
        return T.TError() if failed else ft.ret

    @staticmethod
    def callee_name(fn) -> str:
        names = flatten(fn)
        return ".".join(n.text for n in names) if names else "выражение"

    def call_fn(self, e: A.Call, info: FnInfo, exp, callee):
        params, ret, row = self.instantiate(info, callee)
        if len(params) != len(e.args):
            self.err("ARGUMENT_COUNT", e.start, e.end, name=self.callee_name(e.fn), expected=len(params),
                     actual=len(e.args))
            for a in e.args:
                self.infer(a)
            return T.TError()
        failed = exp is not None and not self.unify_at(exp, ret, e)
        tables = {}
        for k, (a, pt) in enumerate(zip(e.args, params)):
            p = T.prune(pt)
            if isinstance(p, T.TCon) and p.name == "Table":
                tbl = self.static_table(a)
                if tbl is False:
                    continue                                    # диагностика уже выдана
                if tbl is None:
                    self.err("TABLE_REF_NOT_STATIC", a.start, a.end)
                    continue
                self.unify_at(p, T.TCon("Table", [tbl.key, tbl.value]), a)
                tables[f"$param:{k}"] = tbl.qname
                self.p.ann[id(a)] = ("table", tbl)
                continue
            self.infer(a, pt)
        metas = {rm for t in params + [ret] for rm in self.row_metas(t)} | ({row.meta} if row.meta else set())
        for rm in sorted(metas, key=lambda r: r.name):
            self.solve_row(rm)
        for atom in row.resolved().atoms:
            if len(atom) == 2 and atom[1].startswith("$param:"):
                if atom[1] not in tables:
                    continue                                    # таблица не указана статически — ошибка уже выдана
                atom = (atom[0], tables[atom[1]])
            self.ctx.effects.append((atom, e.start, e.end))
        return T.TError() if failed else ret

    def row_metas(self, t) -> list:
        t = T.prune(t)
        out = []
        if isinstance(t, T.TFn):
            if t.row.meta is not None:
                out.append(t.row.meta)
            for x in t.params + [t.ret]:
                out += self.row_metas(x)
        elif isinstance(t, (T.TCon, T.TNom)):
            for x in t.args:
                out += self.row_metas(x)
        return out

    def solve_row(self, rm: T.RowMeta):
        """EFF-06: ρ(e) — объединение вкладов; выражения не-лямбды обязаны иметь ровно ρ(e)."""
        if rm.solution is not None:
            return
        cand = frozenset().union(*[c[0] for c in rm.contributions]) if rm.contributions else frozenset()
        rm.solution = cand
        for atoms, exact, s, e in rm.contributions:
            if exact and atoms != cand:
                self.err("TYPE_MISMATCH", s, e, expected=T.show_row(T.Row(cand)), actual=T.show_row(T.Row(atoms)))
        for want, known, s, e in rm.checks:
            if want != known | cand:
                self.err("TYPE_MISMATCH", s, e, expected=T.show_row(T.Row(want)), actual=T.show_row(T.Row(known | cand)))

    def static_table(self, a):
        """Аргумент Table: таблица, None (не путь к таблице — TABLE_REF_NOT_STATIC) или False (ошибка выдана)."""
        while isinstance(a, A.Paren):
            a = a.inner
        names = flatten(a)
        if names is None or names[0].text in self.locals:
            return None
        store = None
        if len(names) == 2:
            store = self.p.lookup(self.m, "values", names[0].text)
        elif len(names) == 3 and names[0].text in self.m.aliases:
            target = self.m.aliases[names[0].text]
            store = target.values.get(names[1].text)
            if isinstance(store, StoreInfo) and not store.pub:
                self.err("PRIVATE_ITEM", names[1].start, names[1].end, name=names[1].text, module=target.name)
                return False
        if isinstance(store, StoreInfo):
            tbl = store.tables.get(names[-1].text)
            if tbl is None:
                self.err("UNKNOWN_NAME", names[-1].start, names[-1].end, name=names[-1].text)
                return False
            return tbl
        return None

    def construct(self, e: A.Call, ref, exp):
        if isinstance(ref, TypeRef):
            info = ref.info
            if not self.opaque_ok(info, e.fn):
                for a in e.args:
                    self.infer(a)
                return T.TError()
            st = self.fresh_sum(info, e.fn)
            pt, tag = T.subst(info.rep, info.mapping(st.args)), info.name
        else:
            st = self.fresh_sum(ref.sum, e.fn)
            pt, tag = self.payload(ref.sum, ref.tag, st), ref.tag
        want = 0 if pt is None else 1
        if len(e.args) != want:
            self.err("ARGUMENT_COUNT", e.start, e.end, name=tag, expected=want, actual=len(e.args))
            for a in e.args:
                self.infer(a)
            return T.TError()
        failed = exp is not None and not self.unify_at(exp, st, e)
        self.infer(e.args[0], pt)
        return T.TError() if failed else st

    # ------------------------------------------------------------ блоки и ветвления
    def block(self, b: A.Block, exp):
        saved = dict(self.locals)
        last_never = False
        for st in b.stmts:
            mark = len(self.pending)
            if isinstance(st, A.Let):
                ann = self.p.resolve_type(st.type, self.m, self.scope) if st.type is not None else None
                t = self.infer(st.value, ann)
                self.finalize(mark)
                if st.name.text != "_":
                    self.locals[st.name.text] = ann if ann is not None else t
                last_never = isinstance(T.prune(t), T.TCon) and T.prune(t).name == "Never"
                continue
            t = self.infer(st.expr)
            self.finalize(mark)
            z = T.prune(t)
            last_never = isinstance(z, T.TCon) and z.name == "Never"
            if not st.semi:
                if not (isinstance(z, T.TError) or isinstance(z, T.TCon) and z.name in ("Unit", "Never")):
                    self.err("EXPECTED_UNIT_STATEMENT", st.expr.start, st.expr.end, actual=T.show(T.zonk(t)))
            elif isinstance(z, T.TCon) and z.name == "Result":
                self.err("RESULT_DISCARDED", st.expr.start, st.expr.end)
        if b.tail is not None:
            t = self.infer(b.tail, exp)
        else:
            t = T.NEVER if last_never else T.UNIT
            if exp is not None and not self.unify_at(exp, t, b):
                t = T.TError()
        self.locals = saved
        return t

    def join(self, t1, t2, node):
        if isinstance(T.prune(t1), T.TCon) and T.prune(t1).name == "Never":
            return t2
        if isinstance(T.prune(t2), T.TCon) and T.prune(t2).name == "Never":
            return t1
        return t1 if self.unify_at(t1, t2, node) else T.TError()

    def if_(self, e: A.If, exp):
        self.infer(e.cond, T.BOOL)
        if e.else_ is None:
            t = self.infer(e.then, T.UNIT)
            return t if isinstance(t, T.TError) else T.UNIT
        if exp is not None:
            self.infer(e.then, exp)
            self.infer(e.else_, exp)
            return exp
        t1 = self.infer(e.then)
        t2 = self.infer(e.else_)
        return self.join(t1, t2, e.else_)

    def match(self, e: A.Match, exp):
        st = self.known(self.infer(e.scrutinee), e.scrutinee)
        sum_ = None
        if isinstance(st, T.TCon) and st.name in BUILTIN_SUMS:
            sum_ = st.name
        elif isinstance(st, T.TNom) and st.info.kind in ("enum", "opaque"):
            sum_ = st.info
        elif not isinstance(st, T.TError):
            self.err("NOT_A_SUM_TYPE", e.scrutinee.start, e.scrutinee.end, type=T.show(T.zonk(st)))
        seen, result, unresolved = set(), exp, False
        for arm in e.arms:
            payload, ok = T.TError(), False
            ref, k = self.resolve(arm.pattern.path) if sum_ is not None else (None, 0)
            pat = arm.pattern
            if ref is None and sum_ is not None:
                unresolved = True
            if ref is not None:
                if k < len(pat.path):
                    unresolved = True
                    nm = pat.path[k]
                    self.err("UNKNOWN_VARIANT", nm.start, nm.end, type=T.show(st), name=nm.text)
                elif isinstance(sum_, TypeInfo) and sum_.kind == "opaque":
                    if isinstance(ref, TypeRef) and ref.info is sum_:
                        self.p.ann[id(arm)] = sum_.name
                        if sum_.name in seen:
                            self.err("DUPLICATE_MATCH_ARM", pat.start, pat.end, tag=sum_.name)
                        elif self.opaque_ok(sum_, pat):
                            payload, ok = T.subst(sum_.rep, sum_.mapping(st.args)), True
                        seen.add(sum_.name)
                    else:
                        unresolved = True
                        self.err("UNKNOWN_MATCH_TAG", pat.start, pat.end, tag=self.pat_text(pat), type=T.show(st))
                elif isinstance(ref, VariantRef) and (ref.sum == sum_ if isinstance(sum_, str) else ref.sum is sum_):
                    tag = ref.tag
                    self.p.ann[id(arm)] = tag
                    if tag in seen:
                        self.err("DUPLICATE_MATCH_ARM", pat.start, pat.end, tag=tag)
                    else:
                        pt = self.payload(sum_, tag, st)
                        if pt is None and pat.binder is not None:
                            self.err("ARGUMENT_COUNT", pat.start, pat.end, name=tag, expected=0, actual=1)
                        else:
                            payload, ok = (pt if pt is not None else T.UNIT), True
                    seen.add(tag)
                else:
                    unresolved = True
                    self.err("UNKNOWN_MATCH_TAG", pat.start, pat.end, tag=self.pat_text(pat), type=T.show(st))
            saved = dict(self.locals)
            if pat.binder is not None and pat.binder.text != "_":
                self.locals[pat.binder.text] = payload if ok else T.TError()
            if result is not None:
                bt = self.infer(arm.body, result)
            else:
                bt = self.infer(arm.body)
                result = None if isinstance(T.prune(bt), T.TCon) and T.prune(bt).name == "Never" else bt
            self.locals = saved
        if sum_ is not None and not unresolved:                 # без каскада после ошибки шаблона (CHK-03)
            tags = [sum_.name] if isinstance(sum_, TypeInfo) and sum_.kind == "opaque" else self.tags(sum_)
            missing = [t for t in tags if t not in seen]
            if missing:
                self.err("NON_EXHAUSTIVE_MATCH", e.start, e.start + 5, missing=missing)
        self.p.ann[id(e)] = ("match", sum_)
        if result is None:
            return T.NEVER if e.arms else T.UNIT
        return result

    @staticmethod
    def pat_text(p: A.Pattern) -> str:
        return ".".join(n.text for n in p.path)

    # ------------------------------------------------------------ лямбда
    def lambda_(self, e: A.Lambda, exp):
        ef = T.prune(exp) if exp is not None else None
        if ef is not None and not isinstance(ef, (T.TFn, T.TMeta, T.TError)):
            self.err("TYPE_MISMATCH", e.start, e.end, expected=T.show(T.zonk(ef)), actual="fn")
            return T.TError()
        if isinstance(ef, T.TFn) and len(ef.params) != len(e.params):
            self.err("TYPE_MISMATCH", e.start, e.end, expected=T.show(T.zonk(ef)), actual=f"fn с {len(e.params)} параметрами")
            return T.TError()
        fn_exp = ef if isinstance(ef, T.TFn) else None
        saved_locals, saved_ctx = dict(self.locals), self.ctx
        params, seen = [], set()
        for i, p in enumerate(e.params):
            if p.name.text in seen:
                self.err("DUPLICATE_PARAMETER", p.name.start, p.name.end, name=p.name.text)
            seen.add(p.name.text)
            if p.type is not None:
                t = self.p.resolve_type(p.type, self.m, self.scope)
                if fn_exp is not None:
                    self.unify_at(fn_exp.params[i], t, p)
            elif fn_exp is not None:
                t = fn_exp.params[i]
            else:
                t = T.TMeta(lambda_param=(p.name.text, p.name.start, p.name.end))
                self.pending.append(("lambda", t))
            if isinstance(T.prune(t), T.TMeta) and T.prune(t).lambda_param is None and fn_exp is not None:
                T.prune(t).lambda_param = (p.name.text, p.name.start, p.name.end)
            params.append(t)
            self.locals[p.name.text] = t
        ret = fn_exp.ret if fn_exp is not None else T.TMeta()
        self.ctx = Ctx(ret)
        self.infer(e.body, ret)
        effects = self.ctx.effects
        self.ctx, self.locals = saved_ctx, saved_locals
        actual = frozenset(a for a, _, _ in effects)
        if fn_exp is not None:
            row = fn_exp.row
            if row.meta is not None and row.meta.solution is None:
                row.meta.contributions.append((actual - row.atoms, False, e.start, e.end))
            else:
                self.require_effects(effects, row.resolved().atoms)
            return fn_exp
        t = T.TFn(params, ret, T.Row(actual))
        if ef is not None:
            self.unify_at(ef, t, e)
        return t

    # ------------------------------------------------------------ записи, карты, события
    def record_type_path(self, names):
        """Голова литерала записи — путь в пространстве типов."""
        a, b = names[0].start, names[-1].end
        if len(names) == 1 and names[0].text == "Map" and self.p.lookup(self.m, "types", "Map") is None:
            return "Map"
        info = self.p.qualified(self.m, "types", names)
        if info is False:
            return None
        if info is None:
            self.err("UNKNOWN_TYPE", a, b, name=".".join(n.text for n in names))
            return None
        return info

    def record_lit(self, e: A.RecordLit, exp):
        names = flatten(e.type)
        info = self.record_type_path(names)
        if info is None:
            for en in e.entries:
                self.infer(en.value)
            return T.TError()
        self.p.ann[id(e)] = ("record", info)
        if info == "Map":
            return self.map_lit(e, exp)
        if info.kind not in ("record", "event"):
            self.err("TYPE_MISMATCH", e.type.start, e.type.end, expected="запись", actual=info.qname)
            for en in e.entries:
                self.infer(en.value)
            return T.TError()
        t = self.fresh_sum(info, e.type)
        if exp is not None and not self.unify_at(exp, t, e):
            return T.TError()
        self.record_entries(info, t, e.entries, e.brace, e.end)
        return t

    def record_entries(self, info: TypeInfo, t, entries, brace: int, end: int):
        fields = {n: T.subst(ft, info.mapping(T.prune(t).args)) for n, ft in info.fields}
        seen, base = set(), False
        for en in entries:
            if en.kind == "pair":
                self.err("TYPE_MISMATCH", en.start, en.end, expected="поле записи", actual="пара карты")
                continue
            if en.kind == "base":
                self.infer(en.value, t)
                base = True
                continue
            nm = en.name
            if nm.text not in fields:
                self.err("UNKNOWN_FIELD", nm.start, nm.end, type=info.qname, name=nm.text)
                self.infer(en.value)
            elif nm.text in seen:
                self.err("DUPLICATE_FIELD", nm.start, nm.end, name=nm.text)
                self.infer(en.value)
            else:
                self.infer(en.value, fields[nm.text])
            seen.add(nm.text)
        if not base:
            missing = [n for n, _ in info.fields if n not in seen]
            if missing:
                self.err("MISSING_FIELD", brace, end, name=missing[0], missing=missing)

    def map_lit(self, e: A.RecordLit, exp):
        k = self.new_meta(e.start, e.end, "K")
        v = self.new_meta(e.start, e.end, "V")
        t = T.TCon("Map", [k, v])
        if exp is not None and not self.unify_at(exp, t, e):
            return T.TError()
        self.need_bound(k, "Key", e)
        consts = {}
        for en in e.entries:
            if en.kind != "pair":
                self.err("TYPE_MISMATCH", en.start, en.end, expected="пара карты", actual="поле записи")
                continue
            self.infer(en.key, k)
            self.infer(en.value, v)
        keys = [en.key for en in e.entries if en.kind == "pair"]
        if keys and all(self.const_key(x) is not None for x in keys):
            for x in keys:
                c = self.const_key(x)
                if c in consts:
                    self.err("DUPLICATE_MAP_KEY", x.start, x.end, key=self.src_text(x.start, x.end))
                consts.setdefault(c, x)
        return t

    def src_text(self, a: int, b: int) -> str:
        return self.p.sources[self.m.file][a:b].decode("utf-8")

    @staticmethod
    def const_key(x):
        while isinstance(x, A.Paren):
            x = x.inner
        if isinstance(x, A.Lit):
            return (x.kind, x.value)
        if isinstance(x, A.Unary) and x.op == "-" and isinstance(x.operand, A.Lit) and x.operand.kind == "int" \
                and x.operand.value is not None:
            return ("int", -x.operand.value)
        return None

    def emit(self, e: A.Emit):
        a, b = span_of(e.event)
        info = self.p.qualified(self.m, "types", e.event)
        if info is None:
            self.err("UNKNOWN_TYPE", a, b, name=".".join(n.text for n in e.event))
        elif info is not False and info.kind != "event":
            self.err("UNKNOWN_EFFECT_TARGET", a, b, path=".".join(n.text for n in e.event))
        if not isinstance(info, TypeInfo) or info.kind != "event":
            for en in e.entries:
                self.infer(en.value)
            return T.UNIT
        self.record_entries(info, T.TNom(info, []), e.entries, e.brace, e.end)
        self.p.ann[id(e)] = ("emit", info)
        self.ctx.effects.append((("emits", info.qname), e.start, e.end))
        return T.UNIT

    # ------------------------------------------------------------ операторы
    def binary(self, e: A.Binary, exp):
        op = e.op
        if op in ("and", "or"):
            self.infer(e.left, T.BOOL)
            self.infer(e.right, T.BOOL)
            return T.BOOL
        if op in ("+", "-", "*", "/", "%"):
            self.infer(e.left, T.INT)
            self.infer(e.right, T.INT)
            return T.INT
        if op == "++":
            lt = self.known(self.infer(e.left), e.left)
            if isinstance(lt, T.TMeta) and exp is not None:
                self.unify_at(exp, lt, e.left)
                lt = T.prune(lt)
            if isinstance(lt, T.TError):
                self.infer(e.right)
                return lt
            if isinstance(lt, T.TCon) and lt.name in ("String", "Bytes", "Seq"):
                self.infer(e.right, lt)
                return lt
            self.err("TYPE_MISMATCH", e.left.start, e.left.end, expected="String | Bytes | Seq<T>",
                     actual=T.show(T.zonk(lt)))
            self.infer(e.right)
            return T.TError()
        lt = self.known(self.infer(e.left), e.left)
        self.infer(e.right, lt)
        self.need_bound(lt, "Eq" if op in ("==", "!=") else "Key", e)
        return T.BOOL

    def try_(self, e: A.Try):
        t = self.known(self.infer(e.operand), e.operand)
        ret = T.prune(self.ctx.ret)
        if isinstance(t, T.TError):
            return t
        if isinstance(t, T.TCon) and t.name in ("Result", "Option"):
            if isinstance(ret, T.TMeta):
                ret.ref = T.TCon(t.name, [T.TMeta()] + ([t.args[1]] if t.name == "Result" else []))
                ret = T.prune(ret)
            ok = isinstance(ret, T.TCon) and ret.name == t.name
            if ok and t.name == "Result":
                try:
                    T.unify(ret.args[1], t.args[1])
                except T.UnifyError:
                    ok = False
            if not ok and not isinstance(ret, T.TError):
                need = f"Result<_, {T.show(T.zonk(t.args[1]))}>" if t.name == "Result" else "Option<_>"
                self.err("QUESTION_MARK_CONTEXT", e.start, e.end, expected=need)
            return t.args[0]
        self.err("TYPE_MISMATCH", e.operand.start, e.operand.end, expected="Result<_, _> | Option<_>",
                 actual=T.show(T.zonk(t)))
        return T.TError()


def is_primitive(info: FnInfo) -> bool:
    """Функция std с телом `{}` реализуется машиной как примитив `std.<модуль>.<имя>@1`."""
    b = info.decl.body
    return not b.stmts and b.tail is None


def check_project(files: list[tuple[str, bytes]]) -> list:
    """Разрешение имён, типы и эффекты проекта; files уже разобраны без ошибок. Возвращает диагностики."""
    return check_project_full(files)[1]


def check_project_full(files: list[tuple[str, bytes]]):
    """То же, но вместе с проектом: сведения об объявлениях нужны инструментам (пробник, позже граф)."""
    p = Project(files)
    mark = len(p.diags)
    for m in p.modules.values():
        if m.is_std:
            Checker(p, m).check_module()               # тела std на bagaev: им тоже нужны разрешения
    assert len(p.diags) == mark, p.diags[mark:]
    for m in p.user:
        Checker(p, m).check_module()
    p.flush_bounds()                                    # аннотации let и лямбд в телах
    return p, p.diags
