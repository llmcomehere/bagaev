"""Примитивы MACHINE-1: функции std с телом `{}` и примитивы операторов (spec/runtime/machine.md §5,
spec/stdlib/api.md). Каждый — одно применение PRIM_APPLY; FAULT — исключение Fault.

Имена — `std.<модуль>.<функция>@1` для std и `op.<имя>@1` для операторов исходника (SURF-33…SURF-38).
"""
from __future__ import annotations

from bagaev_ref.machine.values import NONE, MapV, Rec, Var, compare, err, key_of, ok, some

MIN, MAX = -2**63, 2**63 - 1


class Fault(Exception):
    """Определённая языком остановка программы (OUT-01 FAULT)."""

    def __init__(self, code: str, **data):
        super().__init__(code)
        self.code, self.data = code, data


class NotImplementedPrim(Exception):
    """Примитив, контракт которого ещё не закрыт (codec — BD07): IMPLEMENTATION_STOP NOT_IMPLEMENTED."""


# ------------------------------------------------------------ std.i64 (STD-002…STD-011, errors.md)
OVERFLOW = Var(0, "Overflow")
DIV_ZERO = Var(1, "DivisionByZero")


def _checked(v):
    return ok(v) if MIN <= v <= MAX else err(OVERFLOW)


def _quot(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def i64_div(a, b):
    if b == 0:
        return err(DIV_ZERO)
    return _checked(_quot(a, b))


def i64_rem(a, b):
    if b == 0:
        return err(DIV_ZERO)
    return ok(a - _quot(a, b) * b)


def _trap(r):
    if r.ordinal == 1:
        raise Fault("DIVISION_BY_ZERO" if r.payload is DIV_ZERO else "ARITHMETIC_OVERFLOW")
    return r.payload


PARSE_REASONS = ["Empty", "SignOnly", "LeadingZero", "InvalidDigit"]


def parse_decimal(s: str):
    """stdlib/types.md §4: синтаксис всей строки, затем диапазон (SA-010). Индексы — позиции scalar values."""
    def bad(index, reason):
        syntax = Rec((index, Var(PARSE_REASONS.index(reason), reason)))
        return err(Var(0, "InvalidSyntax", syntax))
    if s == "":
        return bad(0, "Empty")
    i = 1 if s[0] == "-" else 0
    if i == len(s):
        return bad(1, "SignOnly")                      # единственный минус
    if not ("0" <= s[i] <= "9"):
        return bad(i, "InvalidDigit")                  # начальный плюс или не-ASCII-цифра
    if s[i] == "0":
        if i + 1 < len(s):
            return bad(i + 1, "LeadingZero")           # после первого нуля любой следующий символ
        return ok(0)
    for j in range(i + 1, len(s)):
        if not ("0" <= s[j] <= "9"):
            return bad(j, "InvalidDigit")
    v = int(s)
    return ok(v) if MIN <= v <= MAX else err(Var(1, "OutOfRange"))


# ------------------------------------------------------------ std.data
DATA_CODES = ["DuplicateKey", "Utf8Leading", "Utf8Continuation", "Utf8Overlong", "Utf8Surrogate", "Utf8Range",
              "Utf8Truncated", "UnexpectedEnd", "ContextMismatch", "InvalidEncoding", "UnknownVariant",
              "NonCanonicalMap", "TrailingBytes"]


def data_error(code: str, first: int, second: int):
    return Rec((Var(DATA_CODES.index(code), code), first, second))


def bounds(length, start, end):
    """Ok, если 0 ≤ start ≤ end ≤ length; иначе Err(BoundsError{length, start, end}) без подрезки (SX-013)."""
    if 0 <= start <= end <= length:
        return None
    return err(Rec((length, start, end)))


# ------------------------------------------------------------ коллекции
def seq_get(xs, i):
    return some(xs[i]) if 0 <= i < len(xs) else NONE


def seq_slice(xs, a, b):
    return bounds(len(xs), a, b) or ok(xs[a:b])


def first_duplicate(keys: list):
    """Первая повторная позиция и первая предшествующая равная (data-values §4)."""
    seen = {}
    for i, k in enumerate(keys):
        if k in seen:
            return seen[k], i
        seen[k] = i
    return None


def map_build(entries):
    keys = [e.fields[0] for e in entries]
    dup = first_duplicate(keys)
    if dup:
        return err(data_error("DuplicateKey", dup[0], dup[1]))
    return ok(MapV({e.fields[0]: e.fields[1] for e in entries}))


def map_put(m, k, v):
    d = dict(m.d)
    d[k] = v
    return MapV(d)


def map_remove(m, k):
    d = dict(m.d)
    d.pop(k, None)
    return MapV(d)


def map_get(m, k):
    return some(m.d[k]) if k in m.d else NONE


# ------------------------------------------------------------ строки и байты
def from_scalars(xs):
    for i, v in enumerate(xs):
        if not (0 <= v <= 0x10FFFF) or 0xD800 <= v <= 0xDFFF:
            return err(Rec((i, v)))
    return ok("".join(chr(v) for v in xs))


def from_octets(xs):
    for i, v in enumerate(xs):
        if not 0 <= v <= 255:
            return err(Rec((i, v)))
    return ok(bytes(xs))


def utf8_decode(b: bytes):
    """Строгий UTF-8 с классом первой ошибки: first — смещение байта, second = −1 (stdlib/types.md)."""
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c < 0x80:
            i += 1
            continue
        if 0xC2 <= c <= 0xDF:
            need, lo, hi = 1, 0x80, 0xBF
        elif 0xE0 <= c <= 0xEF:
            need = 2
            lo, hi = (0xA0, 0xBF) if c == 0xE0 else (0x80, 0x9F) if c == 0xED else (0x80, 0xBF)
        elif 0xF0 <= c <= 0xF4:
            need = 3
            lo, hi = (0x90, 0xBF) if c == 0xF0 else (0x80, 0x8F) if c == 0xF4 else (0x80, 0xBF)
        else:
            return err(data_error("Utf8Leading", i, -1))
        for j in range(1, need + 1):                    # first — ошибочный октет; Truncated — начало (DATA API R07)
            if i + j >= n:
                return err(data_error("Utf8Truncated", i, -1))
            cj = b[i + j]
            if j == 1 and 0x80 <= cj <= 0xBF and not lo <= cj <= hi:
                code = "Utf8Overlong" if c in (0xE0, 0xF0) else "Utf8Surrogate" if c == 0xED else "Utf8Range"
                return err(data_error(code, i + j, -1))
            if not 0x80 <= cj <= 0xBF:
                return err(data_error("Utf8Continuation", i + j, -1))
        i += need + 1
    return ok(b.decode("utf-8"))


def json_quote(s: str) -> str:
    """Строковый литерал BAG-CJSON-1 (CANON-04)."""
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ord(ch) < 0x20:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


# ------------------------------------------------------------ std.test
def expect(label, cond):
    if not cond:
        raise Fault("TEST_ASSERTION", label=label)


def expect_equal(label, actual, expected):
    if actual != expected:
        raise Fault("TEST_ASSERTION", label=label)


def codec(*_):
    raise NotImplementedPrim("std.codec — контракт VALUE-CODEC-V1 не закрыт (BD07)")


PRIMS = {
    # операторы исходника (SURF-33…SURF-38)
    "op.add@1": lambda a, b: _trap(_checked(a + b)),
    "op.sub@1": lambda a, b: _trap(_checked(a - b)),
    "op.mul@1": lambda a, b: _trap(_checked(a * b)),
    "op.div@1": lambda a, b: _trap(i64_div(a, b)),
    "op.rem@1": lambda a, b: _trap(i64_rem(a, b)),
    "op.neg@1": lambda a: _trap(_checked(-a)),
    "op.not@1": lambda a: not a,
    "op.eq@1": lambda a, b: a == b,
    "op.ne@1": lambda a, b: a != b,
    "op.lt@1": lambda a, b: key_of(a) < key_of(b),
    "op.le@1": lambda a, b: key_of(a) <= key_of(b),
    "op.gt@1": lambda a, b: key_of(a) > key_of(b),
    "op.ge@1": lambda a, b: key_of(a) >= key_of(b),
    "op.concat_string@1": lambda a, b: a + b,
    "op.concat_bytes@1": lambda a, b: a + b,
    "op.concat_seq@1": lambda a, b: a + b,
    # std.i64
    "std.i64.eq@1": lambda a, b: a == b,
    "std.i64.lt@1": lambda a, b: a < b,
    "std.i64.add@1": lambda a, b: _checked(a + b),
    "std.i64.sub@1": lambda a, b: _checked(a - b),
    "std.i64.mul@1": lambda a, b: _checked(a * b),
    "std.i64.div@1": i64_div,
    "std.i64.rem@1": i64_rem,
    "std.i64.neg@1": lambda a: _checked(-a),
    "std.i64.parse_decimal@1": parse_decimal,
    "std.i64.format_decimal@1": lambda n: str(n),
    # std.value
    "std.value.equal@1": lambda a, b: a == b,
    "std.value.compare@1": compare,
    # std.option, std.result (без функций высшего порядка — они на bagaev)
    "std.option.is_some@1": lambda o: o.ordinal == 1,
    "std.option.value_or@1": lambda o, d: o.payload if o.ordinal == 1 else d,
    "std.result.is_ok@1": lambda r: r.ordinal == 0,
    # std.seq
    "std.seq.length@1": len,
    "std.seq.get@1": seq_get,
    "std.seq.append@1": lambda xs, x: xs + (x,),
    "std.seq.concat@1": lambda a, b: a + b,
    "std.seq.slice@1": seq_slice,
    # std.map
    "std.map.build@1": map_build,
    "std.map.get@1": map_get,
    "std.map.length@1": lambda m: len(m.d),
    "std.map.entries@1": lambda m: tuple(Rec((k, v)) for k, v in m.entries()),
    "std.map.put@1": map_put,
    "std.map.remove@1": map_remove,
    # std.string
    "std.string.scalar_length@1": len,
    "std.string.scalar_get@1": lambda s, i: some(ord(s[i])) if 0 <= i < len(s) else NONE,
    "std.string.slice@1": lambda s, a, b: bounds(len(s), a, b) or ok(s[a:b]),
    "std.string.concat@1": lambda a, b: a + b,
    "std.string.from_scalars@1": from_scalars,
    "std.string.to_scalars@1": lambda s: tuple(ord(c) for c in s),
    # std.bytes
    "std.bytes.length@1": len,
    "std.bytes.get@1": lambda b, i: some(b[i]) if 0 <= i < len(b) else NONE,
    "std.bytes.slice@1": lambda b, x, y: bounds(len(b), x, y) or ok(b[x:y]),
    "std.bytes.concat@1": lambda a, b: a + b,
    "std.bytes.from_octets@1": from_octets,
    "std.bytes.to_octets@1": lambda b: tuple(b),
    # std.utf8, std.codec, std.json
    "std.utf8.encode@1": lambda s: s.encode("utf-8"),
    "std.utf8.decode@1": utf8_decode,
    "std.codec.encode@1": codec,
    "std.codec.decode@1": codec,
    "std.json.quote@1": json_quote,
    # std.test
    "std.test.expect@1": expect,
    "std.test.expect_equal@1": expect_equal,
}
HOST_OPS = {"std.store.get", "std.store.contains", "std.store.all", "std.store.put", "std.store.remove",
            "std.store.replace_all"}
