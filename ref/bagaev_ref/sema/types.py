"""Типы проверки: monotype TYPES-0.1 §2, ряды эффектов EFFECTS-1 §2, унификация §4, предикаты §9.

Номинальный тип сравнивается по объявлению (TypeInfo), а не по имени. Meta существуют только во время
проверки тела; ряд с RowMeta — ряд вызова обобщённой функции до вычисления ρ(e) (EFF-06).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count

BUILTIN_ARITY = {"Bool": 0, "Int64": 0, "String": 0, "Bytes": 0, "Unit": 0, "Never": 0,
                 "Option": 1, "Result": 2, "Seq": 1, "Map": 2, "Table": 2}
SCALARS = {"Bool", "Int64", "String", "Bytes", "Unit", "Never"}
BOUNDS = ("Eq", "Key", "Persistable")
_ids = count(1)


class Type:
    pass


@dataclass(eq=False)
class TCon(Type):
    """Встроенный конструктор: скаляры, Option, Result, Seq, Map, Table."""
    name: str
    args: list = field(default_factory=list)


@dataclass(eq=False)
class TNom(Type):
    """Пользовательский или std номинальный тип: record, enum, opaque, event."""
    info: object                       # sema.project.TypeInfo
    args: list = field(default_factory=list)


@dataclass(eq=False)
class TRigid(Type):
    name: str
    bounds: frozenset
    uid: int = field(default_factory=lambda: next(_ids))


@dataclass(eq=False)
class TMeta(Type):
    ref: Type | None = None
    uid: int = field(default_factory=lambda: next(_ids))
    lambda_param: object = None        # (имя, start, end) — meta параметра лямбды (PARAMETER_TYPE_REQUIRED)
    site: object = None                # место специализации для AMBIGUOUS_TYPE_ARGUMENT


@dataclass(eq=False)
class TFn(Type):
    params: list
    ret: Type
    row: "Row"


@dataclass(eq=False)
class TError(Type):
    """Тип после уже выданной ошибки: совместим со всем, каскада диагностик нет."""


@dataclass(eq=False)
class RowMeta:
    """Эффект-переменная на месте вызова: ρ(e) — объединение вкладов аргументов (EFF-06)."""
    name: str
    solution: frozenset | None = None
    contributions: list = field(default_factory=list)   # (atoms, exact: bool, start, end)
    checks: list = field(default_factory=list)          # (ожидаемые атомы, известные атомы, start, end): после ρ(e)


@dataclass(eq=False)
class Row:
    atoms: frozenset = frozenset()
    meta: RowMeta | None = None

    def resolved(self) -> "Row":
        if self.meta is not None and self.meta.solution is not None:
            return Row(self.atoms | self.meta.solution)
        return self


PURE = Row()
UNIT, BOOL, INT, STRING, BYTES, NEVER = (TCon(n) for n in ("Unit", "Bool", "Int64", "String", "Bytes", "Never"))


def prune(t: Type) -> Type:
    while isinstance(t, TMeta) and t.ref is not None:
        t = t.ref
    return t


def zonk(t: Type) -> Type:
    t = prune(t)
    if isinstance(t, TCon):
        return TCon(t.name, [zonk(a) for a in t.args]) if t.args else t
    if isinstance(t, TNom):
        return TNom(t.info, [zonk(a) for a in t.args]) if t.args else t
    if isinstance(t, TFn):
        return TFn([zonk(p) for p in t.params], zonk(t.ret), t.row.resolved())
    return t


def metas(t: Type, out: list) -> list:
    t = prune(t)
    if isinstance(t, TMeta):
        if t not in out:
            out.append(t)
    elif isinstance(t, (TCon, TNom)):
        for a in t.args:
            metas(a, out)
    elif isinstance(t, TFn):
        for p in t.params:
            metas(p, out)
        metas(t.ret, out)
    return out


def subst(t: Type, m: dict, rows: dict | None = None) -> Type:
    """Подстановка параметров объявления (TRigid по uid) и эффект-переменных (атом ("var", uid) → Row)."""
    t = prune(t)
    if isinstance(t, TRigid):
        return m.get(t.uid, t)
    if isinstance(t, TCon):
        return TCon(t.name, [subst(a, m, rows) for a in t.args]) if t.args else t
    if isinstance(t, TNom):
        return TNom(t.info, [subst(a, m, rows) for a in t.args]) if t.args else t
    if isinstance(t, TFn):
        return TFn([subst(p, m, rows) for p in t.params], subst(t.ret, m, rows), subst_row(t.row, rows or {}))
    return t


def subst_row(r: Row, rows: dict) -> Row:
    atoms, meta = set(), r.meta
    for a in r.atoms:
        if a[0] == "var" and a[1] in rows:
            repl = rows[a[1]]
            if isinstance(repl, RowMeta):
                meta = repl
            else:
                atoms |= repl
        else:
            atoms.add(a)
    return Row(frozenset(atoms), meta)


# ------------------------------------------------------------ отображение
def show(t: Type) -> str:
    t = prune(t)
    if isinstance(t, TCon):
        if t.name == "Unit":
            return "()"
        return t.name + ("<" + ", ".join(show(a) for a in t.args) + ">" if t.args else "")
    if isinstance(t, TNom):
        return t.info.qname + ("<" + ", ".join(show(a) for a in t.args) + ">" if t.args else "")
    if isinstance(t, TRigid):
        return t.name
    if isinstance(t, TMeta):
        return "_"
    if isinstance(t, TFn):
        s = "fn(" + ", ".join(show(p) for p in t.params) + ") -> " + show(t.ret)
        r = show_row(t.row)
        return s + (" uses " + r if r != "{}" else "")
    return "<ошибка>"


def show_atom(a) -> str:
    if a[0] == "var":
        return a[2]
    return a[0] + " " + a[1]


ATOM_ORDER = {"reads": 0, "writes": 1, "emits": 2, "host": 3, "consumes": 4, "var": 5}


def sorted_atoms(atoms) -> list:
    return sorted(atoms, key=lambda a: (ATOM_ORDER[a[0]], show_atom(a)))


def show_row(r: Row) -> str:
    r = r.resolved()
    parts = [show_atom(a) for a in sorted_atoms(r.atoms) if a[0] != "var"]
    var = [show_atom(a) for a in r.atoms if a[0] == "var"] + ([r.meta.name] if r.meta is not None else [])
    s = ", ".join(parts)
    if var:
        s += (" | " if s else "| ") + ", ".join(var)
    return "{ " + s + " }" if s else "{}"


# ------------------------------------------------------------ унификация
class UnifyError(Exception):
    def __init__(self, code: str, data: dict):
        super().__init__(code)
        self.code, self.data = code, data


def occurs(m: TMeta, t: Type) -> bool:
    t = prune(t)
    if t is m:
        return True
    if isinstance(t, (TCon, TNom)):
        return any(occurs(m, a) for a in t.args)
    if isinstance(t, TFn):
        return any(occurs(m, p) for p in t.params) or occurs(m, t.ret)
    return False


def unify(expected: Type, actual: Type, site=None):
    """expected ← actual. Выражение типа Never совместимо с любым ожидаемым типом, но не наоборот: значений
    типа Never нет (TYPES-0.1 §2, §7). TError гасит каскад."""
    a, b = prune(expected), prune(actual)
    if a is b:
        return
    if isinstance(a, TError) or isinstance(b, TError):
        return
    if isinstance(b, TCon) and b.name == "Never":
        return
    if isinstance(a, TMeta) or isinstance(b, TMeta):
        m, other = (a, b) if isinstance(a, TMeta) else (b, a)
        if occurs(m, other):
            raise UnifyError("OCCURS_CHECK", {"meta": "_", "type": show(other)})
        m.ref = other
        return
    if isinstance(a, TRigid) or isinstance(b, TRigid):
        r, other = (a, b) if isinstance(a, TRigid) else (b, a)
        raise UnifyError("RIGID_TYPE_MISMATCH", {"param": r.name, "actual": show(other)})
    mismatch = UnifyError("TYPE_MISMATCH", {"expected": show(a), "actual": show(b)})
    if type(a) is not type(b):
        raise mismatch
    if isinstance(a, TCon):
        if a.name != b.name or len(a.args) != len(b.args):
            raise mismatch
        for x, y in zip(a.args, b.args):
            _unify_inner(x, y, mismatch, site)
        return
    if isinstance(a, TNom):
        if a.info is not b.info:
            raise mismatch
        for x, y in zip(a.args, b.args):
            _unify_inner(x, y, mismatch, site)
        return
    if isinstance(a, TFn):
        if len(a.params) != len(b.params):
            raise mismatch
        for x, y in zip(a.params, b.params):
            _unify_inner(x, y, mismatch, site)
        _unify_inner(a.ret, b.ret, mismatch, site)
        unify_rows(a.row, b.row, mismatch, site)
        return
    raise mismatch


def _unify_inner(x, y, outer: UnifyError, site):
    """Вложенное несовпадение сообщается целыми типами (ожидался/получен), а не их частями."""
    try:
        unify(x, y, site)
    except UnifyError as e:
        if e.code == "TYPE_MISMATCH":
            raise outer from None
        raise


def unify_rows(expected: Row, actual: Row, mismatch: UnifyError, site):
    """Ряды fn-типов совпадают точно; ряд с RowMeta получает вклад «точное совпадение» (EFF-06 п. 2)."""
    e, a = expected.resolved(), actual.resolved()
    if e.meta is not None and e.meta.solution is None:
        extra = a.atoms - e.atoms
        if not e.atoms <= a.atoms or a.meta is not None and a.meta is not e.meta:
            raise mismatch
        start, end = site if site else (0, 0)
        e.meta.contributions.append((frozenset(extra), True, start, end))
        return
    if a.meta is not None and a.meta.solution is None:
        if a.meta is not e.meta:
            start, end = site if site else (0, 0)
            a.meta.checks.append((e.atoms, a.atoms, start, end))   # ρ(e) задают аргументы, не ожидаемый тип
        return
    if e.atoms != a.atoms:
        raise mismatch


# ------------------------------------------------------------ предикаты Eq / Key / Persistable
def satisfies(t: Type, bound: str, path: frozenset = frozenset()) -> bool | None:
    """Структурный предикат TYPES-0.1 §9 как наибольшая неподвижная точка (D69). None — тип ещё не известен."""
    t = prune(t)
    if isinstance(t, (TError,)):
        return True
    if isinstance(t, TMeta):
        return None
    if isinstance(t, TRigid):
        return bound in t.bounds or (bound == "Eq" and "Key" in t.bounds)
    if isinstance(t, TFn):
        return False
    if isinstance(t, TCon):
        if t.name in SCALARS:
            return True
        if t.name == "Table":
            return False
        if t.name == "Map":
            k, v = t.args
            if bound == "Key":
                return False
            if bound == "Eq":
                return _all([satisfies(k, "Key", path), satisfies(v, "Eq", path)])
            return _all([satisfies(k, "Key", path), satisfies(k, "Persistable", path), satisfies(v, "Persistable", path)])
        return _all([satisfies(a, bound, path) for a in t.args])
    if isinstance(t, TNom):
        key = (bound, id(t.info), tuple(show(a) for a in t.args))
        if key in path:
            return True
        path = path | {key}
        return _all([satisfies(ft, bound, path) for ft in t.info.member_types(t.args)])
    return False


def _all(vals) -> bool | None:
    if any(v is False for v in vals):
        return False
    if any(v is None for v in vals):
        return None
    return True
