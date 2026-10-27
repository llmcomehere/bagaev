"""Проект: модули, три пространства имён, импорты, устойчивые ID, объявления и сигнатуры.

Порядок и диапазоны диагностик — spec/language/checking.md §1–§4. Тела проверяет sema.check.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from bagaev_ref.diag import make
from bagaev_ref.sema import types as T
from bagaev_ref.sema.std import STD_SOURCES
from bagaev_ref.syntax import ast as A
from bagaev_ref.syntax.parser import parse
from bagaev_ref.syntax.printer import id_sites

ID_RE = re.compile(r"^[0-9a-hjkmnp-tv-z]{6}$")
ENTRY_KINDS = {"command", "query", "handler", "migration", "test"}
HOST_OWNED = {"handler", "migration", "test"}
CONTEXT_ATOMS = {"query": {"reads"}, "command": {"reads", "writes", "emits"},
                 "handler": {"reads", "writes", "emits", "consumes"}}
UNSUPPORTED_TYPES = {"Float": "V1-P01", "BigInt": "V1-P02"}


# ------------------------------------------------------------ сведения об объявлениях
@dataclass(eq=False)
class TypeInfo:
    kind: str                      # record enum opaque event
    name: str
    module: "ModuleInfo"
    decl: object
    pub: bool
    params: list = field(default_factory=list)        # TRigid
    fields: list = field(default_factory=list)        # (имя, Type)
    variants: list = field(default_factory=list)      # (имя, Type | None)
    rep: object = None

    @property
    def qname(self) -> str:
        return f"{self.module.name}.{self.name}"

    def mapping(self, args) -> dict:
        return {p.uid: a for p, a in zip(self.params, args)}

    def member_types(self, args) -> list:
        m = self.mapping(args)
        out = [T.subst(t, m) for _, t in self.fields]
        out += [T.subst(t, m) for _, t in self.variants if t is not None]
        if self.rep is not None:
            out.append(T.subst(self.rep, m))
        return out


@dataclass(eq=False)
class FnInfo:
    kind: str                      # fn command query handler migration test
    name: str
    module: "ModuleInfo"
    decl: object
    pub: bool
    tparams: list = field(default_factory=list)       # TRigid
    eparams: list = field(default_factory=list)       # (имя, uid)
    params: list = field(default_factory=list)        # Type
    ret: object = None
    row: T.Row = T.PURE
    table: object = None           # TableInfo миграции
    actual: frozenset = frozenset()  # фактические атомы тела (после проверки)

    @property
    def qname(self) -> str:
        return f"{self.module.name}.{self.name}"


@dataclass(eq=False)
class TableInfo:
    name: str
    store: "StoreInfo"
    decl: object
    key: object = None
    value: object = None

    @property
    def qname(self) -> str:
        return f"{self.store.module.name}.{self.store.name}.{self.name}"


@dataclass(eq=False)
class StoreInfo:
    name: str
    module: "ModuleInfo"
    decl: object
    pub: bool
    kind: str = "store"
    tables: dict = field(default_factory=dict)


@dataclass(eq=False)
class MeaningInfo:
    kind: str                      # entity contract
    name: str
    module: "ModuleInfo"
    decl: object
    pub: bool
    rules: set = field(default_factory=set)


@dataclass(eq=False)
class ModuleInfo:
    name: str
    file: str
    tree: A.File
    is_std: bool
    types: dict = field(default_factory=dict)
    values: dict = field(default_factory=dict)
    meanings: dict = field(default_factory=dict)
    imported: dict = field(default_factory=lambda: {"types": {}, "values": {}, "meanings": {}})
    aliases: dict = field(default_factory=dict)
    imports: list = field(default_factory=list)      # (UseDecl, ModuleInfo)


@dataclass
class Scope:
    """Параметры типов и эффектов, видимые в сигнатуре и теле."""
    rigids: dict = field(default_factory=dict)        # имя → TRigid
    effects: dict = field(default_factory=dict)       # имя → uid
    table_params: dict | None = None                 # имя → индекс (только std.store)


def span_of(path) -> tuple[int, int]:
    return path[0].start, path[-1].end


class Project:
    def __init__(self, files: list[tuple[str, bytes]]):
        """files — (путь относительно корня с «/», байты); все файлы уже разобраны без ошибок."""
        self.diags: list = []
        self.sources = dict(files)
        self.deferred_bounds: list = []                    # (тип, ограничение, модуль, start, end): TYPES-0.1 §2
        self.types: dict = {}                              # id(узел выражения) → тип (для понижения в BIR-1)
        self.ann: dict = {}                                # id(узел) → разрешение: путь, вызов, тег ветви, запись
        self.modules: dict[str, ModuleInfo] = {}
        self.user: list[ModuleInfo] = []
        for name, src in STD_SOURCES.items():
            tree, _, ds = parse(src.encode("utf-8"), f"<{name}>")
            assert not ds, (name, ds)
            self.modules[name] = ModuleInfo(name, f"<{name}>", tree, True)
        for rel, data in sorted(files):
            tree, _, ds = parse(data, rel)
            assert not ds and tree is not None
            expected = rel[:-4].replace("/", ".")
            m = ModuleInfo(expected, rel, tree, False)
            if expected == "std" or expected.startswith("std."):
                a, b = span_of(tree.module.path)            # пространство std принадлежит набору инструментов (CHK-01)
                self.d("DUPLICATE_DECLARATION", m, a, b, name=expected)
                continue
            if [n.text for n in tree.module.path] != expected.split("."):
                a, b = span_of(tree.module.path)
                self.d("MODULE_PATH_MISMATCH", m, a, b, module=".".join(n.text for n in tree.module.path), path=rel)
            self.modules[expected] = m
            self.user.append(m)
        mods = list(self.modules.values())
        for m in mods:
            self.declare(m)
        for m in mods:
            self.resolve_imports(m)
        for m in self.user:
            self.check_duplicates(m)
            self.check_attrs(m)
        self.check_cycles()
        self.check_ids()
        for m in mods:
            self.type_bodies(m)
        for m in self.user:
            self.check_recursive_types(m)
        for m in mods:
            self.stores_and_events(m)
        for m in mods:
            self.signatures(m)
        for m in self.user:
            self.check_links(m)
        self.flush_bounds()

    def flush_bounds(self):
        """Ограничения в записи типов проверяются, когда известны поля всех типов (предикаты — gfp)."""
        items, self.deferred_bounds = self.deferred_bounds, []
        for t, bound, m, a, b in items:
            if T.satisfies(t, bound) is False:
                self.d("BOUND_NOT_SATISFIED", m, a, b, type=T.show(t), bound=bound)

    # ------------------------------------------------------------ диагностики
    def d(self, code: str, m: ModuleInfo, start: int, end: int, phase: str | None = None, **data):
        if m.is_std:
            raise AssertionError(f"std {m.name}: {code} {data}")
        self.diags.append(make(code, m.file, start, end, phase, **data))

    # ------------------------------------------------------------ объявления
    def declare(self, m: ModuleInfo):
        for it in m.tree.items:
            d = it.decl
            if isinstance(d, A.TypeDecl):
                m.types.setdefault(d.name.text, TypeInfo(d.kind, d.name.text, m, d, it.pub or m.is_std))
            elif isinstance(d, A.EventDecl):
                m.types.setdefault(d.name.text, TypeInfo("event", d.name.text, m, d, it.pub or m.is_std))
            elif isinstance(d, A.StoreDecl):
                m.values.setdefault(d.name.text, StoreInfo(d.name.text, m, d, it.pub))
            elif isinstance(d, (A.EntityDecl, A.ContractDecl)):
                kind = "entity" if isinstance(d, A.EntityDecl) else "contract"
                rules = {r.name.text for r in d.rules} if kind == "contract" else set()
                m.meanings.setdefault(d.name.text, MeaningInfo(kind, d.name.text, m, d, it.pub, rules))
            else:
                kind = d.kind if isinstance(d, A.EntryDecl) else {
                    A.FnDecl: "fn", A.HandlerDecl: "handler", A.MigrationDecl: "migration", A.TestDecl: "test"}[type(d)]
                m.values.setdefault(d.name.text, FnInfo(kind, d.name.text, m, d, it.pub or m.is_std))

    def resolve_imports(self, m: ModuleInfo):
        for u in m.tree.uses:
            if u.group is None:
                target = self.modules.get(".".join(n.text for n in u.path))
                if target is None:
                    self.d("UNKNOWN_MODULE", m, *span_of(u.path), name=".".join(n.text for n in u.path))
                    continue
                m.imports.append((u, target))
                alias = (u.alias or u.path[-1]).text
                if alias in m.aliases:
                    self.d("DUPLICATE_DECLARATION", m, *span_of([u.alias or u.path[-1]]), name=alias)
                    continue
                m.aliases[alias] = target
                continue
            target = self.modules.get(".".join(n.text for n in u.path))
            if target is None:
                self.d("UNKNOWN_MODULE", m, *span_of(u.path), name=".".join(n.text for n in u.path))
                continue
            m.imports.append((u, target))
            for g in u.group:
                name = g.name.text
                found = [(ns, getattr(target, ns)[name]) for ns in ("types", "values", "meanings")
                         if name in getattr(target, ns)]
                if not found:
                    self.d("UNKNOWN_NAME", m, g.name.start, g.name.end, name=name)
                    continue
                public = [(ns, info) for ns, info in found if info.pub]
                if not public:
                    self.d("PRIVATE_ITEM", m, g.name.start, g.name.end, name=name, module=target.name)
                    continue
                for ns, info in public:                      # одноимённое непубличное объявление не импортируется
                    m.imported[ns].setdefault((g.alias or g.name).text, info)

    def check_duplicates(self, m: ModuleInfo):
        """SURF-03: имя повторяется в одном пространстве модуля, включая имена из use."""
        entries = []
        for u in m.tree.uses:
            if not u.group:
                continue
            target = self.modules.get(".".join(n.text for n in u.path))
            for g in u.group:
                nm = g.alias or g.name
                for ns in ("types", "values", "meanings"):
                    if target is not None and g.name.text in getattr(target, ns) and getattr(target, ns)[g.name.text].pub:
                        entries.append((nm.start, ns, nm))
        for it in m.tree.items:
            d = it.decl
            ns = ("types" if isinstance(d, (A.TypeDecl, A.EventDecl)) else
                  "meanings" if isinstance(d, (A.EntityDecl, A.ContractDecl)) else "values")
            entries.append((d.name.start, ns, d.name))
        seen = set()
        for _, ns, nm in sorted(entries, key=lambda e: e[0]):
            if (ns, nm.text) in seen:
                self.d("DUPLICATE_DECLARATION", m, nm.start, nm.end, name=nm.text)
            seen.add((ns, nm.text))

    def check_attrs(self, m: ModuleInfo):
        nodes = [m.tree.module] + [x for x, _ in id_sites(m.tree)[1:]]
        for node in nodes:
            for at in node.attrs:
                if at.name.text != "id":
                    self.d("UNKNOWN_ATTRIBUTE", m, at.start, at.end, name=at.name.text)
        for it in m.tree.items:
            kind = self.decl_kind(it.decl)
            if it.pub and kind in HOST_OWNED:
                self.d("PUB_NOT_ALLOWED", m, it.pub_at, it.pub_at + 3, kind=kind)

    @staticmethod
    def decl_kind(d) -> str:
        if isinstance(d, A.EntryDecl):
            return d.kind
        return {A.FnDecl: "fn", A.HandlerDecl: "handler", A.MigrationDecl: "migration", A.TestDecl: "test",
                A.TypeDecl: "type", A.EventDecl: "event", A.StoreDecl: "store", A.EntityDecl: "entity",
                A.ContractDecl: "contract"}[type(d)]

    def check_cycles(self):
        """SURF-02: цикл импортов; диагностика — на первом use цикла в первом по пути модуле цикла."""
        index, low, stack, on, sccs, counter = {}, {}, [], set(), [], [0]

        def visit(v):
            index[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on.add(v)
            for _, w in v.imports:
                if w.is_std:
                    continue
                if w not in index:
                    visit(w)
                    low[v] = min(low[v], low[w])
                elif w in on:
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp.append(w)
                    if w is v:
                        break
                sccs.append(comp)
        for m in self.user:
            if m not in index:
                visit(m)
        for comp in sccs:
            members = set(comp)
            if len(comp) == 1 and not any(t is comp[0] for _, t in comp[0].imports):
                continue
            first = min(comp, key=lambda x: x.file)
            u = next(u for u, t in first.imports if t in members)
            path = self.cycle_path(first, u, members)
            self.d("MODULE_IMPORT_CYCLE", first, *span_of(u.path), cycle=" -> ".join(x.name for x in path))

    @staticmethod
    def cycle_path(first, u, members) -> list:
        """Кратчайший путь импортов от цели use обратно к first: простой цикл для data.cycle."""
        start = next(t for uu, t in first.imports if uu is u)
        prev, queue = {start: None}, [start]
        while queue:
            cur = queue.pop(0)
            if cur is first:
                break
            for _, t in cur.imports:
                if t in members and t not in prev:
                    prev[t] = cur
                    queue.append(t)
        chain, cur = [], first
        while cur is not None:
            chain.append(cur)
            cur = prev.get(cur)
        return [first] + chain[::-1][:-1] + [first] if start is not first else [first, first]

    def check_ids(self):
        """SURF-07: @id у заголовка модуля, деклараций, полей, вариантов, таблиц, правил; уникальность в проекте."""
        seen = {}
        for m in self.user:
            for node, _ in id_sites(m.tree):
                ids = [a for a in node.attrs if a.name.text == "id"]
                if not ids:
                    nm = self.site_name(node)
                    self.d("MISSING_ENTITY_ID", m, nm[0], nm[1])
                    continue
                for k, at in enumerate(ids):
                    ok = (k == 0 and len(at.args) == 1 and at.args[0][0] == "STRING" and isinstance(at.args[0][1], str)
                          and ID_RE.match(at.args[0][1]))
                    if not ok:
                        text = ", ".join(str(a[1]) for a in at.args)
                        self.d("MALFORMED_ENTITY_ID", m, at.start, at.end, text=text)
                        continue
                    v = at.args[0][1]
                    if v in seen:
                        self.d("DUPLICATE_ENTITY_ID", m, at.start, at.end, id=v, other=seen[v])
                    else:
                        seen[v] = f"{m.file}:{at.start}"

    @staticmethod
    def site_name(node) -> tuple[int, int]:
        if isinstance(node, A.ModuleHeader):
            return span_of(node.path) if node.path else (node.start, node.end)
        if isinstance(node, A.Item):
            return node.decl.name.start, node.decl.name.end
        return node.name.start, node.name.end

    # ------------------------------------------------------------ поиск имён
    @staticmethod
    def lookup(m: ModuleInfo, ns: str, name: str):
        return getattr(m, ns).get(name) or m.imported[ns].get(name)

    def qualified(self, m: ModuleInfo, ns: str, path, report: bool = True):
        """Путь из одного имени или «псевдоним.имя»; None — не найдено (диагностику выдаёт вызывающий)."""
        if len(path) == 1:
            return self.lookup(m, ns, path[0].text)
        if len(path) == 2 and path[0].text in m.aliases:
            target = m.aliases[path[0].text]
            info = getattr(target, ns).get(path[1].text)
            if info is not None and not info.pub:
                if report:
                    self.d("PRIVATE_ITEM", m, path[1].start, path[1].end, name=path[1].text, module=target.name)
                return False
            return info
        return None

    def lookup_table(self, m: ModuleInfo, path):
        """Таблица по пути; None — не найдена; False — диагностика (PRIVATE_ITEM) уже выдана."""
        if len(path) < 2:
            return None
        store = self.qualified(m, "values", path[:-1])
        if store is False:
            return False
        if not isinstance(store, StoreInfo):
            return None
        return store.tables.get(path[-1].text)

    # ------------------------------------------------------------ типы
    def resolve_type(self, t, m: ModuleInfo, scope: Scope):
        if isinstance(t, A.UnitType):
            return T.UNIT
        if isinstance(t, A.FnType):
            ps = [self.resolve_type(p, m, scope) for p in t.params]
            ret = self.resolve_type(t.ret, m, scope)
            row = self.resolve_row(t.row, m, scope) if t.row is not None else T.PURE
            return T.TFn(ps, ret, row)
        names = [n.text for n in t.path]
        args = [self.resolve_type(a, m, scope) for a in t.args]
        a, b = span_of(t.path)
        if len(names) == 1:
            n = names[0]
            if n in scope.rigids:
                if args:
                    self.d("UNSUPPORTED_FEATURE", m, t.start, t.end, phase="resolve", feature_id="V1-X07")
                    return T.TError()
                return scope.rigids[n]
            info = self.lookup(m, "types", n)
            if info is not None:
                return self.apply_args(info, args, t, m)
            if n in T.BUILTIN_ARITY:
                if n == "Table" and scope.table_params is None:
                    self.d("TABLE_PARAM_ONLY_IN_STD", m, t.start, t.end)
                    return T.TError()
                if len(args) != T.BUILTIN_ARITY[n]:
                    self.d("TYPE_ARITY", m, t.start, t.end, type=n, expected=T.BUILTIN_ARITY[n], actual=len(args))
                    return T.TError()
                if n == "Map" and not m.is_std:
                    self.deferred_bounds.append((args[0], "Key", m, t.start, t.end))
                return T.UNIT if n == "Unit" else T.TCon(n, args) if args else T.TCon(n)
            if n in UNSUPPORTED_TYPES:
                self.d("UNSUPPORTED_FEATURE", m, a, b, phase="resolve", feature_id=UNSUPPORTED_TYPES[n])
                return T.TError()
            self.d("UNKNOWN_TYPE", m, a, b, name=n)
            return T.TError()
        info = self.qualified(m, "types", t.path)
        if info is False:
            return T.TError()
        if info is None:
            self.d("UNKNOWN_TYPE", m, a, b, name=".".join(names))
            return T.TError()
        return self.apply_args(info, args, t, m)

    def apply_args(self, info: TypeInfo, args, t, m):
        if len(args) != len(info.decl.params if isinstance(info.decl, A.TypeDecl) else []):
            expected = len(info.decl.params) if isinstance(info.decl, A.TypeDecl) else 0
            self.d("TYPE_ARITY", m, t.start, t.end, type=info.name, expected=expected, actual=len(args))
            return T.TError()
        if not m.is_std and isinstance(info.decl, A.TypeDecl):
            for g, arg in zip(info.decl.params, args):
                for bnd in g.bounds:
                    if bnd.text in T.BOUNDS:
                        self.deferred_bounds.append((arg, bnd.text, m, t.start, t.end))
        return T.TNom(info, args)

    def resolve_row(self, row, m: ModuleInfo, scope: Scope) -> T.Row:
        atoms = set()
        if row.var is not None:
            if row.var.text in scope.effects:
                atoms.add(("var", scope.effects[row.var.text], row.var.text))
            else:
                self.d("UNKNOWN_EFFECT_VARIABLE", m, row.var.start, row.var.end, name=row.var.text)
        for it in row.items:
            text = ".".join(n.text for n in it.path)
            a, b = span_of(it.path)
            if it.kind in ("reads", "writes"):
                if scope.table_params is not None and len(it.path) == 1 and text in scope.table_params:
                    atoms.add((it.kind, f"$param:{scope.table_params[text]}"))
                    continue
                tbl = self.lookup_table(m, it.path)
                if tbl is None:
                    self.d("UNKNOWN_EFFECT_TARGET", m, a, b, path=text)
                elif tbl is not False:
                    atoms.add((it.kind, tbl.qname))
            elif it.kind == "emits":
                info = self.qualified(m, "types", it.path, report=True)
                if isinstance(info, TypeInfo) and info.kind == "event":
                    atoms.add(("emits", info.qname))
                elif info is not False:
                    self.d("UNKNOWN_EFFECT_TARGET", m, a, b, path=text)
            else:
                self.d("UNKNOWN_HOST_ADAPTER", m, a, b, name=text)
        return T.Row(frozenset(atoms))

    def generics(self, gens, m: ModuleInfo) -> Scope:
        scope = Scope()
        seen = set()
        for g in gens:
            if g.name.text in seen:
                self.d("DUPLICATE_PARAMETER", m, g.name.start, g.name.end, name=g.name.text)
                continue
            seen.add(g.name.text)
            if g.is_effect:
                scope.effects[g.name.text] = next(T._ids)
                continue
            bounds = set()
            for bnd in g.bounds:
                if bnd.text in T.BOUNDS:
                    bounds.add(bnd.text)
                else:
                    self.d("UNKNOWN_TYPE", m, bnd.start, bnd.end, name=bnd.text)
            scope.rigids[g.name.text] = T.TRigid(g.name.text, frozenset(bounds))
        return scope

    def type_bodies(self, m: ModuleInfo):
        for info in m.types.values():
            d = info.decl
            if isinstance(d, A.TypeDecl):
                scope = self.generics(d.params, m)
                info.params = list(scope.rigids.values())
            else:
                scope = Scope()
            members = d.fields if isinstance(d, (A.EventDecl,)) or info.kind == "record" else d.variants
            seen = set()
            for mem in members:
                if mem.name.text in seen:
                    self.d("DUPLICATE_MEMBER", m, mem.name.start, mem.name.end, name=mem.name.text, decl=info.name)
                    continue
                seen.add(mem.name.text)
                if isinstance(mem, A.FieldDecl):
                    info.fields.append((mem.name.text, self.resolve_type(mem.type, m, scope)))
                else:
                    pt = self.resolve_type(mem.payload, m, scope) if mem.payload is not None else None
                    info.variants.append((mem.name.text, pt))
            if info.kind == "opaque":
                info.rep = self.resolve_type(d.rep, m, scope)

    def check_recursive_types(self, m: ModuleInfo):
        """SURF-10 / D69: в группе взаимно рекурсивных типов обращения передают те же параметры по порядку."""
        decls = [i for i in m.types.values()]
        refs = {}
        for info in decls:
            out = []
            d = info.decl
            texprs = [f.type for f in getattr(d, "fields", [])] + [v.payload for v in getattr(d, "variants", [])
                                                                  if v.payload is not None]
            if isinstance(d, A.TypeDecl) and d.rep is not None:
                texprs.append(d.rep)
            for te in texprs:
                self.type_paths(te, out)
            refs[info] = [(tp, tgt) for tp in out for tgt in [self.qualified(m, "types", tp.path, report=False)]
                          if isinstance(tgt, TypeInfo) and tgt.module is m]
        index, low, stack, on, comp_of, counter = {}, {}, [], set(), {}, [0]

        def visit(v):
            index[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on.add(v)
            for _, w in refs[v]:
                if w not in index:
                    visit(w)
                    low[v] = min(low[v], low[w])
                elif w in on:
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                comp = set()
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp.add(w)
                    if w is v:
                        break
                for w in comp:
                    comp_of[w] = comp
        for v in decls:
            if v not in index:
                visit(v)
        for info in decls:
            own = [g.name.text for g in getattr(info.decl, "params", [])]
            for tp, tgt in refs[info]:
                if tgt not in comp_of[info] or (len(comp_of[info]) == 1 and tgt is not info):
                    continue
                args = [a.path[0].text if isinstance(a, A.TypePath) and len(a.path) == 1 and not a.args else None
                        for a in tp.args]
                tgt_n = len(getattr(tgt.decl, "params", []))
                if args != own or len(args) != tgt_n:
                    self.d("IRREGULAR_RECURSIVE_TYPE", m, tp.start, tp.end, type=tgt.name)

    def type_paths(self, te, out):
        if isinstance(te, A.TypePath):
            out.append(te)
            for a in te.args:
                self.type_paths(a, out)
        elif isinstance(te, A.FnType):
            for p in te.params:
                self.type_paths(p, out)
            self.type_paths(te.ret, out)

    # ------------------------------------------------------------ сигнатуры
    def stores_and_events(self, m: ModuleInfo):
        """Таблицы и события всех модулей разрешаются до сигнатур: ряд может ссылаться на модуль, идущий позже."""
        for it in m.tree.items:
            d = it.decl
            if isinstance(d, A.StoreDecl):
                self.store(m, m.values[d.name.text], d)
            elif isinstance(d, A.EventDecl) and m.types[d.name.text].decl is d:
                self.event(m, m.types[d.name.text])

    def signatures(self, m: ModuleInfo):
        for it in m.tree.items:
            d = it.decl
            info = m.values.get(getattr(d, "name", A.Name(0, 0, "")).text)
            if isinstance(info, FnInfo) and info.decl is d:
                self.signature(m, info)

    def store(self, m: ModuleInfo, info: StoreInfo, d: A.StoreDecl):
        if info.decl is not d:
            return
        for t in d.tables:
            if t.name.text in info.tables:
                self.d("DUPLICATE_MEMBER", m, t.name.start, t.name.end, name=t.name.text, decl=info.name)
                continue
            ti = TableInfo(t.name.text, info, t)
            info.tables[t.name.text] = ti
            ty = self.resolve_type(t.type, m, Scope())
            if isinstance(ty, T.TError):
                ti.key = ti.value = T.TError()
            elif not (isinstance(ty, T.TCon) and ty.name == "Map"):
                self.d("TABLE_TYPE_NOT_MAP", m, t.type.start, t.type.end, name=t.name.text)
                ti.key = ti.value = T.TError()
            else:
                ti.key, ti.value = ty.args
                for arg, bound in ((ti.key, "Key"), (ti.value, "Persistable")):
                    if T.satisfies(arg, bound) is False:
                        self.d("BOUND_NOT_SATISFIED", m, t.type.start, t.type.end, type=T.show(arg), bound=bound)
            if t.derived_from is not None:
                tgt = self.qualified(m, "meanings", t.derived_from)
                if tgt is not False and not (isinstance(tgt, MeaningInfo) and tgt.kind == "entity"):
                    self.d("INVALID_LINK_TARGET", m, *span_of(t.derived_from),
                           path=".".join(n.text for n in t.derived_from))

    def event(self, m: ModuleInfo, info: TypeInfo):
        if m.is_std:
            return
        for f, (name, ty) in zip(info.decl.fields, info.fields):
            if T.satisfies(ty, "Persistable") is False:
                self.d("EVENT_NOT_PERSISTABLE", m, f.name.start, f.name.end, name=name)

    def signature(self, m: ModuleInfo, info: FnInfo):
        d = info.decl
        scope = self.generics(getattr(d, "generics", []), m)
        info.tparams = list(scope.rigids.values())
        info.eparams = list(scope.effects.items())
        if m.is_std and m.name == "std.store":
            scope.table_params = {p.name.text: k for k, p in enumerate(d.params)}
        params = list(getattr(d, "params", [])) + ([d.param] if hasattr(d, "param") else [])
        seen = set()
        for p in params:
            if p.name.text in seen:
                self.d("DUPLICATE_PARAMETER", m, p.name.start, p.name.end, name=p.name.text)
            seen.add(p.name.text)
            info.params.append(self.resolve_type(p.type, m, scope))
        info.ret = self.resolve_type(d.ret, m, scope) if getattr(d, "ret", None) is not None else T.UNIT
        row = self.resolve_row(d.uses, m, scope) if getattr(d, "uses", None) is not None else T.PURE
        if info.kind in CONTEXT_ATOMS:
            allowed = CONTEXT_ATOMS[info.kind]
            for it in d.uses.items if d.uses is not None else []:
                if it.kind not in allowed and it.kind != "host":   # host уже дал UNKNOWN_HOST_ADAPTER (CHK-03)
                    self.d("EFFECT_NOT_ALLOWED_IN_CONTEXT", m, it.start, it.end,
                           atom=it.kind + " " + ".".join(n.text for n in it.path), context=info.kind)
        if info.kind == "command":
            r = T.prune(info.ret)
            if not isinstance(r, T.TError) and not (isinstance(r, T.TCon) and r.name == "Result"):
                self.d("COMMAND_RESULT_NOT_RESULT", m, d.ret.start, d.ret.end)
        if info.kind == "handler":
            pt = info.params[0]
            if isinstance(pt, T.TNom) and pt.info.kind == "event":
                row = T.Row(row.atoms | {("consumes", pt.info.qname)})
            elif not isinstance(pt, T.TError):
                self.d("TYPE_MISMATCH", m, d.param.type.start, d.param.type.end, expected="event", actual=T.show(pt))
        if info.kind == "migration":
            tbl = self.lookup_table(m, d.table)
            if tbl is None:
                self.d("UNKNOWN_EFFECT_TARGET", m, *span_of(d.table), path=".".join(n.text for n in d.table))
            elif tbl is not False:
                info.table = tbl
                r = T.prune(info.ret)
                ok = isinstance(r, T.TCon) and r.name == "Result" and same(r.args[0], tbl.value)
                if not ok and not isinstance(r, T.TError) and not isinstance(tbl.value, T.TError):
                    self.d("MIGRATION_TYPE_MISMATCH", m, d.ret.start, d.ret.end, actual=T.show(r),
                           table=".".join(n.text for n in d.table), expected=T.show(tbl.value))
        info.row = row

    # ------------------------------------------------------------ связи
    def check_links(self, m: ModuleInfo):
        for it in m.tree.items:
            d = it.decl
            if isinstance(d, A.ContractDecl):
                tgt = self.qualified(m, "meanings", d.about)
                if tgt is not False and not (isinstance(tgt, MeaningInfo) and tgt.kind == "entity"):
                    self.d("INVALID_LINK_TARGET", m, *span_of(d.about), path=".".join(n.text for n in d.about))
                seen = set()
                for r in d.rules:
                    if r.name.text in seen:
                        self.d("DUPLICATE_MEMBER", m, r.name.start, r.name.end, name=r.name.text, decl=d.name.text)
                    seen.add(r.name.text)
        for it in m.tree.items:
            for lk in getattr(it.decl, "links", []):
                if lk.kind == "supersedes":
                    continue
                for path in lk.targets:
                    if self.link_target(m, path) is False:
                        self.d("INVALID_LINK_TARGET", m, *span_of(path), path=".".join(n.text for n in path))

    def link_target(self, m: ModuleInfo, path):
        """implements/requires/checks: сущность, контракт или Contract.rule (с необязательным псевдонимом модуля).
        True — цель есть; False — нет; None — непубличная цель, PRIVATE_ITEM уже выдан."""
        for k in (1, 2):
            if len(path) < k:
                continue
            head = self.qualified(m, "meanings", path[:k], report=True)
            if head is False:
                return None
            if isinstance(head, MeaningInfo):
                rest = path[k:]
                if not rest:
                    return True
                return head.kind == "contract" and len(rest) == 1 and rest[0].text in head.rules
        return False


def same(a, b) -> bool:
    try:
        T.unify(a, b)
        return True
    except T.UnifyError:
        return False
