"""BAG-CJSON-1 и дайджесты (spec/kernel/canonical.md CANON-01…CANON-08) и обратное наблюдение CANON-11.

encode(obj) — канонические байты; decode(data) — строгий разбор с проверкой канонической формы (CANON-06).
"""
from __future__ import annotations

import hashlib
import json
import re

from bagaev_ref.machine.values import NOPAY, MapV, Rec, Var
from bagaev_ref.sema import types as T

KIND_RE = re.compile(r"[a-z0-9-]+")


class NonCanonical(ValueError):
    """Отказ декодера: NON_CANONICAL_JSON (CANON-06) или недопустимое значение (CANON-02…04)."""


def _string(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if 0xD800 <= o <= 0xDFFF:
            raise NonCanonical("суррогат в строке (CANON-04)")
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 0x20:
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _enc(v) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, str):
        return _string(v)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_enc(x) for x in v) + "]"
    if isinstance(v, dict):
        items = sorted(v.items(), key=lambda kv: [ord(c) for c in kv[0]])   # по scalar values (CANON-03)
        return "{" + ",".join(_string(k) + ":" + _enc(x) for k, x in items) + "}"
    raise NonCanonical(f"значение {type(v).__name__} недопустимо в BAG-CJSON-1 (CANON-02)")


def encode(obj) -> bytes:
    """CANON-01…05: UTF-8, без пробелов, ключи по scalar values, только строки вместо чисел."""
    return _enc(obj).encode("utf-8")


def decode(data: bytes):
    """CANON-06: разобрать, закодировать обратно и сравнить байты; повтор ключа и числа — отказ."""
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise NonCanonical(f"повтор ключа {k!r} (CANON-03)")
            d[k] = v
        return d

    def no_number(x):
        raise NonCanonical("число JSON (CANON-02)")
    try:
        text = data.decode("utf-8")
        obj = json.loads(text, object_pairs_hook=pairs, parse_float=no_number, parse_int=no_number,
                         parse_constant=no_number)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise NonCanonical(str(e)) from None
    if encode(obj) != data:
        raise NonCanonical("байты не совпадают с канонической формой (CANON-06)")
    return obj


def digest(kind: str, version: str, body) -> str:
    """CANON-08: SHA-256(UTF8("bagaev/" + kind + "/" + version) || 0x0A || BAG-CJSON-1(body))."""
    if not KIND_RE.fullmatch(kind) or not KIND_RE.fullmatch(version):
        raise ValueError("kind и version — ASCII [a-z0-9-]+")
    return hashlib.sha256(f"bagaev/{kind}/{version}".encode("ascii") + b"\n" + encode(body)).hexdigest()


# ------------------------------------------------------------ обратное наблюдение (CANON-11)
BUILTIN = {"Option": [("None", None), ("Some", 0)], "Result": [("Ok", 0), ("Err", 1)]}


class BadValue(ValueError):
    """Наблюдение не соответствует типу (аргумент запроса, строка таблицы)."""


def _keys(obs: dict, *want):
    """Точный набор полей объекта CANON-11: лишнее или недостающее поле — отказ."""
    if set(obs) != {"type", *want}:
        raise BadValue(f"поля {sorted(obs)} вместо {sorted({'type', *want})}"[:200])


def _text(s) -> str:
    if not isinstance(s, str) or any(0xD800 <= ord(ch) <= 0xDFFF for ch in s):
        raise BadValue("String — Unicode scalar values без суррогатов (CANON-04)")
    return s


def unobserve(obs, t, nominal: bool = True):
    """Значение машины из наблюдаемой формы CANON-11 по статическому типу t (аргументы запросов, строки таблиц).
    Строго: точный набор полей, строки без суррогатов, коллекции — списки. `nominal=False` — чтение данных
    хранилища: имя типа в записи не сверяется, только строение (привязка схемы структурная, HST-04)."""
    from bagaev_ref.machine.observe import type_text
    t = T.prune(t)
    if not isinstance(obs, dict) or not isinstance(obs.get("type"), str) or (nominal and obs["type"] != type_text(t)):
        raise BadValue(f"ожидался {type_text(t)}, получено {obs!r}"[:200])
    if isinstance(t, T.TCon):
        n = t.name
        if n == "Bool":
            _keys(obs, "value")
            if not isinstance(obs["value"], bool):
                raise BadValue("Bool")
            return obs["value"]
        if n == "Int64":
            _keys(obs, "value")
            s = obs["value"]
            if not isinstance(s, str) or not re.fullmatch(r"-?(0|[1-9][0-9]*)", s) or s == "-0":
                raise BadValue("Int64 — десятичная строка (CANON-07)")
            v = int(s)
            if not -2**63 <= v < 2**63:
                raise BadValue("Int64 вне диапазона")
            return v
        if n == "String":
            _keys(obs, "value")
            return _text(obs["value"])
        if n == "Bytes":
            _keys(obs, "hex")
            h = obs["hex"]
            if not isinstance(h, str) or not re.fullmatch(r"([0-9a-f]{2})*", h):
                raise BadValue("Bytes — строчные hex-цифры")
            return bytes.fromhex(h)
        if n == "Unit":
            _keys(obs)
            return None
        if n == "Seq":
            _keys(obs, "items")
            if not isinstance(obs["items"], list):
                raise BadValue("Seq — список items")
            return tuple(unobserve(x, t.args[0], nominal) for x in obs["items"])
        if n == "Map":
            _keys(obs, "entries")
            if not isinstance(obs["entries"], list):
                raise BadValue("Map — список entries")
            d = {}
            for e in obs["entries"]:
                if not isinstance(e, list) or len(e) != 2:
                    raise BadValue("запись карты — пара [ключ, значение]")
                kk = unobserve(e[0], t.args[0], nominal)
                if kk in d:
                    raise BadValue("повтор ключа карты")
                d[kk] = unobserve(e[1], t.args[1], nominal)
            return MapV(d)
        if n in BUILTIN:
            tags = [x for x, _ in BUILTIN[n]]
            tag = obs.get("tag")
            if tag not in tags:
                raise BadValue(f"тег {tag!r}")
            idx = dict(BUILTIN[n])[tag]
            _keys(obs, "tag", *(() if idx is None else ("payload",)))
            return Var(tags.index(tag), tag, NOPAY if idx is None else unobserve(obs["payload"], t.args[idx], nominal))
        raise BadValue(f"тип {n} не наблюдается как данные")
    if isinstance(t, T.TNom):
        info, m = t.info, t.info.mapping(t.args)
        if info.kind in ("record", "event"):
            _keys(obs, "fields")
            fields = obs["fields"]
            if not isinstance(fields, dict) or set(fields) != {f for f, _ in info.fields}:
                raise BadValue(f"поля {sorted(fields) if isinstance(fields, dict) else fields!r}"[:200])
            return Rec(tuple(unobserve(fields[f], T.subst(ft, m), nominal) for f, ft in info.fields))
        if info.kind == "opaque":
            _keys(obs, "value")
            return unobserve(obs["value"], T.subst(info.rep, m), nominal)
        tags = [x for x, _ in info.variants]
        tag = obs.get("tag")
        if tag not in tags:
            raise BadValue(f"тег {tag!r}")
        pt = dict(info.variants)[tag]
        _keys(obs, "tag", *(() if pt is None else ("payload",)))
        return Var(tags.index(tag), tag, NOPAY if pt is None else unobserve(obs["payload"], T.subst(pt, m), nominal))
    raise BadValue("функция не является данными")
