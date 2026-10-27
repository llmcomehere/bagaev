"""Узлы BIR-1 (spec/ir/bir.md). Каждый узел несёт nid и место в исходнике (файл, start, end).

Имена форм — §2 BIR-1. Целочисленный код `k` нужен только для быстрого ветвления машины.
Локальные имена разрешены в индексы: `Local(i)` — i-е по счёту от ближайшего связывания (0 — последнее).
"""
from __future__ import annotations

CONST, LOCAL, GLOBAL, LET, LAMBDA, CALL, IF, MATCH, VARIANT, RECORD, FIELD, SEQ, MAP, PRIM, RETURN, PERFORM = range(16)
FORM_NAMES = ["Const", "Local", "Global", "Let", "Lambda", "Call", "If", "Match", "Variant", "Record", "Field",
              "SeqLit", "MapBuild", "Prim", "Return", "Perform"]


class Node:
    __slots__ = ("k", "nid", "site", "ty")       # ty — статический тип (для наблюдения и моста; машина не читает)

    def fields(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


class Const(Node):
    __slots__ = ("value",)

    def __init__(self, nid, site, value):
        self.k, self.nid, self.site, self.value = CONST, nid, site, value


class Local(Node):
    __slots__ = ("index", "name")

    def __init__(self, nid, site, index, name):
        self.k, self.nid, self.site, self.index, self.name = LOCAL, nid, site, index, name


class Global(Node):
    """Член группы функций модуля (LetRec модуля, связанный до запуска)."""
    __slots__ = ("fn",)

    def __init__(self, nid, site, fn):
        self.k, self.nid, self.site, self.fn = GLOBAL, nid, site, fn


class Let(Node):
    __slots__ = ("name", "value", "body")

    def __init__(self, nid, site, name, value, body):
        self.k, self.nid, self.site, self.name, self.value, self.body = LET, nid, site, name, value, body


class Lambda(Node):
    __slots__ = ("arity", "body")

    def __init__(self, nid, site, arity, body):
        self.k, self.nid, self.site, self.arity, self.body = LAMBDA, nid, site, arity, body


class Call(Node):
    __slots__ = ("fn", "args")

    def __init__(self, nid, site, fn, args):
        self.k, self.nid, self.site, self.fn, self.args = CALL, nid, site, fn, args


class If(Node):
    __slots__ = ("cond", "then", "els")

    def __init__(self, nid, site, cond, then, els):
        self.k, self.nid, self.site, self.cond, self.then, self.els = IF, nid, site, cond, then, els


class Match(Node):
    """arms: тег → (связывает ли нагрузку, тело). opaque — разбор непрозрачного типа (одна ветвь)."""
    __slots__ = ("scrutinee", "arms", "opaque")

    def __init__(self, nid, site, scrutinee, arms, opaque=False):
        self.k, self.nid, self.site = MATCH, nid, site
        self.scrutinee, self.arms, self.opaque = scrutinee, arms, opaque


class Variant(Node):
    """Вариант суммы с нагрузкой или конструктор opaque (ordinal = -1, представление — сама нагрузка)."""
    __slots__ = ("tag", "ordinal", "payload")

    def __init__(self, nid, site, tag, ordinal, payload):
        self.k, self.nid, self.site, self.tag, self.ordinal, self.payload = VARIANT, nid, site, tag, ordinal, payload


class Record(Node):
    """entries — (слот поля, выражение) в исходном порядке; nfields — число полей по объявлению."""
    __slots__ = ("entries", "nfields")

    def __init__(self, nid, site, entries, nfields):
        self.k, self.nid, self.site, self.entries, self.nfields = RECORD, nid, site, entries, nfields


class Field(Node):
    __slots__ = ("target", "index")

    def __init__(self, nid, site, target, index):
        self.k, self.nid, self.site, self.target, self.index = FIELD, nid, site, target, index


class SeqLit(Node):
    __slots__ = ("items",)

    def __init__(self, nid, site, items):
        self.k, self.nid, self.site, self.items = SEQ, nid, site, items


class MapBuild(Node):
    """items — ключ и значение каждой пары подряд: k0, v0, k1, v1…"""
    __slots__ = ("items",)

    def __init__(self, nid, site, items):
        self.k, self.nid, self.site, self.items = MAP, nid, site, items


class Prim(Node):
    __slots__ = ("name", "args", "fn")

    def __init__(self, nid, site, name, args, fn):
        self.k, self.nid, self.site, self.name, self.args, self.fn = PRIM, nid, site, name, args, fn


class Return(Node):
    __slots__ = ("value",)

    def __init__(self, nid, site, value):
        self.k, self.nid, self.site, self.value = RETURN, nid, site, value


class Perform(Node):
    """Операция хоста: std.store и emit (EFF-01). Исполняет хост в транзакции (Ф4)."""
    __slots__ = ("op", "resource", "args")

    def __init__(self, nid, site, op, resource, args):
        self.k, self.nid, self.site, self.op, self.resource, self.args = PERFORM, nid, site, op, resource, args


class Function:
    """Член группы функций модуля: имя, арность, тело; глобальная функция — замыкание без окружения."""
    __slots__ = ("qname", "arity", "body", "info", "closure")

    def __init__(self, qname, arity, info):
        self.qname, self.arity, self.info, self.body, self.closure = qname, arity, info, None, None


def walk(node):
    """Обход дерева в прямом порядке (для дампа и проверок)."""
    yield node
    for s in node.__slots__:
        v = getattr(node, s)
        if isinstance(v, Node):
            yield from walk(v)
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, Node):
                    yield from walk(x)
                elif isinstance(x, tuple):
                    for y in x:
                        if isinstance(y, Node):
                            yield from walk(y)
        elif isinstance(v, dict):
            for x in v.values():
                if isinstance(x, tuple) and isinstance(x[1], Node):
                    yield from walk(x[1])
