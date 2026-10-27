"""Наблюдаемое значение (spec/kernel/canonical.md CANON-11): значение машины плюс его статический тип."""
from __future__ import annotations

from bagaev_ref.machine.values import NOPAY
from bagaev_ref.sema import types as T

BUILTIN_TAGS = {"Option": [("None", None), ("Some", 0)], "Result": [("Ok", 0), ("Err", 1)]}


def type_text(t) -> str:
    """Каноническое написание типа: аргументы через «,» без пробелов, пользовательские типы с модулем."""
    t = T.prune(t)
    if isinstance(t, T.TCon):
        if t.name == "Unit":
            return "Unit"
        return t.name + ("<" + ",".join(type_text(a) for a in t.args) + ">" if t.args else "")
    if isinstance(t, T.TNom):
        return t.info.qname + ("<" + ",".join(type_text(a) for a in t.args) + ">" if t.args else "")
    if isinstance(t, T.TFn):
        return "Fn"
    return "?"


def observe(v, t) -> dict:
    t = T.prune(t)
    name = type_text(t)
    if isinstance(t, T.TFn):
        return {"type": "Fn"}
    if isinstance(t, T.TCon):
        n = t.name
        if n == "Bool":
            return {"type": "Bool", "value": bool(v)}
        if n == "Int64":
            return {"type": "Int64", "value": str(v)}
        if n == "String":
            return {"type": "String", "value": v}
        if n == "Bytes":
            return {"type": "Bytes", "hex": v.hex()}
        if n == "Unit":
            return {"type": "Unit"}
        if n == "Seq":
            return {"type": name, "items": [observe(x, t.args[0]) for x in v]}
        if n == "Map":
            return {"type": name, "entries": [[observe(k, t.args[0]), observe(x, t.args[1])] for k, x in v.entries()]}
        if n in BUILTIN_TAGS:
            out = {"type": name, "tag": v.tag}
            idx = dict(BUILTIN_TAGS[n])[v.tag]
            if idx is not None:
                out["payload"] = observe(v.payload, t.args[idx])
            return out
        raise AssertionError(n)
    info = t.info
    m = info.mapping(t.args)
    if info.kind in ("record", "event"):
        return {"type": name, "fields": {fn: observe(x, T.subst(ft, m)) for (fn, ft), x in zip(info.fields, v.fields)}}
    if info.kind == "opaque":
        return {"type": name, "value": observe(v, T.subst(info.rep, m))}
    out = {"type": name, "tag": v.tag}
    pt = dict(info.variants)[v.tag]
    if pt is not None and v.payload is not NOPAY:
        out["payload"] = observe(v.payload, T.subst(pt, m))
    return out
