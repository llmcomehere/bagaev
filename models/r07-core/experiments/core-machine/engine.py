"""CORE-0.1: typed pure JSON expressions and an explicit small-step CEK.

This is a research profile, not bagaev or a complete V1 implementation.
Only reference transitions consume semantic steps.  Checked arithmetic Err is
ordinary data; physical profile guards are not semantic budget outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from hashlib import sha256
from types import MappingProxyType
from collections.abc import Mapping
import json
from typing import Any


PROFILE_REVISION = "core-machine/r06-v1"
PRIMITIVE_REVISION = "core-i64/r06-v1"
MIN_INT, MAX_INT = -(2**63), 2**63 - 1
MAX_NODES, MAX_DEPTH, MAX_BINDERS = 1024, 64, 1024
MAX_TYPE_PARAMETERS, MAX_ARITY, MAX_GROUP_PARAMETERS = 128, 16, 8
MAX_TYPE_DEPTH, MAX_TYPE_NODES = 32, 8192
MAX_BUDGET, MAX_HEAP, MAX_CONTINUATION = 65536, 4096, 4096
MAX_VALUE_TYPE_DEPTH, MAX_VALUE_TYPE_NODES = 64, 8192
PRIMITIVES = ("i64.eq", "i64.lt", "i64.add", "i64.sub", "i64.div", "i64.rem")
ARITHMETIC_ERRORS = ("Overflow", "DivisionByZero")


class CoreError(ValueError):
    def __init__(self, code, path=(), detail="", kind="PrelaunchDiagnostic"):
        self.code, self.path, self.detail, self.kind = code, tuple(path), detail, kind
        super().__init__(code + (": " + detail if detail else ""))


def _id(value, path=()):
    if type(value) is not str or not value:
        raise CoreError("INVALID_ID", path)
    if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise CoreError("INVALID_UNICODE_SCALAR", path)
    if len(value) > 128:
        raise CoreError("PROFILE_LIMIT", path, "ID length")
    return value


def _freeze(value, path=(), depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    if depth > 256 or count[0] > 65536:
        raise CoreError("PROFILE_LIMIT", path, "raw JSON size/depth")
    if isinstance(value, Mapping):
        result = {}
        for key, child in value.items():
            if type(key) is not str:
                raise CoreError("INVALID_SHAPE", path, "non-string JSON key")
            if any(0xD800 <= ord(c) <= 0xDFFF for c in key):
                raise CoreError("INVALID_UNICODE_SCALAR", path)
            result[key] = _freeze(child, path + (key,), depth + 1, count)
        return MappingProxyType(result)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(child, path + (i,), depth + 1, count) for i, child in enumerate(value))
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if not MIN_INT <= value <= MAX_INT:
            raise CoreError("INVALID_LITERAL", path, "integer outside Int64")
        return value
    if type(value) is str:
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise CoreError("INVALID_UNICODE_SCALAR", path)
        if len(value) > 512:
            raise CoreError("PROFILE_LIMIT", path, "raw string length")
        return value
    raise CoreError("INVALID_SHAPE", path, "not a JSON value")


def canonical(value):
    if is_dataclass(value):
        return {f.name: canonical(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {key: canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [canonical(child) for child in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise CoreError("INVALID_SHAPE", detail="non-canonical value")


def digest(value):
    data = json.dumps(canonical(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    return sha256(data.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Program:
    source_id: str
    revision: str
    result_type: Any
    entry: Any
    profile_revision: str = PROFILE_REVISION

    def __post_init__(self):
        _id(self.source_id, ("source_id",))
        _id(self.revision, ("revision",))
        _id(self.profile_revision, ("profile_revision",))
        frozen = _freeze({"source_id": self.source_id, "revision": self.revision,
                          "result_type": self.result_type, "entry": self.entry,
                          "profile_revision": self.profile_revision})
        object.__setattr__(self, "result_type", frozen["result_type"])
        object.__setattr__(self, "entry", frozen["entry"])


@dataclass(frozen=True)
class Type:
    tag: str
    args: tuple[Type, ...] = ()
    var_id: str | None = None


BOOL, INT, UNIT, ERROR = (Type(t) for t in ("Bool", "Int64", "Unit", "ArithmeticError"))
SCALARS = {t.tag: t for t in (BOOL, INT, UNIT, ERROR)}


def _fn(params, result):
    return Type("Fn", tuple(params) + (result,))


def _result_type(ok):
    return Type("Result", (ok,))


def type_json(typ):
    if typ.tag in SCALARS:
        return typ.tag
    if typ.tag == "Var":
        return {"tag": "var", "id": typ.var_id}
    if typ.tag == "Fn":
        return {"tag": "fn", "params": [type_json(t) for t in typ.args[:-1]],
                "result": type_json(typ.args[-1])}
    if typ.tag == "Result":
        return {"tag": "result", "ok": type_json(typ.args[0])}
    raise CoreError("INVALID_TYPE")


def _closed(value, keys, path):
    if not isinstance(value, Mapping):
        raise CoreError("INVALID_SHAPE", path, "object expected")
    extra, missing = set(value) - set(keys), set(keys) - set(value)
    if extra:
        raise CoreError("UNKNOWN_FIELD", path + (sorted(extra)[0],))
    if missing:
        raise CoreError("MISSING_FIELD", path + (sorted(missing)[0],))


def _seq(value, path, limit=MAX_ARITY):
    if not isinstance(value, (tuple, list)):
        raise CoreError("INVALID_SHAPE", path, "array expected")
    if len(value) > limit:
        raise CoreError("PROFILE_LIMIT", path, "array length")
    return value


def _substitute(typ, substitutions):
    if typ.tag == "Var":
        return substitutions.get(typ.var_id, typ)
    if not typ.args:
        return typ
    return Type(typ.tag, tuple(_substitute(t, substitutions) for t in typ.args))


@dataclass(frozen=True)
class Scheme:
    parameters: tuple[str, ...]
    body: Type


@dataclass(frozen=True)
class FunctionInfo:
    binder: str
    params: tuple[tuple[str, Type], ...]
    result_type: Type
    body_id: str

    @property
    def type(self):
        return _fn((t for _, t in self.params), self.result_type)


@dataclass(frozen=True)
class Prepared:
    program: Program
    content_digest: str
    result_type: Type
    nodes: Mapping
    node_types: Mapping
    type_arguments: Mapping
    result_ok_types: Mapping
    group_functions: Mapping


FIELDS = {
    "const": ("type", "value"),
    "var": ("binder", "type_args"),
    "let": ("binder", "type", "value", "body"),
    "if": ("condition", "then", "else"),
    "lambda": ("params", "result_type", "body"),
    "call": ("fn", "args"),
    "letrec": ("type_params", "functions", "body"),
    "prim": ("name", "args"),
    "result": ("tag", "ok_type", "value"),
    "match_result": ("value", "ok_binder", "ok_body", "err_binder", "err_body"),
}


class _Checker:
    def __init__(self):
        self.nodes, self.node_types, self.type_arguments = {}, {}, {}
        self.result_ok_types, self.group_functions = {}, {}
        self.binders, self.type_parameters = set(), set()
        self.type_count = 0

    def typ(self, raw, scope, path, depth=0):
        self.type_count += 1
        if self.type_count > MAX_TYPE_NODES or depth > MAX_TYPE_DEPTH:
            raise CoreError("PROFILE_LIMIT", path, "type nodes/depth")
        if type(raw) is str:
            if raw not in SCALARS:
                raise CoreError("INVALID_TYPE", path)
            return SCALARS[raw]
        if not isinstance(raw, Mapping) or type(raw.get("tag")) is not str:
            raise CoreError("INVALID_TYPE", path)
        tag = raw["tag"]
        if tag == "var":
            _closed(raw, ("tag", "id"), path)
            name = _id(raw["id"], path + ("id",))
            if name not in scope:
                raise CoreError("UNBOUND_TYPE_VARIABLE", path, name)
            return Type("Var", var_id=name)
        if tag == "fn":
            _closed(raw, ("tag", "params", "result"), path)
            params = _seq(raw["params"], path + ("params",))
            return _fn((self.typ(t, scope, path + ("params", i), depth + 1)
                        for i, t in enumerate(params)),
                       self.typ(raw["result"], scope, path + ("result",), depth + 1))
        if tag == "result":
            _closed(raw, ("tag", "ok"), path)
            return _result_type(self.typ(raw["ok"], scope, path + ("ok",), depth + 1))
        raise CoreError("INVALID_TYPE", path, tag)

    def declare(self, name, path):
        _id(name, path)
        if name in self.binders:
            raise CoreError("DUPLICATE_BINDER", path, name)
        self.binders.add(name)
        if len(self.binders) > MAX_BINDERS:
            raise CoreError("PROFILE_LIMIT", path, "binders")
        return name

    def params(self, raw, scope, path):
        result = []
        for i, param in enumerate(_seq(raw, path)):
            p = path + (i,)
            _closed(param, ("binder", "type"), p)
            name = self.declare(param["binder"], p + ("binder",))
            result.append((name, self.typ(param["type"], scope, p + ("type",))))
        return tuple(result)

    def same(self, actual, expected, path):
        if actual != expected:
            raise CoreError("TYPE_MISMATCH", path,
                            f"expected {type_json(expected)!r}; got {type_json(actual)!r}")

    def check(self, node, env, scope, path, depth=0):
        if depth > MAX_DEPTH or len(self.nodes) >= MAX_NODES:
            raise CoreError("PROFILE_LIMIT", path, "expression nodes/depth")
        if not isinstance(node, Mapping):
            raise CoreError("INVALID_SHAPE", path, "node expected")
        op = node.get("op")
        if type(op) is not str or op not in FIELDS:
            raise CoreError("UNKNOWN_FORM", path + ("op",))
        _closed(node, ("op", "nid") + FIELDS[op], path)
        nid = _id(node["nid"], path + ("nid",))
        if nid in self.nodes:
            raise CoreError("DUPLICATE_NODE_ID", path + ("nid",), nid)
        self.nodes[nid] = node

        def child(key, child_env=env, child_scope=scope):
            return self.check(node[key], child_env, child_scope, path + (key,), depth + 1)

        if op == "const":
            typ = self.typ(node["type"], scope, path + ("type",))
            value = node["value"]
            valid = ((typ == BOOL and type(value) is bool)
                     or (typ == INT and type(value) is int and MIN_INT <= value <= MAX_INT)
                     or (typ == UNIT and value is None)
                     or (typ == ERROR and type(value) is str and value in ARITHMETIC_ERRORS))
            if not valid:
                raise CoreError("INVALID_LITERAL", path)
        elif op == "var":
            name = _id(node["binder"], path + ("binder",))
            if name not in env:
                raise CoreError("UNBOUND_VARIABLE", path, name)
            args = tuple(self.typ(t, scope, path + ("type_args", i))
                         for i, t in enumerate(_seq(node["type_args"], path + ("type_args",))))
            scheme = env[name]
            if len(args) != len(scheme.parameters):
                raise CoreError("TYPE_ARGUMENT_ARITY", path)
            typ = _substitute(scheme.body, dict(zip(scheme.parameters, args)))
            self.type_arguments[nid] = args
        elif op == "let":
            name = self.declare(node["binder"], path + ("binder",))
            declared = self.typ(node["type"], scope, path + ("type",))
            self.same(child("value"), declared, path + ("value",))
            typ = child("body", {**env, name: Scheme((), declared)})
        elif op == "if":
            self.same(child("condition"), BOOL, path + ("condition",))
            typ, other = child("then"), child("else")
            self.same(other, typ, path + ("else",))
        elif op == "lambda":
            params = self.params(node["params"], scope, path + ("params",))
            result = self.typ(node["result_type"], scope, path + ("result_type",))
            body_env = {**env, **{name: Scheme((), t) for name, t in params}}
            self.same(child("body", body_env), result, path + ("body",))
            typ = _fn((t for _, t in params), result)
        elif op == "call":
            function = child("fn")
            args = _seq(node["args"], path + ("args",))
            actual = tuple(self.check(arg, env, scope, path + ("args", i), depth + 1)
                           for i, arg in enumerate(args))
            if function.tag != "Fn":
                raise CoreError("TYPE_MISMATCH", path + ("fn",), "function expected")
            if len(actual) != len(function.args) - 1:
                raise CoreError("CALL_ARITY", path)
            for i, (got, expected) in enumerate(zip(actual, function.args[:-1])):
                self.same(got, expected, path + ("args", i))
            typ = function.args[-1]
        elif op == "letrec":
            parameters = tuple(_seq(node["type_params"], path + ("type_params",), MAX_GROUP_PARAMETERS))
            for i, parameter in enumerate(parameters):
                p = path + ("type_params", i)
                _id(parameter, p)
                if parameter in self.type_parameters:
                    raise CoreError("DUPLICATE_TYPE_PARAMETER", p, parameter)
                self.type_parameters.add(parameter)
                if len(self.type_parameters) > MAX_TYPE_PARAMETERS:
                    raise CoreError("PROFILE_LIMIT", p, "type parameters")
            inner_scope = scope | frozenset(parameters)
            functions = _seq(node["functions"], path + ("functions",))
            if not functions:
                raise CoreError("INVALID_SHAPE", path + ("functions",), "empty recursive group")
            infos = []
            for i, function in enumerate(functions):
                p = path + ("functions", i)
                _closed(function, ("binder", "params", "result_type", "body"), p)
                binder = self.declare(function["binder"], p + ("binder",))
                params = self.params(function["params"], inner_scope, p + ("params",))
                result = self.typ(function["result_type"], inner_scope, p + ("result_type",))
                if not isinstance(function["body"], Mapping):
                    raise CoreError("INVALID_SHAPE", p + ("body",))
                infos.append(FunctionInfo(binder, params, result, function["body"].get("nid")))
            monomorphic = {**env, **{f.binder: Scheme((), f.type) for f in infos}}
            for i, (function, info) in enumerate(zip(functions, infos)):
                body_env = {**monomorphic, **{name: Scheme((), t) for name, t in info.params}}
                p = path + ("functions", i, "body")
                actual = self.check(function["body"], body_env, inner_scope, p, depth + 1)
                self.same(actual, info.result_type, p)
            outside = {**env, **{f.binder: Scheme(parameters, f.type) for f in infos}}
            self.group_functions[nid] = tuple(infos)
            typ = child("body", outside)
        elif op == "prim":
            if type(node["name"]) is not str or node["name"] not in PRIMITIVES:
                raise CoreError("UNKNOWN_PRIMITIVE", path + ("name",))
            args = _seq(node["args"], path + ("args",))
            if len(args) != 2:
                raise CoreError("CALL_ARITY", path)
            for i, arg in enumerate(args):
                self.same(self.check(arg, env, scope, path + ("args", i), depth + 1),
                          INT, path + ("args", i))
            typ = BOOL if node["name"] in ("i64.eq", "i64.lt") else _result_type(INT)
        elif op == "result":
            ok = self.typ(node["ok_type"], scope, path + ("ok_type",))
            if node["tag"] not in ("Ok", "Err"):
                raise CoreError("INVALID_RESULT_TAG", path + ("tag",))
            self.same(child("value"), ok if node["tag"] == "Ok" else ERROR, path + ("value",))
            self.result_ok_types[nid] = ok
            typ = _result_type(ok)
        elif op == "match_result":
            subject = child("value")
            if subject.tag != "Result":
                raise CoreError("TYPE_MISMATCH", path + ("value",), "Result expected")
            ok_name = self.declare(node["ok_binder"], path + ("ok_binder",))
            err_name = self.declare(node["err_binder"], path + ("err_binder",))
            typ = child("ok_body", {**env, ok_name: Scheme((), subject.args[0])})
            other = child("err_body", {**env, err_name: Scheme((), ERROR)})
            self.same(other, typ, path + ("err_body",))
        else:
            raise CoreError("UNKNOWN_FORM", path)
        self.node_types[nid] = typ
        return typ


def prepare(program):
    if not isinstance(program, Program):
        raise CoreError("INVALID_SHAPE", detail="Program expected")
    if program.profile_revision != PROFILE_REVISION:
        raise CoreError("UNSUPPORTED_PROFILE", ("profile_revision",))
    checker = _Checker()
    declared = checker.typ(program.result_type, frozenset(), ("result_type",))
    actual = checker.check(program.entry, {}, frozenset(), ("entry",))
    checker.same(actual, declared, ("entry",))
    stamp = digest({"profile_revision": PROFILE_REVISION,
                    "primitive_revision": PRIMITIVE_REVISION, "program": canonical(program)})
    return Prepared(program, stamp, actual,
                    MappingProxyType(dict(checker.nodes)), MappingProxyType(dict(checker.node_types)),
                    MappingProxyType(dict(checker.type_arguments)), MappingProxyType(dict(checker.result_ok_types)),
                    MappingProxyType(dict(checker.group_functions)))


def decode_program(raw):
    raw = _freeze(raw)
    _closed(raw, ("source_id", "revision", "result_type", "entry", "profile_revision"), ())
    return Program(raw["source_id"], raw["revision"], raw["result_type"], raw["entry"], raw["profile_revision"])


@dataclass(frozen=True)
class FunctionRef:
    heap_slot: int
    member: int | None
    type_args: tuple[Type, ...]
    content_digest: str
    node_id: str


@dataclass(frozen=True)
class Value:
    type: Type
    tag: str
    payload: Any


@dataclass(frozen=True)
class GroupBinding:
    heap_slot: int
    member: int
    specialization: tuple[Type, ...] | None


@dataclass(frozen=True)
class Capture:
    kind: str
    node_id: str
    environment: tuple
    type_environment: tuple


@dataclass(frozen=True)
class Frame:
    kind: str
    node_id: str
    environment: tuple
    type_environment: tuple
    values: tuple[Value, ...] = ()
    index: int = 0
    function: Value | None = None


@dataclass(frozen=True)
class TraceEntry:
    step_index: int
    rule: str
    node_id: str


@dataclass(frozen=True)
class Machine:
    prepared: Prepared
    control: str | Value
    environment: tuple = ()
    type_environment: tuple = ()
    continuation: tuple[Frame, ...] = ()
    heap: tuple[Capture, ...] = ()
    steps: int = 0
    remaining: int = 0
    trace: tuple[TraceEntry, ...] = ()
    cancel_at: int | None = None
    cancel_request_id: str = "cancel"
    termination: str | None = None
    code: str | None = None


@dataclass(frozen=True)
class Execution:
    profile_revision: str
    content_digest: str
    termination: str
    code: str
    value: Value | None
    steps: int
    remaining: int
    trace: tuple[TraceEntry, ...]
    cancel_request_id: str | None


class _Guard(RuntimeError):
    def __init__(self, code):
        self.code = code


def _value(typ, tag, payload):
    stack, count = [(typ, 0)], 0
    while stack:
        current, depth = stack.pop()
        count += 1
        if count > MAX_VALUE_TYPE_NODES or depth > MAX_VALUE_TYPE_DEPTH:
            raise _Guard("VALUE_LIMIT")
        if current.tag == "Var":
            raise RuntimeError("unresolved runtime type variable")
        stack.extend((child, depth + 1) for child in current.args)
    return Value(typ, tag, payload)


def _scalar(typ, payload):
    return _value(typ, "Scalar", payload)


def _extend(env, bindings):
    result = dict(env)
    result.update(bindings)
    return tuple(sorted(result.items()))


def _resolve(typ, type_environment):
    return _substitute(typ, dict(type_environment))


def _push(machine, frame):
    if len(machine.continuation) >= MAX_CONTINUATION:
        raise _Guard("CONTINUATION_LIMIT")
    return machine.continuation + (frame,)


def _capture(machine, kind, nid):
    if len(machine.heap) >= MAX_HEAP:
        raise _Guard("HEAP_LIMIT")
    capture = Capture(kind, nid, machine.environment, machine.type_environment)
    return len(machine.heap), machine.heap + (capture,)


def _function_value(machine, binding, explicit):
    if isinstance(binding, Value):
        if explicit:
            raise RuntimeError("type arguments on monomorphic value")
        return binding
    capture = machine.heap[binding.heap_slot]
    node = machine.prepared.nodes[capture.node_id]
    info = machine.prepared.group_functions[capture.node_id][binding.member]
    if binding.specialization is None:
        args = tuple(_resolve(t, machine.type_environment) for t in explicit)
    else:
        if explicit:
            raise RuntimeError("polymorphic recursive reference")
        args = binding.specialization
    if len(args) != len(node["type_params"]):
        raise RuntimeError("bad runtime type arguments")
    tenv = _extend(capture.type_environment, zip(node["type_params"], args))
    typ = _resolve(info.type, tenv)
    ref = FunctionRef(binding.heap_slot, binding.member, args,
                      machine.prepared.content_digest, capture.node_id)
    return _value(typ, "Function", ref)


def _enter_body(machine, function, arguments, continuation):
    if function.tag != "Function" or function.type.tag != "Fn":
        raise RuntimeError("non-function in call")
    if tuple(v.type for v in arguments) != function.type.args[:-1]:
        raise RuntimeError("runtime call signature mismatch")
    ref = function.payload
    capture = machine.heap[ref.heap_slot]
    node = machine.prepared.nodes[capture.node_id]
    if ref.content_digest != machine.prepared.content_digest:
        raise RuntimeError("wrong code snapshot")
    if capture.kind == "lambda":
        if ref.member is not None or ref.type_args:
            raise RuntimeError("invalid lambda reference")
        env, tenv = capture.environment, capture.type_environment
        params, body = tuple(p["binder"] for p in node["params"]), node["body"]["nid"]
    elif capture.kind == "group":
        infos = machine.prepared.group_functions[capture.node_id]
        info = infos[ref.member]
        group_bindings = ((f.binder, GroupBinding(ref.heap_slot, i, ref.type_args)) for i, f in enumerate(infos))
        env = _extend(capture.environment, group_bindings)
        tenv = _extend(capture.type_environment, zip(node["type_params"], ref.type_args))
        params, body = tuple(name for name, _ in info.params), info.body_id
    else:
        raise RuntimeError("invalid capture kind")
    if len(params) != len(arguments):
        raise RuntimeError("runtime call arity")
    return replace(machine, control=body, environment=_extend(env, zip(params, arguments)),
                   type_environment=tenv, continuation=continuation)


def _primitive(name, values):
    if len(values) != 2 or any(v.type != INT or v.tag != "Scalar" for v in values):
        raise RuntimeError("primitive signature")
    a, b = (v.payload for v in values)
    if name == "i64.eq":
        return _scalar(BOOL, a == b)
    if name == "i64.lt":
        return _scalar(BOOL, a < b)
    error = None
    if name == "i64.add":
        result = a + b
    elif name == "i64.sub":
        result = a - b
    elif name in ("i64.div", "i64.rem"):
        if b == 0:
            error, result = "DivisionByZero", 0
        else:
            quotient = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                quotient = -quotient
            result = quotient if name == "i64.div" else a - quotient * b
    else:
        raise RuntimeError("unknown primitive")
    if error is None and not MIN_INT <= result <= MAX_INT:
        error = "Overflow"
    payload = _scalar(ERROR, error) if error else _scalar(INT, result)
    return _value(_result_type(INT), "Err" if error else "Ok", payload)


def _transition(machine):
    prepared = machine.prepared
    if type(machine.control) is str:
        nid = machine.control
        node = prepared.nodes[nid]
        op = node["op"]
        if op == "const":
            value = _scalar(_resolve(prepared.node_types[nid], machine.type_environment), node["value"])
            return replace(machine, control=value), "CONST", nid
        if op == "var":
            binding = dict(machine.environment)[node["binder"]]
            value = _function_value(machine, binding, prepared.type_arguments[nid])
            return replace(machine, control=value), "VAR", nid
        if op == "lambda":
            slot, heap = _capture(machine, "lambda", nid)
            typ = _resolve(prepared.node_types[nid], machine.type_environment)
            value = _value(typ, "Function", FunctionRef(slot, None, (), prepared.content_digest, nid))
            return replace(machine, control=value, heap=heap), "LAMBDA", nid
        if op == "letrec":
            slot, heap = _capture(machine, "group", nid)
            bindings = ((f.binder, GroupBinding(slot, i, None))
                        for i, f in enumerate(prepared.group_functions[nid]))
            return replace(machine, control=node["body"]["nid"], heap=heap,
                           environment=_extend(machine.environment, bindings)), "LETREC", nid
        frame_kind = {"let": "LET", "if": "IF", "call": "CALL_FN", "prim": "PRIM",
                      "result": "RESULT", "match_result": "MATCH"}[op]
        frame = Frame(frame_kind, nid, machine.environment, machine.type_environment)
        continuation = _push(machine, frame)
        if op == "let":
            child, rule = node["value"], "LET_ENTER"
        elif op == "if":
            child, rule = node["condition"], "IF_ENTER"
        elif op == "call":
            child, rule = node["fn"], "CALL_ENTER"
        elif op == "prim":
            child, rule = node["args"][0], "PRIM_ENTER"
        elif op == "result":
            child, rule = node["value"], "RESULT_ENTER"
        else:
            child, rule = node["value"], "MATCH_ENTER"
        return replace(machine, control=child["nid"], continuation=continuation), rule, nid

    value = machine.control
    frame = machine.continuation[-1]
    rest = machine.continuation[:-1]
    node, nid = prepared.nodes[frame.node_id], frame.node_id
    if frame.kind == "LET":
        new = replace(machine, control=node["body"]["nid"], continuation=rest,
                      environment=_extend(frame.environment, ((node["binder"], value),)),
                      type_environment=frame.type_environment)
        return new, "LET_BIND", nid
    if frame.kind == "IF":
        if value.type != BOOL or value.tag != "Scalar":
            raise RuntimeError("non-Bool condition")
        branch = "then" if value.payload else "else"
        new = replace(machine, control=node[branch]["nid"], continuation=rest,
                      environment=frame.environment, type_environment=frame.type_environment)
        return new, "IF_THEN" if value.payload else "IF_ELSE", nid
    if frame.kind == "CALL_FN":
        if not node["args"]:
            return _enter_body(machine, value, (), rest), "CALL_BODY", nid
        new_frame = replace(frame, kind="CALL_ARGS", function=value)
        new = replace(machine, control=node["args"][0]["nid"], continuation=rest + (new_frame,),
                      environment=frame.environment, type_environment=frame.type_environment)
        return new, "CALL_ARGS", nid
    if frame.kind in ("CALL_ARGS", "PRIM"):
        values = frame.values + (value,)
        index = frame.index + 1
        if index < len(node["args"]):
            new_frame = replace(frame, values=values, index=index)
            new = replace(machine, control=node["args"][index]["nid"], continuation=rest + (new_frame,),
                          environment=frame.environment, type_environment=frame.type_environment)
            return new, "CALL_NEXT" if frame.kind == "CALL_ARGS" else "PRIM_NEXT", nid
        if frame.kind == "CALL_ARGS":
            return _enter_body(machine, frame.function, values, rest), "CALL_BODY", nid
        return replace(machine, control=_primitive(node["name"], values), continuation=rest), "PRIM_APPLY", nid
    if frame.kind == "RESULT":
        typ = _result_type(_resolve(prepared.result_ok_types[nid], frame.type_environment))
        expected = typ.args[0] if node["tag"] == "Ok" else ERROR
        if value.type != expected:
            raise RuntimeError("Result payload type")
        return replace(machine, control=_value(typ, node["tag"], value), continuation=rest), "RESULT_WRAP", nid
    if frame.kind == "MATCH":
        if value.type.tag != "Result" or value.tag not in ("Ok", "Err"):
            raise RuntimeError("Match on non-Result")
        branch = "ok" if value.tag == "Ok" else "err"
        env = _extend(frame.environment, ((node[branch + "_binder"], value.payload),))
        new = replace(machine, control=node[branch + "_body"]["nid"], continuation=rest,
                      environment=env, type_environment=frame.type_environment)
        return new, "MATCH_OK" if branch == "ok" else "MATCH_ERR", nid
    raise RuntimeError("unknown continuation frame")


def launch(program_or_prepared, budget, *, cancel_at=None, cancel_request_id="cancel"):
    program = program_or_prepared.program if isinstance(program_or_prepared, Prepared) else program_or_prepared
    prepared = prepare(program)
    if type(budget) is not int or budget < 0:
        raise CoreError("INVALID_BUDGET")
    if budget > MAX_BUDGET:
        raise CoreError("PROFILE_LIMIT", detail="requested step budget")
    if cancel_at is not None:
        if type(cancel_at) is not int or cancel_at < 0:
            raise CoreError("INVALID_CANCELLATION")
        if cancel_at > MAX_BUDGET:
            raise CoreError("PROFILE_LIMIT", detail="cancellation boundary")
    _id(cancel_request_id, ("cancel_request_id",))
    return Machine(prepared, prepared.program.entry["nid"], remaining=budget,
                   cancel_at=cancel_at, cancel_request_id=cancel_request_id)


def step(machine):
    if machine.termination is not None:
        return machine
    if isinstance(machine.control, Value) and not machine.continuation:
        return replace(machine, termination="RETURNED", code="RETURNED")
    if machine.cancel_at is not None and machine.steps >= machine.cancel_at:
        return replace(machine, termination="SEMANTIC_STOP", code="CANCELLED")
    if machine.remaining == 0:
        return replace(machine, termination="SEMANTIC_STOP", code="BUDGET_EXCEEDED")
    try:
        new, rule, nid = _transition(machine)
    except _Guard as guard:
        return replace(machine, termination="IMPLEMENTATION_STOP", code=guard.code)
    except (RuntimeError, KeyError, IndexError, TypeError, ValueError, AttributeError):
        return replace(machine, termination="IMPLEMENTATION_STOP", code="MACHINE_INVARIANT")
    completed = machine.steps + 1
    new = replace(new, steps=completed, remaining=machine.remaining - 1,
                  trace=machine.trace + (TraceEntry(completed, rule, nid),))
    if isinstance(new.control, Value) and not new.continuation:
        new = replace(new, termination="RETURNED", code="RETURNED")
    return new


def execution(machine):
    if machine.termination is None:
        raise CoreError("MACHINE_NOT_TERMINAL", kind="HostAPIDiagnostic")
    value = machine.control if machine.termination == "RETURNED" else None
    return Execution(PROFILE_REVISION, machine.prepared.content_digest,
                     machine.termination, machine.code, value, machine.steps, machine.remaining,
                     machine.trace, machine.cancel_request_id if machine.code == "CANCELLED" else None)


def run(program_or_prepared, budget, *, cancel_at=None, cancel_request_id="cancel"):
    machine = launch(program_or_prepared, budget, cancel_at=cancel_at, cancel_request_id=cancel_request_id)
    while machine.termination is None:
        machine = step(machine)
    return execution(machine)


def observe_value(value):
    if not isinstance(value, Value):
        raise CoreError("INVALID_VALUE", kind="HostAPIDiagnostic")
    typ = type_json(value.type)
    if value.tag == "Scalar":
        return {"type": typ, "value": value.payload}
    if value.tag in ("Ok", "Err"):
        return {"type": typ, "tag": value.tag, "value": observe_value(value.payload)}
    if value.tag == "Function":
        ref = value.payload
        return {"type": typ, "kind": "Function", "code": {
            "content_digest": ref.content_digest, "node_id": ref.node_id, "member": ref.member}}
    raise CoreError("INVALID_VALUE", kind="HostAPIDiagnostic")


def encode_data(value):
    if not isinstance(value, Value):
        raise CoreError("INVALID_VALUE", kind="CodecDiagnostic")
    pending = [value.type]
    while pending:
        typ = pending.pop()
        if typ.tag in ("Fn", "Var"):
            raise CoreError("NON_PERSISTABLE_VALUE", kind="CodecDiagnostic")
        pending.extend(typ.args)
    if value.tag in ("Ok", "Err"):
        payload = encode_data(value.payload)
        return {"type": type_json(value.type), "tag": value.tag, "value": payload}
    return observe_value(value)


def execution_json(result):
    return {"profile_revision": result.profile_revision, "content_digest": result.content_digest,
            "termination": result.termination, "code": result.code,
            "value": observe_value(result.value) if result.value is not None else None,
            "steps": result.steps, "remaining": result.remaining,
            "trace": [canonical(entry) for entry in result.trace],
            "cancel_request_id": result.cancel_request_id}
