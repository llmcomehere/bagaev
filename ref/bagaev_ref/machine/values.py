"""Значения MACHINE-1 (spec/runtime/machine.md §2). Типы стёрты (D75): значение не хранит свой тип,
наблюдение строится по статическому типу (CANON-11).

Int64 — int, Bool — bool, String — str, Bytes — bytes, Unit — None, Seq — tuple, Map — MapV,
запись — Rec, вариант — Var, opaque — само представление, функция — Clo.
"""
from __future__ import annotations

NOPAY = object()                   # вариант без нагрузки


class Var:
    __slots__ = ("ordinal", "tag", "payload")

    def __init__(self, ordinal: int, tag: str, payload=NOPAY):
        self.ordinal, self.tag, self.payload = ordinal, tag, payload

    def __eq__(self, other):
        return isinstance(other, Var) and self.ordinal == other.ordinal and self.payload == other.payload

    def __hash__(self):
        return hash(("Var", self.ordinal, None if self.payload is NOPAY else self.payload))

    def __repr__(self):
        return self.tag if self.payload is NOPAY else f"{self.tag}({self.payload!r})"


class Rec:
    __slots__ = ("fields",)

    def __init__(self, fields: tuple):
        self.fields = fields

    def __eq__(self, other):
        return isinstance(other, Rec) and self.fields == other.fields

    def __hash__(self):
        return hash(("Rec", self.fields))

    def __repr__(self):
        return "Rec" + repr(self.fields)


class MapV:
    """Неизменяемая карта: dict ключ → значение; порядок записей — порядок Key (CANON-11)."""
    __slots__ = ("d",)

    def __init__(self, d: dict):
        self.d = d

    def __eq__(self, other):
        return isinstance(other, MapV) and self.d == other.d

    def __hash__(self):
        return hash(("Map", frozenset(self.d.items())))

    def entries(self) -> list:
        return sorted(self.d.items(), key=lambda kv: key_of(kv[0]))


class Clo:
    """Замыкание: тело, арность, захваченное окружение (связный список (значение, родитель))."""
    __slots__ = ("body", "arity", "env", "name")

    def __init__(self, body, arity, env, name=None):
        self.body, self.arity, self.env, self.name = body, arity, env, name


def key_of(v):
    """Ключ полного порядка Key (data-values.md §6) для сравнения средствами Python."""
    if isinstance(v, bool):
        return (0, int(v))
    if isinstance(v, (int, str, bytes)):
        return v
    if v is None:
        return 0
    if isinstance(v, tuple):
        return tuple(key_of(x) for x in v)
    if isinstance(v, Var):
        return (v.ordinal,) if v.payload is NOPAY else (v.ordinal, key_of(v.payload))
    if isinstance(v, Rec):
        return tuple(key_of(x) for x in v.fields)
    raise TypeError(f"нет порядка Key для {type(v).__name__}")


def compare(a, b) -> int:
    ka, kb = key_of(a), key_of(b)
    return -1 if ka < kb else (1 if ka > kb else 0)


def ok(x):
    return Var(0, "Ok", x)


def err(x):
    return Var(1, "Err", x)


def some(x):
    return Var(1, "Some", x)


NONE = Var(0, "None")
