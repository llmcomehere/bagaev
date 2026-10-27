"""DATA-0.1: bounded typed ready-value jobs with lazy reference work.

No source expression evaluation, host effects, database, or frozen CORE import.
The input checker is separate from the charged work machine.  Wire and compare
results are computed by the work cursor, never by a precomputed answer/trace.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
from types import MappingProxyType
import json

PROFILE_REVISION = "data-core/r07-v1"
CODEC_REVISION = "data-wire/r07-v1"
MAGIC = b"BD07\x01"
MIN_INT, MAX_INT = -(2**63), 2**63 - 1
MAX_RAW_NODES, MAX_RAW_DEPTH = 65536, 128
MAX_SCHEMAS, MAX_MEMBERS, MAX_PARAMETERS = 64, 64, 8
MAX_TYPE_DEPTH, MAX_TYPE_WORK = 32, 8192
MAX_VALUE_DEPTH, MAX_VALUE_NODES = 32, 4096
MAX_STRING, MAX_BYTES, MAX_ITEMS = 1024, 32768, 256
MAX_OUTPUT, MAX_WORK, MAX_BUDGET = 32768, 4096, 262144
PREDICATES = ("Eq", "Key", "Persistable")
SCALARS = ("Bool", "Int64", "Unit", "String", "Bytes", "DataError", "Capability", "HostHandle")
ERROR_CODES = ("DuplicateKey", "Utf8Leading", "Utf8Continuation", "Utf8Overlong",
               "Utf8Surrogate", "Utf8Range", "Utf8Truncated", "UnexpectedEnd",
               "ContextMismatch", "InvalidEncoding", "UnknownVariant",
               "NonCanonicalMap", "TrailingBytes")
OP_FIELDS = {
    "record": ("type", "fields"), "variant": ("type", "tag", "value"),
    "sequence": ("item_type", "items"), "map_build": ("key_type", "value_type", "entries"),
    "field": ("record", "field"), "equal": ("left", "right"), "compare": ("left", "right"),
    "length": ("value",), "seq_get": ("sequence", "index"), "seq_append": ("sequence", "value"),
    "map_get": ("map", "key"), "utf8_encode": ("value",), "utf8_decode": ("value",),
    "encode": ("value",), "decode": ("type", "bytes"),
}
OP_IDS = ("record", "variant", "sequence", "map_build", "field", "equal", "compare", "length",
          "seq_get", "seq_append", "map_get", "utf8_encode", "utf8_decode", "encode", "decode")
RULE_IDS = ("JOB_START", "JOB_FINISH", "RECORD_FIELD", "VARIANT_WRAP", "SEQUENCE_ITEM",
            "FIELD_SELECT", "LENGTH_ITEM", "SEQ_GET", "SEQUENCE_APPEND", "COMPARE_NODE",
            "COMPARE_UNIT", "COMPARE_END", "COMPARE_NEXT", "MAP_STAGE", "MAP_PROBE", "MAP_DECIDE",
            "MAP_COPY", "MAP_ADD", "MAP_COMMIT", "MAP_LOOKUP", "MAP_LOOKUP_DECIDE", "MAP_LOOKUP_END",
            "UTF8_SCALAR", "UTF8_WRITE", "UTF8_READ", "UTF8_END", "ENCODE_WRITE", "ENCODE_NODE",
            "ENCODE_NEXT", "ENCODE_SCAN", "ENCODE_SCALAR", "DECODE_READ", "DECODE_NODE",
            "DECODE_NEXT", "DECODE_SCALAR", "DECODE_LENGTH", "DECODE_TAG", "DECODE_ASSEMBLE",
            "DECODE_MAP_ORDER", "DECODE_END")
LIMITS = {"raw_nodes": 65536, "raw_depth": 128, "schemas": 64, "members": 64, "parameters": 8,
          "type_depth": 32, "type_work": 8192, "value_depth": 32, "value_nodes": 4096,
          "string_scalars": 1024, "bytes": 32768, "items": 256, "output": 32768,
          "work_frames": 4096, "budget": 262144, "identifier_scalars": 128}


class DataCoreError(ValueError):
    def __init__(self, code, path=(), detail="", kind="PrelaunchDiagnostic"):
        self.code, self.path, self.detail, self.kind = code, tuple(path), detail, kind
        super().__init__(code + (": " + detail if detail else ""))


def _limit(condition, path=(), detail=""):
    if not condition:
        raise DataCoreError("PROFILE_LIMIT", path, detail, "UnsupportedInputProfile")


def _id(value, path=()):
    if type(value) is not str or not value:
        raise DataCoreError("INVALID_ID", path)
    if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise DataCoreError("INVALID_UNICODE_SCALAR", path)
    _limit(len(value) <= 128, path, "identifier length")
    return value


def _shape(value, keys, path=()):
    if not isinstance(value, Mapping):
        raise DataCoreError("INVALID_SHAPE", path, "object required")
    expected = set(keys)
    for key in value:
        if key not in expected:
            raise DataCoreError("UNKNOWN_FIELD", path + (key,))
    for key in keys:
        if key not in value:
            raise DataCoreError("MISSING_FIELD", path + (key,))


def _array(value, path=(), maximum=None):
    if not isinstance(value, (tuple, list)):
        raise DataCoreError("INVALID_SHAPE", path, "array required")
    if maximum is not None:
        _limit(len(value) <= maximum, path, "array size")
    return value


def _freeze(value, path=(), depth=0, counter=None):
    counter = [0] if counter is None else counter
    counter[0] += 1
    _limit(depth <= MAX_RAW_DEPTH and counter[0] <= MAX_RAW_NODES, path, "raw JSON size/depth")
    if isinstance(value, Mapping):
        out = {}
        for key, child in value.items():
            if type(key) is not str:
                raise DataCoreError("INVALID_SHAPE", path, "non-string key")
            if any(0xD800 <= ord(c) <= 0xDFFF for c in key):
                raise DataCoreError("INVALID_UNICODE_SCALAR", path)
            out[key] = _freeze(child, path + (key,), depth + 1, counter)
        return MappingProxyType(out)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(child, path + (i,), depth + 1, counter) for i, child in enumerate(value))
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if not MIN_INT <= value <= MAX_INT:
            raise DataCoreError("INVALID_LITERAL", path, "integer outside Int64")
        return value
    if type(value) is str:
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise DataCoreError("INVALID_UNICODE_SCALAR", path)
        _limit(len(value) <= MAX_STRING, path, "raw string length")
        return value
    raise DataCoreError("INVALID_SHAPE", path, "not an in-process JSON value")


@dataclass(frozen=True)
class Type:
    tag: str
    args: tuple = ()
    ident: str = ""
    revision: str = ""


BOOL, INT, UNIT, STRING, BYTES, ERROR = (Type(name) for name in ("Bool", "Int64", "Unit", "String", "Bytes", "DataError"))


def type_json(t):
    if t.tag in SCALARS:
        return t.tag
    if t.tag == "var":
        return {"tag": "var", "id": t.ident}
    if t.tag == "fn":
        return {"tag": "fn", "params": [type_json(a) for a in t.args[:-1]], "result": type_json(t.args[-1])}
    if t.tag in ("seq", "option"):
        return {"tag": t.tag, "item": type_json(t.args[0])}
    if t.tag == "map":
        return {"tag": "map", "key": type_json(t.args[0]), "value": type_json(t.args[1])}
    if t.tag == "result":
        return {"tag": "result", "ok": type_json(t.args[0]), "err": type_json(t.args[1])}
    if t.tag == "nominal":
        return {"tag": "nominal", "id": t.ident, "revision": t.revision, "args": [type_json(a) for a in t.args]}
    raise DataCoreError("INVALID_TYPE")


@dataclass(frozen=True)
class Value:
    type: Type
    kind: str
    data: object
    nodes: int = 1
    depth: int = 0


def _children(v):
    if v.kind == "seq":
        return v.data
    if v.kind == "record":
        return tuple(child for _, child in v.data)
    if v.kind == "sum":
        return (v.data[2],)
    if v.kind == "map":
        return tuple(child for pair in v.data for child in pair)
    return ()


def _make(t, kind, data):
    provisional = Value(t, kind, data)
    children = _children(provisional)
    return Value(t, kind, data, 1 + sum(v.nodes for v in children),
                 1 + max(v.depth for v in children) if children else 0)


def _payload_json(v):
    if v.kind == "record":
        return {key: _payload_json(child) for key, child in v.data}
    if v.kind == "sum":
        return {"tag": v.data[0], "value": _payload_json(v.data[2])}
    if v.kind == "seq":
        return [_payload_json(child) for child in v.data]
    if v.kind == "map":
        return [{"key": _payload_json(k), "value": _payload_json(val)} for k, val in v.data]
    if v.kind == "Bytes":
        return list(v.data)
    return v.data


def value_json(v):
    return {"type": type_json(v.type), "data": _payload_json(v)}


@dataclass(frozen=True)
class Job:
    source_id: str
    revision: str
    schemas: object
    operation: object
    profile_revision: str = PROFILE_REVISION

    def __post_init__(self):
        _id(self.source_id, ("source_id",)); _id(self.revision, ("revision",))
        _id(self.profile_revision, ("profile_revision",))
        frozen = _freeze({"source_id": self.source_id, "revision": self.revision,
                          "schemas": self.schemas, "operation": self.operation,
                          "profile_revision": self.profile_revision})
        object.__setattr__(self, "schemas", frozen["schemas"])
        object.__setattr__(self, "operation", frozen["operation"])


def canonical(value):
    if isinstance(value, Job):
        return {"source_id": value.source_id, "revision": value.revision,
                "schemas": canonical(value.schemas), "operation": canonical(value.operation),
                "profile_revision": value.profile_revision}
    if isinstance(value, Type):
        return type_json(value)
    if isinstance(value, Value):
        return value_json(value)
    if isinstance(value, Mapping):
        return {key: canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    if value is None or type(value) in (str, bool, int):
        return value
    raise DataCoreError("INVALID_SHAPE", detail="not canonical JSON")


def digest(value):
    return sha256(json.dumps(canonical(value), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def decode_job(raw):
    _shape(raw, ("source_id", "revision", "schemas", "operation", "profile_revision"))
    return Job(**raw)


def _subst(t, bindings):
    if t.tag == "var":
        return bindings.get(t.ident, t)
    return Type(t.tag, tuple(_subst(a, bindings) for a in t.args), t.ident, t.revision)


def _type_limit(t):
    pending = [(t, 0)]; count = 0
    while pending:
        current, depth = pending.pop(); count += 1
        _limit(depth <= MAX_TYPE_DEPTH and count <= MAX_TYPE_WORK, detail="instantiated/result type metadata")
        pending.extend((child, depth + 1) for child in current.args)


def raw_node_count(value):
    pending = [value]; count = 0
    while pending:
        current = pending.pop(); count += 1
        if isinstance(current, Mapping): pending.extend(current.values())
        elif isinstance(current, (tuple, list)): pending.extend(current)
    return count


@dataclass(frozen=True)
class Schema:
    ident: str
    revision: str
    kind: str
    parameters: tuple
    members: tuple
    codec: object


class Registry:
    """Immutable declarations; memo tables are local checked metadata only."""
    def __init__(self, schemas):
        self.raw = _freeze(schemas)
        _array(self.raw, ("schemas",), MAX_SCHEMAS)
        raw_by_ref = {}; all_parameters = set(); bounds_by_ref = {}
        for i, raw in enumerate(self.raw):
            path = ("schemas", i)
            if not isinstance(raw, Mapping) or raw.get("kind") not in ("record", "sum"):
                raise DataCoreError("INVALID_SHAPE", path, "schema kind")
            member_key = "fields" if raw["kind"] == "record" else "variants"
            _shape(raw, ("id", "revision", "kind", "type_params", "codec", member_key), path)
            ref = (_id(raw["id"], path + ("id",)), _id(raw["revision"], path + ("revision",)))
            if ref in raw_by_ref:
                raise DataCoreError("DUPLICATE_SCHEMA", path)
            raw_by_ref[ref] = raw
            if raw["codec"] not in (None, CODEC_REVISION):
                raise DataCoreError("UNSUPPORTED_CODEC", path + ("codec",))
            params = []
            for j, param in enumerate(_array(raw["type_params"], path + ("type_params",), MAX_PARAMETERS)):
                p = path + ("type_params", j); _shape(param, ("id", "bounds"), p)
                identifier = _id(param["id"], p + ("id",))
                if identifier in all_parameters:
                    raise DataCoreError("DUPLICATE_TYPE_PARAMETER", p)
                all_parameters.add(identifier)
                bounds = _array(param["bounds"], p + ("bounds",), 3)
                if any(type(b) is not str or b not in PREDICATES for b in bounds) or len(set(bounds)) != len(bounds):
                    raise DataCoreError("INVALID_TYPE", p, "predicate bounds")
                params.append((identifier, tuple(bounds)))
            bounds_by_ref[ref] = tuple(params)
        self._raw_by_ref = MappingProxyType(raw_by_ref)
        self._bounds_by_ref = MappingProxyType(bounds_by_ref)
        self._parse_work = 0; self._predicate_work = 0
        self._predicates = {}; self._layouts = {}; definitions = {}
        for i, raw in enumerate(self.raw):
            path = ("schemas", i); ref = (raw["id"], raw["revision"])
            params = dict(bounds_by_ref[ref]); member_key = "fields" if raw["kind"] == "record" else "variants"
            members = []; names = set()
            for j, row in enumerate(_array(raw[member_key], path + (member_key,), MAX_MEMBERS)):
                p = path + (member_key, j); _shape(row, ("id", "type"), p)
                name = _id(row["id"], p + ("id",))
                if name in names:
                    raise DataCoreError("DUPLICATE_FIELD" if raw["kind"] == "record" else "DUPLICATE_TAG", p)
                names.add(name); members.append((name, self.parse(row["type"], params, p + ("type",))))
            if raw["kind"] == "sum" and not members:
                raise DataCoreError("INVALID_TYPE", path, "empty sum")
            definitions[ref] = Schema(*ref, raw["kind"], bounds_by_ref[ref], tuple(members), raw["codec"])
        self.definitions = MappingProxyType(definitions)
        graph = {ref: set() for ref in definitions}
        for ref, definition in definitions.items():
            pending = [t for _, t in definition.members]
            while pending:
                t = pending.pop()
                if t.tag == "nominal": graph[ref].add((t.ident, t.revision))
                pending.extend(t.args)
        active = set(); done = set()
        def visit(ref):
            if ref in active:
                raise DataCoreError("PENDING_RECURSIVE_DATA", ("schemas",), str(ref))
            if ref in done: return
            active.add(ref)
            for target in sorted(graph[ref]): visit(target)
            active.remove(ref); done.add(ref)
        for ref in definitions: visit(ref)
        for definition in definitions.values():
            environment = dict(definition.parameters)
            for _, t in definition.members: self.check_type(t, environment)
        self.content_digest = digest({"profile_revision": PROFILE_REVISION, "codec_revision": CODEC_REVISION,
                                      "schemas": canonical(self.raw)})

    def parse(self, raw, parameters=None, path=(), depth=0):
        parameters = {} if parameters is None else parameters
        self._parse_work += 1
        _limit(depth <= MAX_TYPE_DEPTH and self._parse_work <= MAX_TYPE_WORK, path, "type metadata work/depth")
        if type(raw) is str:
            if raw not in SCALARS: raise DataCoreError("INVALID_TYPE", path)
            return Type(raw)
        if not isinstance(raw, Mapping): raise DataCoreError("INVALID_TYPE", path)
        tag = raw.get("tag")
        if tag == "var":
            _shape(raw, ("tag", "id"), path); identifier = _id(raw["id"], path + ("id",))
            if identifier not in parameters: raise DataCoreError("UNBOUND_TYPE_VARIABLE", path)
            return Type("var", ident=identifier)
        fields = {"fn": ("params", "result"), "seq": ("item",), "option": ("item",),
                  "map": ("key", "value"), "result": ("ok", "err"),
                  "nominal": ("id", "revision", "args")}
        if type(tag) is not str or tag not in fields: raise DataCoreError("INVALID_TYPE", path)
        _shape(raw, ("tag",) + fields[tag], path)
        if tag == "fn":
            arguments = [self.parse(a, parameters, path + ("params", i), depth + 1)
                         for i, a in enumerate(_array(raw["params"], path + ("params",), MAX_MEMBERS))]
            arguments.append(self.parse(raw["result"], parameters, path + ("result",), depth + 1))
            return Type(tag, tuple(arguments))
        if tag == "nominal":
            ref = (_id(raw["id"], path + ("id",)), _id(raw["revision"], path + ("revision",)))
            if ref not in self._raw_by_ref: raise DataCoreError("UNKNOWN_TYPE", path)
            arguments = _array(raw["args"], path + ("args",), MAX_PARAMETERS)
            if len(arguments) != len(self._bounds_by_ref[ref]): raise DataCoreError("TYPE_ARGUMENT_ARITY", path)
            return Type(tag, tuple(self.parse(a, parameters, path + ("args", i), depth + 1)
                                   for i, a in enumerate(arguments)), *ref)
        return Type(tag, tuple(self.parse(raw[key], parameters, path + (key,), depth + 1) for key in fields[tag]))

    def ground(self, raw, path=()):
        t = self.parse(raw, {}, path); self.check_type(t, {})
        return t

    def check_type(self, t, bounds):
        for a in t.args: self.check_type(a, bounds)
        if t.tag == "map" and not self.predicate("Key", t.args[0], bounds):
            raise DataCoreError("KEY_REQUIRED", detail="Map key")
        if t.tag == "nominal":
            definition = self.definitions[(t.ident, t.revision)]
            for (_, required), actual in zip(definition.parameters, t.args):
                for name in required:
                    if not self.predicate(name, actual, bounds):
                        raise DataCoreError("BOUND_NOT_SATISFIED", detail=name)

    def layout(self, t):
        if t in self._layouts: return self._layouts[t]
        if t == ERROR:
            result = ("record", (("code", STRING), ("first", INT), ("second", INT)))
        elif t.tag == "option": result = ("sum", (("None", UNIT), ("Some", t.args[0])))
        elif t.tag == "result": result = ("sum", (("Ok", t.args[0]), ("Err", t.args[1])))
        elif t.tag == "nominal":
            definition = self.definitions[(t.ident, t.revision)]
            substitution = {name: a for (name, _), a in zip(definition.parameters, t.args)}
            members = tuple((name, _subst(a, substitution)) for name, a in definition.members)
            for _, child in members: _type_limit(child)
            result = (definition.kind, members)
        else: result = (t.tag, ())
        self._layouts[t] = result
        return result

    def predicate(self, name, t, bounds=None):
        bounds = {} if bounds is None else bounds
        environment = tuple(sorted(bounds.items())); root = (name, t, environment)
        pending = [(name, t, None)]
        while pending:
            pred, current, dependencies = pending.pop(); key = (pred, current, environment)
            if key in self._predicates: continue
            if dependencies is not None:
                self._predicates[key] = all(self._predicates[(p, child, environment)] for p, child in dependencies)
                continue
            self._predicate_work += 1
            _limit(self._predicate_work <= MAX_TYPE_WORK, detail="predicate work")
            if current.tag == "var":
                declared = bounds.get(current.ident, ())
                self._predicates[key] = pred in declared or pred == "Eq" and "Key" in declared
            elif current.tag in ("fn", "Capability", "HostHandle"):
                self._predicates[key] = False
            elif current.tag in SCALARS:
                self._predicates[key] = True
            elif current.tag == "map" and pred == "Key":
                self._predicates[key] = False
            elif pred == "Persistable" and current.tag == "nominal" and self.definitions[(current.ident, current.revision)].codec is None:
                self._predicates[key] = False
            else:
                if current.tag == "seq": dependencies = ((pred, current.args[0]),)
                elif current.tag == "map":
                    dependencies = (("Key", current.args[0]), (pred, current.args[1]))
                    if pred == "Persistable": dependencies += ((pred, current.args[0]),)
                else: dependencies = tuple((pred, child) for _, child in self.layout(current)[1])
                pending.append((pred, current, dependencies))
                pending.extend((p, child, None) for p, child in reversed(dependencies)
                               if (p, child, environment) not in self._predicates)
        return self._predicates[root]


def predicate(schemas, type_json, name):
    if name not in PREDICATES: raise DataCoreError("UNKNOWN_PREDICATE")
    registry = Registry(schemas); t = registry.ground(_freeze(type_json))
    return registry.predicate(name, t)


def _sign(a, b):
    return (a > b) - (a < b)


def _checked_input_compare(a, b):
    """Prelaunch validation of ready canonical maps; never the runtime op."""
    if a.kind in ("Bool", "Int64", "Unit"):
        return 0 if a.kind == "Unit" else _sign(a.data, b.data)
    if a.kind in ("String", "Bytes"): return _sign(a.data, b.data)
    if a.kind == "sum":
        different = _sign(a.data[1], b.data[1])
        return different or _checked_input_compare(a.data[2], b.data[2])
    left, right = _children(a), _children(b)
    for x, y in zip(left, right):
        different = _checked_input_compare(x, y)
        if different: return different
    return _sign(len(left), len(right))


def _input_value(registry, t, raw, path=(), depth=0, counter=None):
    counter = [0] if counter is None else counter
    counter[0] += 1
    _limit(depth <= MAX_VALUE_DEPTH and counter[0] <= MAX_VALUE_NODES, path, "value nodes/depth")
    if t.tag == "Bool":
        if type(raw) is not bool: raise DataCoreError("INVALID_LITERAL", path)
        v = _make(t, "Bool", raw)
    elif t.tag == "Int64":
        if type(raw) is not int or not MIN_INT <= raw <= MAX_INT: raise DataCoreError("INVALID_LITERAL", path)
        v = _make(t, "Int64", raw)
    elif t.tag == "Unit":
        if raw is not None: raise DataCoreError("INVALID_LITERAL", path)
        v = _make(t, "Unit", None)
    elif t.tag == "String":
        if type(raw) is not str: raise DataCoreError("INVALID_LITERAL", path)
        if any(0xD800 <= ord(c) <= 0xDFFF for c in raw): raise DataCoreError("INVALID_UNICODE_SCALAR", path)
        _limit(len(raw) <= MAX_STRING, path, "String scalars"); v = _make(t, "String", raw)
    elif t.tag == "Bytes":
        _array(raw, path, MAX_BYTES)
        if any(type(b) is not int or not 0 <= b <= 255 for b in raw): raise DataCoreError("INVALID_LITERAL", path)
        v = _make(t, "Bytes", tuple(raw))
    elif t.tag in ("fn", "Capability", "HostHandle", "var"):
        raise DataCoreError("UNSUPPORTED_VALUE_TYPE", path)
    elif t.tag == "seq":
        children = tuple(_input_value(registry, t.args[0], child, path + (i,), depth + 1, counter)
                         for i, child in enumerate(_array(raw, path, MAX_ITEMS)))
        v = _make(t, "seq", children)
    elif t.tag == "map":
        rows = []
        for i, row in enumerate(_array(raw, path, MAX_ITEMS)):
            p = path + (i,); _shape(row, ("key", "value"), p)
            k = _input_value(registry, t.args[0], row["key"], p + ("key",), depth + 1, counter)
            val = _input_value(registry, t.args[1], row["value"], p + ("value",), depth + 1, counter)
            if rows and _checked_input_compare(rows[-1][0], k) >= 0:
                raise DataCoreError("NON_CANONICAL_MAP_INPUT", p)
            rows.append((k, val))
        v = _make(t, "map", tuple(rows))
    else:
        kind, members = registry.layout(t)
        if kind == "record":
            _shape(raw, tuple(name for name, _ in members), path)
            data = tuple((name, _input_value(registry, child, raw[name], path + (name,), depth + 1, counter))
                         for name, child in members)
            v = _make(t, kind, data)
            if t == ERROR and raw["code"] not in ERROR_CODES: raise DataCoreError("INVALID_LITERAL", path + ("code",))
        else:
            _shape(raw, ("tag", "value"), path)
            names = [name for name, _ in members]
            if type(raw["tag"]) is not str or raw["tag"] not in names: raise DataCoreError("UNKNOWN_TAG", path + ("tag",))
            ordinal = names.index(raw["tag"])
            child = _input_value(registry, members[ordinal][1], raw["value"], path + ("value",), depth + 1, counter)
            v = _make(t, "sum", (raw["tag"], ordinal, child))
    _limit(v.nodes <= MAX_VALUE_NODES and v.depth <= MAX_VALUE_DEPTH, path, "value nodes/depth")
    return v


@dataclass(frozen=True)
class Prepared:
    job: Job
    registry: Registry
    operation: Mapping
    result_type: Type
    content_digest: str


def prepare(job):
    if not isinstance(job, Job): raise DataCoreError("INVALID_SHAPE", detail="Job required")
    if job.profile_revision != PROFILE_REVISION: raise DataCoreError("UNSUPPORTED_PROFILE")
    registry = Registry(job.schemas); raw = job.operation; path = ("operation",)
    if not isinstance(raw, Mapping) or type(raw.get("op")) is not str or raw.get("op") not in OP_FIELDS:
        raise DataCoreError("UNKNOWN_OPERATION", path)
    op = raw["op"]; _shape(raw, ("op",) + OP_FIELDS[op], path); checked = {"op": op}
    def operand(value, p):
        _shape(value, ("type", "data"), p)
        t = registry.ground(value["type"], p + ("type",))
        return _input_value(registry, t, value["data"], p + ("data",))
    def same(actual, expected, p=path):
        if actual != expected: raise DataCoreError("TYPE_MISMATCH", p)
    def need(name, t):
        if not registry.predicate(name, t):
            raise DataCoreError({"Eq": "EQ_REQUIRED", "Key": "KEY_REQUIRED", "Persistable": "NOT_PERSISTABLE"}[name], path)
    if op == "record":
        t = registry.ground(raw["type"], path + ("type",))
        if t.tag != "nominal" or registry.layout(t)[0] != "record": raise DataCoreError("TYPE_MISMATCH", path)
        members = dict(registry.layout(t)[1]); supplied = set(); fields = []
        for i, row in enumerate(_array(raw["fields"], path + ("fields",), MAX_ITEMS)):
            p = path + ("fields", i); _shape(row, ("id", "value"), p); name = _id(row["id"], p + ("id",))
            if name in supplied: raise DataCoreError("DUPLICATE_FIELD", p)
            if name not in members: raise DataCoreError("UNKNOWN_FIELD", p)
            supplied.add(name); v = operand(row["value"], p + ("value",)); same(v.type, members[name], p)
            fields.append((name, v))
        if supplied != set(members): raise DataCoreError("MISSING_FIELD", path + ("fields",))
        checked.update(type=t, fields=tuple(fields)); result = t
    elif op == "variant":
        t = registry.ground(raw["type"], path + ("type",)); kind, members = registry.layout(t)
        if kind != "sum": raise DataCoreError("TYPE_MISMATCH", path)
        names = [name for name, _ in members]
        if type(raw["tag"]) is not str or raw["tag"] not in names: raise DataCoreError("UNKNOWN_TAG", path + ("tag",))
        ordinal = names.index(raw["tag"]); v = operand(raw["value"], path + ("value",)); same(v.type, members[ordinal][1])
        checked.update(type=t, tag=raw["tag"], ordinal=ordinal, value=v); result = t
    elif op == "sequence":
        t = registry.ground(raw["item_type"], path + ("item_type",)); items = []
        for i, raw_value in enumerate(_array(raw["items"], path + ("items",), MAX_ITEMS)):
            v = operand(raw_value, path + ("items", i)); same(v.type, t); items.append(v)
        result = Type("seq", (t,)); checked.update(items=tuple(items), type=result)
    elif op == "map_build":
        k = registry.ground(raw["key_type"], path + ("key_type",)); vtype = registry.ground(raw["value_type"], path + ("value_type",)); need("Key", k)
        pairs = []
        for i, row in enumerate(_array(raw["entries"], path + ("entries",), MAX_ITEMS)):
            p = path + ("entries", i); _shape(row, ("key", "value"), p)
            key = operand(row["key"], p + ("key",)); val = operand(row["value"], p + ("value",))
            same(key.type, k, p); same(val.type, vtype, p); pairs.append((key, val, i))
        t = Type("map", (k, vtype)); result = Type("result", (t, ERROR)); checked.update(type=t, entries=tuple(pairs))
    elif op in ("equal", "compare"):
        left = operand(raw["left"], path + ("left",)); right = operand(raw["right"], path + ("right",)); same(left.type, right.type)
        need("Eq" if op == "equal" else "Key", left.type)
        checked.update(left=left, right=right); result = BOOL if op == "equal" else INT
    elif op == "field":
        v = operand(raw["record"], path + ("record",)); field = _id(raw["field"], path + ("field",))
        if v.type.tag != "nominal" or v.kind != "record": raise DataCoreError("TYPE_MISMATCH", path)
        fields = dict(v.data)
        if field not in fields: raise DataCoreError("UNKNOWN_FIELD", path + ("field",))
        checked.update(record=v, field=field); result = fields[field].type
    elif op in ("length", "utf8_encode", "utf8_decode", "encode"):
        v = operand(raw["value"], path + ("value",)); checked["value"] = v
        if op == "length":
            if v.kind not in ("String", "Bytes", "seq", "map"): raise DataCoreError("TYPE_MISMATCH", path)
            result = INT
        elif op == "utf8_encode": same(v.type, STRING); result = BYTES
        elif op == "utf8_decode": same(v.type, BYTES); result = Type("result", (STRING, ERROR))
        else:
            need("Persistable", v.type); result = BYTES
            _limit(v.nodes < MAX_VALUE_NODES and v.depth < MAX_VALUE_DEPTH, path, "decode Ok value headroom")
            _type_limit(Type("result", (v.type, ERROR)))
            prospective = {"source_id": job.source_id, "revision": job.revision,
                           "schemas": canonical(job.schemas), "profile_revision": PROFILE_REVISION,
                           "operation": {"op": "decode", "type": type_json(v.type),
                                         "bytes": {"type": "Bytes", "data": []}}}
            _freeze(prospective)
            # The extra Bytes operand is present in the prospective decoder.
            registry.ground("Bytes")
            checked["wire_limit"] = min(MAX_OUTPUT, MAX_RAW_NODES - raw_node_count(prospective))
    elif op in ("seq_get", "seq_append"):
        seq = operand(raw["sequence"], path + ("sequence",))
        if seq.type.tag != "seq": raise DataCoreError("TYPE_MISMATCH", path)
        key = "index" if op == "seq_get" else "value"; v = operand(raw[key], path + (key,))
        same(v.type, INT if op == "seq_get" else seq.type.args[0]); checked.update(sequence=seq); checked[key] = v
        result = Type("option", (seq.type.args[0],)) if op == "seq_get" else seq.type
    elif op == "map_get":
        m = operand(raw["map"], path + ("map",)); key = operand(raw["key"], path + ("key",))
        if m.type.tag != "map": raise DataCoreError("TYPE_MISMATCH", path)
        same(key.type, m.type.args[0]); checked.update(map=m, key=key); result = Type("option", (m.type.args[1],))
    else:
        t = registry.ground(raw["type"], path + ("type",)); need("Persistable", t)
        v = operand(raw["bytes"], path + ("bytes",)); same(v.type, BYTES)
        checked.update(type=t, bytes=v); result = Type("result", (t, ERROR))
    _type_limit(result)
    stamp = digest({"profile_revision": PROFILE_REVISION, "codec_revision": CODEC_REVISION, "job": canonical(job)})
    return Prepared(job, registry, MappingProxyType(checked), result, stamp)


@dataclass(frozen=True)
class TraceEntry:
    step_index: int
    rule: str
    path: tuple


@dataclass(frozen=True, eq=False)
class _Link:
    item: object
    previous: object = None


def _linked_tuple(link):
    out = []
    while link is not None:
        out.append(link.item); link = link.previous
    out.reverse()
    return tuple(out)


@dataclass(frozen=True)
class _Task:
    rule: str
    path: tuple = ()
    data: tuple = ()


@dataclass(frozen=True)
class Machine:
    prepared: Prepared
    work: tuple
    results: tuple
    output: object
    output_size: int
    position: int
    decoded_nodes: int
    steps: int
    remaining: int
    trace: object
    cancel_at: object
    cancel_request_id: str
    termination: object = None
    code: object = None
    answer: object = None


@dataclass(frozen=True)
class Execution:
    profile_revision: str
    codec_revision: str
    content_digest: str
    registry_digest: str
    termination: str
    code: str
    value: object
    steps: int
    remaining: int
    trace: tuple
    cancel_request_id: object


class _PhysicalStop(Exception):
    def __init__(self, code): self.code = code


class _DataFailure(Exception):
    def __init__(self, code, first, second=-1):
        self.code, self.first, self.second = code, first, second


def _runtime_value(t, kind, data):
    # Child metadata is already established; no deep semantic traversal here.
    provisional = Value(t, kind, data); children = _children(provisional)
    nodes = 1 + sum(v.nodes for v in children)
    depth = 1 + max(v.depth for v in children) if children else 0
    if nodes > MAX_VALUE_NODES or depth > MAX_VALUE_DEPTH:
        raise _PhysicalStop("VALUE_LIMIT")
    if kind == "String" and len(data) > MAX_STRING or kind == "Bytes" and len(data) > MAX_BYTES:
        raise _PhysicalStop("VALUE_LIMIT")
    if kind in ("seq", "map") and len(data) > MAX_ITEMS:
        raise _PhysicalStop("VALUE_LIMIT")
    return Value(t, kind, data, nodes, depth)


def _wrapped(t, tag, ordinal, child):
    return _runtime_value(t, "sum", (tag, ordinal, child))


def _error_result(result_type, failure):
    value = _runtime_value(ERROR, "record", (
        ("code", _runtime_value(STRING, "String", failure.code)),
        ("first", _runtime_value(INT, "Int64", failure.first)),
        ("second", _runtime_value(INT, "Int64", failure.second)),
    ))
    return _wrapped(result_type, "Err", 1, value)


def _utf8_octets(c):
    n = ord(c)
    if n < 0x80: return (n,)
    if n < 0x800: return (0xC0 | n >> 6, 0x80 | n & 63)
    if n < 0x10000: return (0xE0 | n >> 12, 0x80 | (n >> 6) & 63, 0x80 | n & 63)
    return (0xF0 | n >> 18, 0x80 | (n >> 12) & 63, 0x80 | (n >> 6) & 63, 0x80 | n & 63)


# UTF-8 cursor: (remaining continuation bytes, accumulator, start, lead, seen).
_UTF8_EMPTY = (0, 0, -1, 0, 0)


def _utf8_feed(state, byte, offset):
    remaining, accumulator, start, lead, seen = state
    if remaining == 0:
        if byte < 0x80: return _UTF8_EMPTY, chr(byte)
        if 0xC2 <= byte <= 0xDF: return (1, byte & 31, offset, byte, 0), None
        if 0xE0 <= byte <= 0xEF: return (2, byte & 15, offset, byte, 0), None
        if 0xF0 <= byte <= 0xF4: return (3, byte & 7, offset, byte, 0), None
        raise _DataFailure("Utf8Leading", offset)
    if not 0x80 <= byte <= 0xBF: raise _DataFailure("Utf8Continuation", offset)
    if seen == 0:
        if lead == 0xE0 and byte < 0xA0 or lead == 0xF0 and byte < 0x90:
            raise _DataFailure("Utf8Overlong", offset)
        if lead == 0xED and byte >= 0xA0: raise _DataFailure("Utf8Surrogate", offset)
        if lead == 0xF4 and byte >= 0x90: raise _DataFailure("Utf8Range", offset)
    accumulator = accumulator << 6 | byte & 63
    if remaining == 1: return _UTF8_EMPTY, chr(accumulator)
    return (remaining - 1, accumulator, start, lead, seen + 1), None


def _be32(n):
    return tuple((n >> shift) & 255 for shift in (24, 16, 8, 0))


def _from_unsigned(octets):
    # Called only for the fixed 1/4/8-octet scalar cursor.
    value = 0
    for b in octets: value = value << 8 | b
    return value


def _wire_header(prepared, t):
    stamp = digest({"profile_revision": PROFILE_REVISION, "codec_revision": CODEC_REVISION,
                    "type": type_json(t)})
    return tuple(MAGIC) + tuple(bytes.fromhex(prepared.registry.content_digest)) + tuple(bytes.fromhex(stamp))


def _child_count(v):
    if v.kind in ("seq", "record"): return len(v.data)
    if v.kind == "sum": return 1
    if v.kind == "map": return 2 * len(v.data)
    return 0


def _child_at(v, index, path):
    if v.kind == "seq": return v.data[index], path + (index,)
    if v.kind == "record":
        name, child = v.data[index]; return child, path + (name,)
    if v.kind == "sum": return v.data[2], path + (v.data[0],)
    row, slot = divmod(index, 2)
    return v.data[row][slot], path + (row, "key" if slot == 0 else "value")


class _Worker:
    """One transient transaction over an immutable machine, committed per rule."""
    def __init__(self, machine):
        self.p = machine.prepared; self.op = self.p.operation
        self.work = list(machine.work); self.results = list(machine.results)
        self.output = machine.output; self.output_size = machine.output_size
        self.position = machine.position; self.decoded_nodes = machine.decoded_nodes
        self.answer = None; self.finished = False

    def schedule(self, *tasks):
        if len(self.work) + len(tasks) > MAX_WORK: raise _PhysicalStop("WORK_LIMIT")
        self.work.extend(reversed(tasks))

    def write(self, octets, rule="ENCODE_WRITE", prefix="wire"):
        if octets:
            self.schedule(_Task(rule, (prefix, self.output_size), (octets, 0, prefix)))

    def compare(self, left, right, path):
        self.schedule(_Task("COMPARE_NODE", path, (left, right)))

    def compare_next(self, left, right, index, path):
        _, child_path = _child_at(left, index, path)
        self.schedule(_Task("COMPARE_NEXT", child_path, (left, right, index, path)))

    def encode_child(self, value, index, path):
        _, child_path = _child_at(value, index, path)
        self.schedule(_Task("ENCODE_NEXT", child_path, (value, index, path)))

    def read(self, mode, t, path, count, accumulator, start, extra=()):
        self.schedule(_Task("DECODE_READ", ("wire", self.position),
                            (mode, t, path, count, accumulator, start, extra)))

    def decode_child(self, t, path, depth, after):
        self.schedule(_Task("DECODE_NEXT", path, (t, depth)), after)

    def map_insert(self, entries, prefix, j, i=0):
        if j == len(entries):
            pairs = tuple((key, value) for key, value, _ in prefix)
            self.results.append(_runtime_value(self.op["type"], "map", pairs))
        elif i == len(prefix): self.map_rebuild(entries, prefix, j, i, 0, False, ())
        else:
            path = ("entries", j, "probe", i)
            self.schedule(_Task("MAP_PROBE", path, (entries, prefix, j, i)))

    def map_rebuild(self, entries, prefix, j, insertion, old_i, added, output):
        data = (entries, prefix, j, insertion, old_i, added, output)
        if not added and old_i == insertion: self.schedule(_Task("MAP_ADD", ("entries", j), data))
        elif old_i < len(prefix): self.schedule(_Task("MAP_COPY", ("entries", j, "copy", old_i), data))
        elif not added: self.schedule(_Task("MAP_ADD", ("entries", j), data))
        else: self.schedule(_Task("MAP_COMMIT", ("entries", j), data))

    def map_lookup(self, index):
        if index == len(self.op["map"].data): self.schedule(_Task("MAP_LOOKUP_END", ("map",)))
        else: self.schedule(_Task("MAP_LOOKUP", ("map", index), (index,)))

    def decoded_container_next(self, t, kind, path, depth, count, index, accumulated, start):
        if index == count:
            self.schedule(_Task("DECODE_ASSEMBLE", path, (t, kind, accumulated, start)))
            return
        if kind == "seq":
            child_type = t.args[0]; child_path = path + (index,)
            after = _Task("@D_SEQUENCE", path, (t, kind, depth, count, index, accumulated, start))
        elif kind == "record":
            name, child_type = self.p.registry.layout(t)[1][index]; child_path = path + (name,)
            after = _Task("@D_RECORD", path, (t, kind, depth, count, index, accumulated, start, name))
        else:
            child_type = t.args[0]; child_path = path + (index, "key")
            after = _Task("@D_MAP_KEY", path, (t, depth, count, index, accumulated, start, self.position))
        self.decode_child(child_type, child_path, depth + 1, after)

    def settle(self):
        # These frames only transfer completed results; they do not visit a new
        # scalar, byte, child, or comparison.  Such work has its own charged rule.
        while self.work and self.work[-1].rule.startswith("@"):
            task = self.work.pop(); d = task.data; path = task.path
            if task.rule == "@COMPARE_AFTER":
                left, right, index, parent = d; result = self.results.pop()
                if result: self.results.append(result)
                elif index + 1 < min(_child_count(left), _child_count(right)):
                    self.compare_next(left, right, index + 1, parent)
                else: self.schedule(_Task("COMPARE_END", parent, (left, right)))
            elif task.rule in ("@D_SEQUENCE", "@D_RECORD"):
                t, kind, depth, count, index, accumulated, start = d[:7]
                child = self.results.pop()
                item = (d[7], child) if kind == "record" else child
                accumulated += (item,)
                # The partial container is subject to the same data bounds.
                _runtime_value(t, kind, accumulated)
                self.decoded_container_next(t, kind, path, depth, count, index + 1, accumulated, start)
            elif task.rule == "@D_MAP_KEY":
                t, depth, count, index, accumulated, start, key_start = d
                key = self.results.pop()
                after = _Task("@D_MAP_VALUE", path, (t, depth, count, index, accumulated, start, key_start, key))
                self.decode_child(t.args[1], path + (index, "value"), depth + 1, after)
            elif task.rule == "@D_MAP_VALUE":
                t, depth, count, index, accumulated, start, key_start, key = d
                value = self.results.pop(); row = (key, value)
                if accumulated:
                    compare_path = path + (index, "order")
                    after = _Task("DECODE_MAP_ORDER", compare_path,
                                  (t, depth, count, index, accumulated, start, key_start, row, path))
                    self.schedule(after); self.compare(accumulated[-1][0], key, compare_path)
                else:
                    _runtime_value(t, "map", (row,))
                    self.decoded_container_next(t, "map", path, depth, count, index + 1, (row,), start)
            elif task.rule == "@D_SUM":
                t, tag, ordinal, start = d
                child = self.results.pop()
                self.schedule(_Task("DECODE_ASSEMBLE", path, (t, "sum", (tag, ordinal, child), start)))
            else: raise _PhysicalStop("MACHINE_INVARIANT")

    def perform(self, task):
        rule, path, d = task.rule, task.path, task.data
        if rule == "JOB_START":
            self.schedule(_Task("JOB_FINISH")); op = self.op["op"]
            if op == "record":
                if self.op["fields"]: self.schedule(_Task("RECORD_FIELD", ("fields", 0), (0,)))
            elif op == "variant": self.schedule(_Task("VARIANT_WRAP", ("value",)))
            elif op == "sequence":
                if self.op["items"]: self.schedule(_Task("SEQUENCE_ITEM", ("items", 0), (0, "items")))
            elif op == "seq_append":
                if self.op["sequence"].data: self.schedule(_Task("SEQUENCE_ITEM", ("sequence", 0), (0, "sequence")))
                else: self.schedule(_Task("SEQUENCE_APPEND", ("value",)))
            elif op == "field": self.schedule(_Task("FIELD_SELECT", ("record", self.op["field"])))
            elif op == "length":
                self.results.append(0)
                if self.op["value"].data: self.schedule(_Task("LENGTH_ITEM", ("value", 0), (0,)))
            elif op == "seq_get": self.schedule(_Task("SEQ_GET", ("sequence",)))
            elif op in ("equal", "compare"): self.compare(self.op["left"], self.op["right"], ("compare",))
            elif op == "map_build":
                if self.op["entries"]: self.schedule(_Task("MAP_STAGE", ("entries", 0), (0, ())))
                else: self.results.append(_runtime_value(self.op["type"], "map", ()))
            elif op == "map_get": self.map_lookup(0)
            elif op == "utf8_encode":
                if self.op["value"].data: self.schedule(_Task("UTF8_SCALAR", ("value", 0), (0,)))
            elif op == "utf8_decode":
                if self.op["value"].data: self.schedule(_Task("UTF8_READ", ("bytes", 0), (0, _UTF8_EMPTY, ())))
                else: self.schedule(_Task("UTF8_END", ("bytes",), (_UTF8_EMPTY, ())))
            elif op == "encode":
                self.schedule(_Task("ENCODE_NODE", ("value",), (self.op["value"],)))
                self.write(_wire_header(self.p, self.op["value"].type))
            elif op == "decode":
                header = _wire_header(self.p, self.op["type"])
                self.read("header", self.op["type"], ("value",), len(header), (), 0, (header, 0))
            else: raise _PhysicalStop("MACHINE_INVARIANT")
        elif rule == "JOB_FINISH":
            op = self.op["op"]; t = self.p.result_type
            if op == "record":
                fields = dict(self.results)
                value = _runtime_value(t, "record", tuple((name, fields[name]) for name, _ in self.p.registry.layout(t)[1]))
            elif op in ("sequence", "seq_append"): value = _runtime_value(t, "seq", tuple(self.results))
            elif op == "length": value = _runtime_value(INT, "Int64", self.results.pop())
            elif op == "equal": value = _runtime_value(BOOL, "Bool", self.results.pop() == 0)
            elif op == "compare": value = _runtime_value(INT, "Int64", self.results.pop())
            elif op in ("utf8_encode", "encode"):
                value = _runtime_value(BYTES, "Bytes", _linked_tuple(self.output))
            elif op in ("map_build", "utf8_decode", "decode"):
                value = _wrapped(t, "Ok", 0, self.results.pop())
            else: value = self.results.pop()
            self.answer = value; self.finished = True; self.work.clear(); self.results.clear()
        elif rule == "RECORD_FIELD":
            index = d[0]; item = self.op["fields"][index]
            _runtime_value(self.p.result_type, "record", tuple(self.results) + (item,))
            self.results.append(item)
            if index + 1 < len(self.op["fields"]):
                self.schedule(_Task(rule, ("fields", index + 1), (index + 1,)))
        elif rule == "VARIANT_WRAP":
            self.results.append(_wrapped(self.p.result_type, self.op["tag"], self.op["ordinal"], self.op["value"]))
        elif rule == "SEQUENCE_ITEM":
            index, source = d
            items = self.op["items"] if source == "items" else self.op["sequence"].data
            value = items[index]
            _runtime_value(self.p.result_type, "seq", tuple(self.results) + (value,))
            self.results.append(value)
            if index + 1 < len(items): self.schedule(_Task(rule, (source, index + 1), (index + 1, source)))
            elif source == "sequence": self.schedule(_Task("SEQUENCE_APPEND", ("value",)))
        elif rule == "SEQUENCE_APPEND":
            _runtime_value(self.p.result_type, "seq", tuple(self.results) + (self.op["value"],))
            self.results.append(self.op["value"])
        elif rule == "FIELD_SELECT": self.results.append(dict(self.op["record"].data)[self.op["field"]])
        elif rule == "LENGTH_ITEM":
            index = d[0]; self.results[-1] += 1
            if index + 1 < len(self.op["value"].data): self.schedule(_Task(rule, ("value", index + 1), (index + 1,)))
        elif rule == "SEQ_GET":
            index = self.op["index"].data; items = self.op["sequence"].data
            if 0 <= index < len(items): value = _wrapped(self.p.result_type, "Some", 1, items[index])
            else: value = _wrapped(self.p.result_type, "None", 0, _runtime_value(UNIT, "Unit", None))
            self.results.append(value)
        elif rule == "COMPARE_NODE":
            left, right = d; kind = left.kind
            if kind in ("Bool", "Int64", "Unit"):
                self.results.append(0 if kind == "Unit" else _sign(left.data, right.data))
            elif kind in ("String", "Bytes"):
                if min(len(left.data), len(right.data)): self.schedule(_Task("COMPARE_UNIT", path + (0,), (left, right, 0, path)))
                else: self.schedule(_Task("COMPARE_END", path, (left, right)))
            elif kind == "sum" and left.data[1] != right.data[1]: self.results.append(_sign(left.data[1], right.data[1]))
            elif kind == "map" and len(left.data) != len(right.data): self.results.append(_sign(len(left.data), len(right.data)))
            elif min(_child_count(left), _child_count(right)): self.compare_next(left, right, 0, path)
            else: self.schedule(_Task("COMPARE_END", path, (left, right)))
        elif rule == "COMPARE_UNIT":
            left, right, index, parent = d
            a = ord(left.data[index]) if left.kind == "String" else left.data[index]
            b = ord(right.data[index]) if right.kind == "String" else right.data[index]
            result = _sign(a, b)
            if result: self.results.append(result)
            elif index + 1 < min(len(left.data), len(right.data)):
                self.schedule(_Task(rule, parent + (index + 1,), (left, right, index + 1, parent)))
            else: self.schedule(_Task("COMPARE_END", parent, (left, right)))
        elif rule == "COMPARE_NEXT":
            left, right, index, parent = d
            a, _ = _child_at(left, index, parent); b, _ = _child_at(right, index, parent)
            self.schedule(_Task("@COMPARE_AFTER", parent, (left, right, index, parent)))
            self.compare(a, b, path)
        elif rule == "COMPARE_END":
            left, right = d
            self.results.append(_sign(len(left.data), len(right.data)) if left.kind in ("String", "Bytes", "seq") else 0)
        elif rule == "MAP_STAGE":
            index, staged = d; staged += (self.op["entries"][index],)
            if index + 1 < len(self.op["entries"]): self.schedule(_Task(rule, ("entries", index + 1), (index + 1, staged)))
            else: self.map_insert(staged, (), 0)
        elif rule == "MAP_PROBE":
            entries, prefix, j, i = d
            self.schedule(_Task("MAP_DECIDE", path, d)); self.compare(entries[j][0], prefix[i][0], path)
        elif rule == "MAP_DECIDE":
            entries, prefix, j, i = d; result = self.results.pop()
            if result == 0: raise _DataFailure("DuplicateKey", prefix[i][2], j)
            if result > 0: self.map_insert(entries, prefix, j, i + 1)
            else: self.map_rebuild(entries, prefix, j, i, 0, False, ())
        elif rule in ("MAP_COPY", "MAP_ADD", "MAP_COMMIT"):
            entries, prefix, j, insertion, old_i, added, output = d
            if rule == "MAP_COMMIT": self.map_insert(entries, output, j + 1)
            else:
                item = entries[j] if rule == "MAP_ADD" else prefix[old_i]
                output += (item,)
                _runtime_value(self.op["type"], "map", tuple((k, v) for k, v, _ in output))
                self.map_rebuild(entries, prefix, j, insertion,
                                 old_i + (rule == "MAP_COPY"), added or rule == "MAP_ADD", output)
        elif rule == "MAP_LOOKUP":
            index = d[0]
            self.schedule(_Task("MAP_LOOKUP_DECIDE", path, d))
            self.compare(self.op["key"], self.op["map"].data[index][0], path)
        elif rule == "MAP_LOOKUP_DECIDE":
            index = d[0]; result = self.results.pop()
            if result == 0:
                self.results.append(_wrapped(self.p.result_type, "Some", 1, self.op["map"].data[index][1]))
            elif result < 0:
                self.results.append(_wrapped(self.p.result_type, "None", 0, _runtime_value(UNIT, "Unit", None)))
            else: self.map_lookup(index + 1)
        elif rule == "MAP_LOOKUP_END":
            self.results.append(_wrapped(self.p.result_type, "None", 0, _runtime_value(UNIT, "Unit", None)))
        elif rule == "UTF8_SCALAR":
            index = d[0]; source = self.op["value"].data
            if index + 1 < len(source): self.schedule(_Task(rule, ("value", index + 1), (index + 1,)))
            self.write(_utf8_octets(source[index]), "UTF8_WRITE", "bytes")
        elif rule in ("UTF8_WRITE", "ENCODE_WRITE"):
            octets, index, prefix = d
            limit = self.op.get("wire_limit", MAX_OUTPUT)
            if self.output_size >= limit: raise _PhysicalStop("OUTPUT_LIMIT")
            self.output = _Link(octets[index], self.output); self.output_size += 1
            if index + 1 < len(octets):
                self.schedule(_Task(rule, (prefix, self.output_size), (octets, index + 1, prefix)))
        elif rule == "UTF8_READ":
            index, cursor, chars = d; source = self.op["value"].data
            cursor, scalar = _utf8_feed(cursor, source[index], index)
            if scalar is not None:
                if len(chars) >= MAX_STRING: raise _PhysicalStop("VALUE_LIMIT")
                chars += (scalar,)
            if index + 1 < len(source): self.schedule(_Task(rule, ("bytes", index + 1), (index + 1, cursor, chars)))
            else: self.schedule(_Task("UTF8_END", ("bytes",), (cursor, chars)))
        elif rule == "UTF8_END":
            cursor, chars = d
            if cursor[0]: raise _DataFailure("Utf8Truncated", cursor[2])
            self.results.append(_runtime_value(STRING, "String", "".join(chars)))
        elif rule.startswith("ENCODE_"): self.encode_step(task)
        elif rule.startswith("DECODE_"): self.decode_step(task)
        else: raise _PhysicalStop("MACHINE_INVARIANT")

    def encode_step(self, task):
        rule, path, d = task.rule, task.path, task.data
        if rule == "ENCODE_NODE":
            value = d[0]; kind = value.kind
            if kind == "Bool": self.write((int(value.data),))
            elif kind == "Int64": self.write(tuple((value.data >> shift) & 255 for shift in range(56, -1, -8)))
            elif kind == "Unit": pass
            elif kind == "String":
                if value.data: self.schedule(_Task("ENCODE_SCAN", path + (0,), (value, 0, 0, path)))
                else: self.write(_be32(0))
            elif kind == "Bytes":
                if value.data:
                    # A cursor over immutable input octets, not a copied encoding.
                    self.schedule(_Task("ENCODE_WRITE", ("wire", self.output_size + 4), (value.data, 0, "wire")))
                self.write(_be32(len(value.data)))
            elif kind in ("seq", "map", "record", "sum"):
                if _child_count(value): self.encode_child(value, 0, path)
                if kind in ("seq", "map"): self.write(_be32(len(value.data)))
                elif kind == "sum": self.write(_be32(value.data[1]))
            else: raise _PhysicalStop("MACHINE_INVARIANT")
        elif rule == "ENCODE_NEXT":
            parent, index, parent_path = d; child, _ = _child_at(parent, index, parent_path)
            if index + 1 < _child_count(parent): self.encode_child(parent, index + 1, parent_path)
            self.schedule(_Task("ENCODE_NODE", path, (child,)))
        elif rule == "ENCODE_SCAN":
            value, index, size, parent_path = d; size += len(_utf8_octets(value.data[index]))
            if index + 1 < len(value.data):
                self.schedule(_Task(rule, parent_path + (index + 1,), (value, index + 1, size, parent_path)))
            else:
                self.schedule(_Task("ENCODE_SCALAR", parent_path + (0,), (value, 0, parent_path)))
                self.write(_be32(size))
        elif rule == "ENCODE_SCALAR":
            value, index, parent_path = d
            if index + 1 < len(value.data):
                self.schedule(_Task(rule, parent_path + (index + 1,), (value, index + 1, parent_path)))
            self.write(_utf8_octets(value.data[index]))
        else: raise _PhysicalStop("MACHINE_INVARIANT")

    def decode_step(self, task):
        rule, path, d = task.rule, task.path, task.data
        if rule == "DECODE_READ":
            mode, t, parent_path, count, accumulated, start, extra = d
            source = self.op["bytes"].data
            if self.position >= len(source): raise _DataFailure("UnexpectedEnd", self.position)
            offset = self.position; byte = source[offset]
            if mode == "header":
                expected, index = extra
                if byte != expected[index]: raise _DataFailure("ContextMismatch", offset)
                self.position += 1
                if index + 1 < len(expected):
                    self.read(mode, t, parent_path, count - 1, (), start, (expected, index + 1))
                else:
                    self.schedule(_Task("DECODE_NODE", parent_path, (t, 0)), _Task("DECODE_END"))
                return
            if mode == "string":
                cursor, chars = accumulated
                cursor, scalar = _utf8_feed(cursor, byte, offset)
                if scalar is not None:
                    if len(chars) >= MAX_STRING: raise _PhysicalStop("VALUE_LIMIT")
                    chars += (scalar,)
                accumulated = (cursor, chars)
            elif mode == "bytes": accumulated = _Link(byte, accumulated)
            else: accumulated += (byte,)
            self.position += 1
            if count > 1:
                self.read(mode, t, parent_path, count - 1, accumulated, start, extra)
            elif mode == "length":
                self.schedule(_Task("DECODE_LENGTH", parent_path, (t, accumulated, start, extra[0])))
            elif mode == "tag":
                self.schedule(_Task("DECODE_TAG", parent_path, (t, accumulated, start, extra[0])))
            else: self.schedule(_Task("DECODE_SCALAR", parent_path, (t, mode, accumulated, start)))
        elif rule == "DECODE_NODE":
            t, depth = d
            if self.decoded_nodes >= MAX_VALUE_NODES or depth > MAX_VALUE_DEPTH:
                raise _PhysicalStop("VALUE_LIMIT")
            self.decoded_nodes += 1; start = self.position
            if t == BOOL: self.read("bool", t, path, 1, (), start)
            elif t == INT: self.read("int", t, path, 8, (), start)
            elif t == UNIT: self.results.append(_runtime_value(UNIT, "Unit", None))
            elif t in (STRING, BYTES) or t.tag in ("seq", "map"):
                self.read("length", t, path, 4, (), start, (depth,))
            else:
                kind, members = self.p.registry.layout(t)
                if kind == "record":
                    self.decoded_container_next(t, kind, path, depth, len(members), 0, (), start)
                elif kind == "sum": self.read("tag", t, path, 4, (), start, (depth,))
                else: raise _PhysicalStop("MACHINE_INVARIANT")
        elif rule == "DECODE_NEXT":
            t, depth = d; self.schedule(_Task("DECODE_NODE", path, (t, depth)))
        elif rule == "DECODE_LENGTH":
            t, octets, start, depth = d; count = _from_unsigned(octets)
            cap = MAX_STRING * 4 if t == STRING else MAX_BYTES if t == BYTES else MAX_ITEMS
            if count > cap: raise _PhysicalStop("VALUE_LIMIT")
            if t == STRING:
                if count: self.read("string", t, path, count, (_UTF8_EMPTY, ()), start)
                else: self.schedule(_Task("DECODE_SCALAR", path, (t, "string", (_UTF8_EMPTY, ()), start)))
            elif t == BYTES:
                if count: self.read("bytes", t, path, count, None, start)
                else: self.schedule(_Task("DECODE_SCALAR", path, (t, "bytes", None, start)))
            else: self.decoded_container_next(t, t.tag, path, depth, count, 0, (), start)
        elif rule == "DECODE_TAG":
            t, octets, start, depth = d; ordinal = _from_unsigned(octets)
            members = self.p.registry.layout(t)[1]
            if ordinal >= len(members): raise _DataFailure("UnknownVariant", start)
            tag, child_type = members[ordinal]
            after = _Task("@D_SUM", path, (t, tag, ordinal, start))
            self.decode_child(child_type, path + (tag,), depth + 1, after)
        elif rule == "DECODE_SCALAR":
            t, mode, accumulated, start = d
            if mode == "bool":
                if accumulated[0] not in (0, 1): raise _DataFailure("InvalidEncoding", start)
                value = _runtime_value(BOOL, "Bool", bool(accumulated[0]))
            elif mode == "int":
                integer = _from_unsigned(accumulated)
                if integer >= 2**63: integer -= 2**64
                value = _runtime_value(INT, "Int64", integer)
            elif mode == "string":
                cursor, chars = accumulated
                if cursor[0]: raise _DataFailure("Utf8Truncated", cursor[2])
                value = _runtime_value(STRING, "String", "".join(chars))
            elif mode == "bytes": value = _runtime_value(BYTES, "Bytes", _linked_tuple(accumulated))
            else: raise _PhysicalStop("MACHINE_INVARIANT")
            self.results.append(value)
        elif rule == "DECODE_ASSEMBLE":
            t, kind, accumulated, start = d
            if t == ERROR and dict(accumulated)["code"].data not in ERROR_CODES:
                raise _DataFailure("InvalidEncoding", start)
            self.results.append(_runtime_value(t, kind, accumulated))
        elif rule == "DECODE_MAP_ORDER":
            t, depth, count, index, accumulated, start, key_start, row, parent_path = d
            result = self.results.pop()
            if result >= 0: raise _DataFailure("NonCanonicalMap", key_start)
            accumulated += (row,); _runtime_value(t, "map", accumulated)
            self.decoded_container_next(t, "map", parent_path, depth, count, index + 1, accumulated, start)
        elif rule == "DECODE_END":
            if self.position != len(self.op["bytes"].data): raise _DataFailure("TrailingBytes", self.position)
        else: raise _PhysicalStop("MACHINE_INVARIANT")


def launch(job_or_prepared, budget, *, cancel_at=None, cancel_request_id="cancel"):
    if type(budget) is not int or not 0 <= budget <= MAX_BUDGET:
        raise DataCoreError("INVALID_BUDGET")
    if cancel_at is not None and (type(cancel_at) is not int or not 0 <= cancel_at <= MAX_BUDGET):
        raise DataCoreError("INVALID_CANCELLATION")
    _id(cancel_request_id, ("cancel_request_id",))
    # A supplied Prepared is convenient, never an authority to skip validation.
    job = job_or_prepared.job if isinstance(job_or_prepared, Prepared) else job_or_prepared
    if not isinstance(job, Job): raise DataCoreError("INVALID_SHAPE", detail="Job or Prepared required")
    prepared = prepare(job)
    return Machine(prepared, (_Task("JOB_START"),), (), None, 0, 0, 0,
                   0, budget, None, cancel_at, cancel_request_id)


def step(machine):
    if not isinstance(machine, Machine): raise DataCoreError("INVALID_SHAPE", detail="Machine required")
    if machine.termination is not None: return machine
    if machine.cancel_at is not None and machine.steps >= machine.cancel_at:
        return replace(machine, termination="SEMANTIC_STOP", code="CANCELLED", answer=None)
    if machine.remaining == 0:
        return replace(machine, termination="SEMANTIC_STOP", code="BUDGET_EXCEEDED", answer=None)
    worker = _Worker(machine)
    if not worker.work:
        return replace(machine, termination="IMPLEMENTATION_STOP", code="MACHINE_INVARIANT", answer=None)
    task = worker.work.pop()
    if task.rule not in RULE_IDS:
        return replace(machine, termination="IMPLEMENTATION_STOP", code="MACHINE_INVARIANT", answer=None)
    # The end cursor is known only after the last decoded subtree completed.
    if task.rule == "DECODE_END": task = _Task(task.rule, ("wire", worker.position), task.data)
    try:
        worker.perform(task); worker.settle()
    except _DataFailure as failure:
        worker.answer = _error_result(machine.prepared.result_type, failure)
        worker.finished = True; worker.work.clear(); worker.results.clear()
    except _PhysicalStop as failure:
        # Refuse before publishing any part of the attempted transition.
        return replace(machine, termination="IMPLEMENTATION_STOP", code=failure.code, answer=None)
    entry = TraceEntry(machine.steps + 1, task.rule, task.path)
    return replace(machine, work=tuple(worker.work), results=tuple(worker.results),
                   output=worker.output, output_size=worker.output_size,
                   position=worker.position, decoded_nodes=worker.decoded_nodes,
                   steps=machine.steps + 1, remaining=machine.remaining - 1,
                   trace=_Link(entry, machine.trace), answer=worker.answer,
                   termination="RETURNED" if worker.finished else None,
                   code="RETURNED" if worker.finished else None)


def execution(machine):
    if not isinstance(machine, Machine) or machine.termination is None:
        raise DataCoreError("INVALID_SHAPE", detail="terminal Machine required")
    p = machine.prepared
    return Execution(PROFILE_REVISION, CODEC_REVISION, p.content_digest, p.registry.content_digest,
                     machine.termination, machine.code, machine.answer, machine.steps,
                     machine.remaining, _linked_tuple(machine.trace),
                     machine.cancel_request_id if machine.code == "CANCELLED" else None)


def execution_json(result):
    if not isinstance(result, Execution): raise DataCoreError("INVALID_SHAPE", detail="Execution required")
    return {"profile_revision": result.profile_revision, "codec_revision": result.codec_revision,
            "content_digest": result.content_digest, "registry_digest": result.registry_digest,
            "termination": result.termination, "code": result.code,
            "value": value_json(result.value) if result.value is not None else None,
            "steps": result.steps, "remaining": result.remaining,
            "trace": [{"step_index": row.step_index, "rule": row.rule, "path": list(row.path)} for row in result.trace],
            "cancel_request_id": result.cancel_request_id}


def run(job_or_prepared, budget, *, cancel_at=None, cancel_request_id="cancel"):
    machine = launch(job_or_prepared, budget, cancel_at=cancel_at, cancel_request_id=cancel_request_id)
    while machine.termination is None: machine = step(machine)
    return execution(machine)

