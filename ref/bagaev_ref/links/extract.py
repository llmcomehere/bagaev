"""Извлечение графа связей из проверенной программы (spec/links/08-bagaev-extraction.md, LINKS-1).

Узлы — места SURF-07 (`@id`): модуль, декларации верхнего уровня, поля, варианты, таблицы, правила.
Рёбра — по фактическим местам в BIR-1 (вызовы, значения-функции, Perform) и по декларациям (типы, связи
implements/requires/checks/supersedes, about, derived_from, migrates, consumes, defines).
"""
from __future__ import annotations

import dataclasses

from bagaev_ref.ir import bir as B
from bagaev_ref.kernel import canonical as C
from bagaev_ref.sema import types as T
from bagaev_ref.sema.project import FnInfo, MeaningInfo, StoreInfo, TypeInfo
from bagaev_ref.syntax import ast as A

def _extractor_rev() -> str:
    """Ревизия извлекателя: версия правил и дайджест кода, от которого зависит граф — сам извлекатель,
    проверка и понижение, интерфейс std (LNK-08-11, D84). Смена любого из них — новый граф."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    parts = {rel: (root / rel).read_bytes().hex() for rel in
             ("links/extract.py", "sema/std.py", "sema/check.py", "sema/project.py", "sema/types.py", "ir/lower.py")}
    return "links-1@1+" + C.digest("extractor", "1", parts)[:16]


EXTRACTOR_REV = _extractor_rev()
READS = {"std.store.get@1", "std.store.contains@1", "std.store.all@1"}
WRITES = {"std.store.put@1", "std.store.remove@1", "std.store.replace_all@1"}
SKIP_FIELDS = {"start", "end", "doc", "pub_at", "op_start", "brace"}   # места и комментарии


# ------------------------------------------------------------ ревизии
def canon(node):
    """Каноническая форма поддерева AST без мест, комментариев и документации (LNK-08-02)."""
    if isinstance(node, A.Name):
        return node.text
    if dataclasses.is_dataclass(node):
        out = {"_": type(node).__name__}
        for f in dataclasses.fields(node):
            if f.name not in SKIP_FIELDS:
                out[f.name] = canon(getattr(node, f.name))
        return out
    if isinstance(node, (list, tuple)):
        if len(node) == 4 and isinstance(node[0], str) and isinstance(node[2], int):   # аргумент атрибута
            return [node[0], canon(node[1])]
        if len(node) == 3 and isinstance(node[0], str) and isinstance(node[1], int):   # цель supersedes
            return node[0]
        return [canon(x) for x in node]
    if isinstance(node, bool) or node is None or isinstance(node, str):
        return node
    if isinstance(node, int):
        return str(node)
    if isinstance(node, bytes):
        return {"hex": node.hex()}
    raise TypeError(type(node).__name__)


def rev_of(node) -> str:
    return C.digest("decl-rev", "1", canon(node))


def sig_of(decl) -> str:
    """Ревизия интерфейса функции: имя, обобщения, параметры, результат, ряд, связи — без тела."""
    parts = {f: canon(getattr(decl, f)) for f in ("name", "generics", "params", "param", "ret", "uses", "links")
             if hasattr(decl, f)}
    return C.digest("decl-sig", "1", parts)


def attr_id(node) -> str | None:
    for a in getattr(node, "attrs", []):
        if a.name.text == "id" and a.args:
            return a.args[0][1]
    return None


DECL_KIND = {A.FnDecl: "fn", A.HandlerDecl: "handler", A.MigrationDecl: "migration", A.TestDecl: "test",
             A.TypeDecl: "type", A.EntityDecl: "entity", A.ContractDecl: "contract", A.StoreDecl: "store",
             A.EventDecl: "event"}


class Extractor:
    def __init__(self, project, prog):
        self.p, self.prog = project, prog
        self.nodes, self.edges, self.gaps, self.unused = {}, [], [], []
        self.by_decl = {}                                # id(decl или узла с attrs) → EntityId
        self.qn = {}                                     # полное имя → EntityId (таблицы, события, функции)

    def node(self, eid, kind, name, file, span, rev, pub=False, sig=None, holder=None):
        n = {"id": eid, "kind": kind, "name": name, "file": file, "span": [str(span[0]), str(span[1])],
             "rev": rev, "pub": pub}
        if sig is not None:
            n["sig"] = sig
        self.nodes[eid] = n
        if holder is not None:
            self.by_decl[id(holder)] = eid
        return eid

    def edge(self, kind, src, dst, file, start, end, origin="structural", rule="", **qual):
        e = {"kind": kind, "src": src, "dst": dst, "site": {"file": file, "span": [str(start), str(end)]},
             "provenance": {"origin": origin, "rule": rule, "extractor": EXTRACTOR_REV}}
        if qual:
            e["qualifiers"] = qual
        self.edges.append(e)

    # ------------------------------------------------------------ узлы
    def collect_nodes(self):
        for m in self.p.user:
            mh = m.tree.module
            mid = self.node(attr_id(mh), "module", m.name, m.file, (mh.start, mh.end),
                            C.digest("decl-rev", "1", {"module": canon(mh), "uses": canon(m.tree.uses)}))
            for it in m.tree.items:
                d = it.decl
                kind = d.kind if isinstance(d, A.EntryDecl) else DECL_KIND[type(d)]
                name = f"{m.name}.{d.name.text}"
                sig = sig_of(d) if kind in ("fn", "command", "query", "handler", "migration", "test") else None
                eid = self.node(attr_id(it), kind, name, m.file, (it.start, it.end), rev_of(it), it.pub, sig, d)
                if getattr(d, "body", None) is not None:          # интерфейс — текст до тела (LNK-08-20)
                    self.nodes[eid]["head"] = [str(it.start), str(d.body.start)]
                self.qn[name] = eid
                self.edge("defines", mid, eid, m.file, d.name.start, d.name.end, rule="LNK-08-10")
                subs = []
                if isinstance(d, A.TypeDecl):
                    subs = [("field", x) for x in d.fields] + [("variant", x) for x in d.variants]
                elif isinstance(d, A.EventDecl):
                    subs = [("field", x) for x in d.fields]
                elif isinstance(d, A.StoreDecl):
                    subs = [("table", x) for x in d.tables]
                elif isinstance(d, A.ContractDecl):
                    subs = [("rule", x) for x in d.rules]
                for sk, x in subs:
                    sname = f"{name}.{x.name.text}"
                    sid = self.node(attr_id(x), sk, sname, m.file, (x.start, x.end), rev_of(x), holder=x)
                    self.qn[sname] = sid
                    self.edge("defines", eid, sid, m.file, x.name.start, x.name.end, rule="LNK-08-10")

    def fn_id(self, info: FnInfo):
        return self.by_decl.get(id(info.decl))

    def type_id(self, info: TypeInfo):
        return self.by_decl.get(id(info.decl))

    # ------------------------------------------------------------ типы
    def nominal(self, t, out: set):
        t = T.prune(t)
        if isinstance(t, T.TNom):
            if not t.info.module.is_std:
                out.add(t.info)
            for a in t.args:
                self.nominal(a, out)
        elif isinstance(t, T.TCon):
            for a in t.args:
                self.nominal(a, out)
        elif isinstance(t, T.TFn):
            for a in t.params:
                self.nominal(a, out)
            self.nominal(t.ret, out)

    def uses_types(self, src, file, types_with_sites):
        """uses_type агрегируется по паре (источник, тип); место — первое в исходнике (LNK-08-05)."""
        first = {}
        for t, s, e in types_with_sites:
            found = set()
            self.nominal(t, found)
            for info in found:
                tid = self.type_id(info)
                if tid is not None and tid != src and (tid not in first or (s, e) < first[tid]):
                    first[tid] = (s, e)
        for tid, (s, e) in sorted(first.items()):
            self.edge("uses_type", src, tid, file, s, e, rule="LNK-08-05")

    def body_types(self, body):
        out = []

        def walk(n):
            if isinstance(n, A.Node):
                t = self.p.types.get(id(n))
                if t is not None:
                    out.append((t, n.start, n.end))
                for f in dataclasses.fields(n):
                    walk(getattr(n, f.name))
            elif isinstance(n, (list, tuple)):
                for x in n:
                    walk(x)
        walk(body)
        return out

    # ------------------------------------------------------------ тела: BIR
    def bir_edges(self, src, fn: B.Function):
        def walk(n, callee=False):
            if not isinstance(n, B.Node):
                return
            if n.k == B.GLOBAL:
                info = n.fn.info
                f, s, e = n.site
                dst = "std:" + info.qname if info.module.is_std else self.fn_id(info)   # std — внешняя цель
                self.edge("calls" if callee else "references", src, dst, f, s, e,
                          rule="LNK-08-03" if callee else "LNK-08-04")
                return
            if n.k == B.PRIM and n.name.startswith("std."):
                f, s, e = n.site
                self.edge("calls", src, "std:" + n.name.rsplit("@", 1)[0], f, s, e, rule="LNK-08-03")
            if n.k == B.PERFORM:
                f, s, e = n.site
                if n.op in READS or n.op in WRITES:
                    self.edge("reads" if n.op in READS else "writes", src, self.qn[n.resource], f, s, e,
                              rule="LNK-08-06", op=n.op)
                else:
                    self.edge("emits", src, self.qn[n.resource], f, s, e, rule="LNK-08-06")
            if n.k == B.CALL:
                walk(n.fn, callee=True)
                for a in n.args:
                    walk(a)
                return
            for slot in n.__slots__:
                inner(getattr(n, slot, None))

        def inner(v):                                    # поля узлов: узел, список, кортеж, словарь ветвей Match
            if isinstance(v, B.Node):
                walk(v)
            elif isinstance(v, (list, tuple)):
                for x in v:
                    inner(x)
            elif isinstance(v, dict):
                for x in v.values():
                    inner(x)
        walk(fn.body)

    # ------------------------------------------------------------ декларации
    def meaning(self, m, path):
        """Цель связи: сущность, контракт или правило (SURF-15); None — не найдена."""
        for k in (1, 2):
            if len(path) < k:
                continue
            head = self.p.qualified(m, "meanings", path[:k], report=False)
            if isinstance(head, MeaningInfo):
                rest = path[k:]
                hid = self.by_decl.get(id(head.decl))
                if not rest:
                    return hid
                if head.kind == "contract" and len(rest) == 1:
                    return self.qn.get(f"{head.module.name}.{head.name}.{rest[0].text}")
        return None

    def decl_edges(self, only=None):
        for m in self.p.user:
            if only is not None and m.name not in only:
                continue
            for it in m.tree.items:
                d = it.decl
                src = self.by_decl[id(d)]
                info = m.values.get(d.name.text) if hasattr(d, "name") else None
                for lk in getattr(d, "links", []):
                    for tgt in lk.targets:
                        if lk.kind == "supersedes":
                            sid, s, e = tgt
                            self.edge("supersedes", src, sid, m.file, s, e, origin="declared", rule="LNK-08-08",
                                      verified=False)
                            self.gaps.append({"entity": src, "reason": "SUPERSEDES_HISTORY_UNCHECKED", "target": sid})
                            continue
                        dst = self.meaning(m, tgt)
                        self.edge(lk.kind, src, dst, m.file, tgt[0].start, tgt[-1].end, origin="declared",
                                  rule="LNK-08-08")
                if isinstance(d, A.ContractDecl):
                    self.edge("about", src, self.meaning(m, d.about), m.file, d.about[0].start, d.about[-1].end,
                              origin="declared", rule="LNK-08-08")
                if isinstance(info, FnInfo) and info.module is m:
                    fn = self.prog.functions[info]
                    sig_types = [(t, d.start, d.end) for t in info.params] + [(info.ret, d.start, d.end)]
                    self.uses_types(src, m.file, sig_types + self.body_types(d.body))
                    self.bir_edges(src, fn)
                    unused = sorted({T.show_atom(x) for x in info.row.atoms} - {T.show_atom(x) for x in info.actual}
                                    - ({"consumes " + T.prune(info.params[0]).info.qname} if info.kind == "handler" else set()))
                    for atom in unused:                      # объявленная граница без места (EFF-12): не ребро
                        self.unused.append({"entity": src, "atom": atom})
                    if info.kind == "handler":
                        pt = T.prune(info.params[0])
                        self.edge("consumes", src, self.type_id(pt.info), m.file, d.param.start, d.param.end,
                                  rule="LNK-08-07")
                    if info.kind == "migration":
                        self.edge("migrates", src, self.qn[info.table.qname], m.file, d.table[0].start,
                                  d.table[-1].end, rule="LNK-08-09")
                if isinstance(d, (A.TypeDecl, A.EventDecl)):
                    tinfo = m.types[d.name.text]
                    for x in d.fields:
                        ft = dict(tinfo.fields)[x.name.text]
                        self.uses_types(self.by_decl[id(x)], m.file, [(ft, x.type.start, x.type.end)])
                    for x in getattr(d, "variants", []):
                        pt = dict(tinfo.variants)[x.name.text]
                        if pt is not None:
                            self.uses_types(self.by_decl[id(x)], m.file, [(pt, x.payload.start, x.payload.end)])
                    if getattr(d, "rep", None) is not None:
                        self.uses_types(src, m.file, [(tinfo.rep, d.rep.start, d.rep.end)])
                if isinstance(d, A.StoreDecl):
                    sinfo = m.values[d.name.text]
                    for x in d.tables:
                        tbl = sinfo.tables[x.name.text]
                        tid = self.by_decl[id(x)]
                        self.uses_types(tid, m.file, [(tbl.key, x.type.start, x.type.end), (tbl.value, x.type.start, x.type.end)])
                        if x.derived_from:
                            self.edge("derived_from", tid, self.meaning(m, x.derived_from), m.file,
                                      x.derived_from[0].start, x.derived_from[-1].end, origin="declared", rule="LNK-08-08")

    def run(self, source_digest: str, only=None, reuse_edges=(), reuse_gaps=(), reuse_unused=()) -> dict:
        """only — модули, чьи рёбра извлекаются заново; reuse_* — готовые рёбра и пробелы остальных (LNK-08-18)."""
        self.collect_nodes()
        if only is not None:
            self.edges = [e for e in self.edges if e["kind"] == "defines"]   # defines — из узлов, всегда заново
        self.decl_edges(only)
        for m in self.p.user:
            if only is not None and m.name not in only:
                continue
            for it in m.tree.items:
                d = it.decl
                if isinstance(d, A.EntryDecl) and it.pub:
                    self.gaps.append({"entity": self.by_decl[id(d)], "reason": "EXTERNAL_CONSUMERS"})
        self.edges += [dict(e) for e in reuse_edges if e["kind"] != "defines"]
        self.gaps += [dict(g) for g in reuse_gaps]
        self.unused += [dict(u) for u in reuse_unused]
        for e in self.edges:
            e["id"] = C.digest("edge", "1", {k: e[k] for k in ("kind", "src", "dst", "site")})[:24]
        edges = sorted(self.edges, key=lambda e: (e["kind"], e["src"], e["dst"], e["site"]["file"],
                                                  int(e["site"]["span"][0]), e["id"]))
        gaps = sorted(self.gaps, key=lambda g: (g["entity"], g["reason"], g.get("target", "")))
        unused = sorted(self.unused, key=lambda u: (u["entity"], u["atom"]))
        return {"format": "bagaev-graph/1", "extractor_rev": EXTRACTOR_REV, "source": source_digest,
                "nodes": [self.nodes[k] for k in sorted(self.nodes)], "edges": edges,
                "coverage": coverage(), "gaps": gaps, "unused_atoms": unused}


def coverage() -> dict:
    """CoverageRecord LINKS-1: полнота по видам рёбер и её основания (LNK-08-11, EFF-13)."""
    complete = {
        "calls": "вызов функции группы — узел Global в позиции вызова BIR-1; иных способов вызвать объявление нет",
        "references": "функция как значение — Global вне позиции вызова; вызов через значение достижим только из её ссылок",
        "reads": "таблица — статический путь (EFF-07), операция std.store — Perform с ресурсом",
        "writes": "то же, что reads",
        "emits": "emit — Perform event.emit@1 с ресурсом",
        "consumes": "параметр handler — тип события (EFF-09)",
        "uses_type": "все номинальные типы сигнатуры и выражений тела по типам проверки",
        "migrates": "migration … on — статический путь таблицы",
        "defines": "все места SURF-07",
        "implements": "синтаксис связей SURF-15",
        "requires": "синтаксис связей SURF-15",
        "checks": "синтаксис связей SURF-15",
        "about": "contract … about",
        "derived_from": "table … derived_from",
    }
    out = {k: {"status": "COMPLETE", "basis": v} for k, v in complete.items()}
    out["supersedes"] = {"status": "PARTIAL", "basis": "цель — строка ID истории проекта; сверка с принятыми снимками — Ф6"}
    return {"kinds": out, "scope": "проект целиком: все модули корня; std — часть ревизии извлекателя",
            "external_boundaries": ["вызывающие точек входа вне программы (EXTERNAL_CONSUMERS)",
                                    "std: внешние цели std:<имя> без узлов; интерфейс std входит в extractor_rev"]}


def source_digest(files) -> str:
    return C.digest("source-set", "1", {f: b.hex() for f, b in sorted(files)})


def extract(project, prog, files) -> dict:
    return Extractor(project, prog).run(source_digest(files))
