"""CALL-0.1: finite static calls over pinned OBS/R03 research semantics.

This is an executable research AST, not the bagaev language/runtime.  Modular
analysis never trusts supplied summaries; a separate structural checker
reconstructs a bounded hygienic strict-let bridge to the frozen OBS AST.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any


class CallError(ValueError):
    def __init__(self, code: str, path: str = "$", detail: str = ""):
        self.code, self.path, self.detail = code, path, detail
        super().__init__(f"{code} at {path}" + (f": {detail}" if detail else ""))


PROFILE_REVISION = "static-call-observation-profile/r04-v1"
EXPECTED_OBS_SHA256 = "9406e4faefd01def24d87f2316f0d21546ea971eb99194771d5ce9eafdca48da"
EXPECTED_LAWS_SHA256 = "ab830682a35ac09d72bb319c26c7a0671c77a63f3e0a6e50f4842973207e7f37"
OBS_PATH = Path(__file__).resolve().parent.parent / "observation-profile" / "engine.py"
LAWS_PATH = Path(__file__).resolve().parent.parent / "law-profile" / "laws.py"
SUPPORTED_PROVIDER = "provider/v1"
MAX_FUNCTIONS, MAX_PARAMETERS, MAX_CONSUMERS = 64, 16, 64
MAX_SOURCE_AST_NODES, MAX_SOURCE_JSON_NODES = 4096, 32768
MAX_SOURCE_STRING_BYTES = 1024 * 1024
MAX_CALL_DEPTH, MAX_EXPANDED_AST_NODES = 32, 8192
MAX_ANALYSIS_STEPS = MAX_EXECUTION_STEPS = 65536


def _check_sources():
    for path, expected in ((OBS_PATH, EXPECTED_OBS_SHA256), (LAWS_PATH, EXPECTED_LAWS_SHA256)):
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise CallError("SEMANTICS_SOURCE_MISMATCH", detail=str(path))


def _load_laws():
    _check_sources()
    name = "_bagaev_r04_frozen_laws"
    if name in sys.modules:
        module = sys.modules[name]
        if Path(module.__file__).resolve() != LAWS_PATH:
            raise CallError("SEMANTICS_SOURCE_MISMATCH", detail="module path differs")
        return module
    spec = importlib.util.spec_from_file_location(name, LAWS_PATH)
    if spec is None or spec.loader is None:
        raise CallError("SEMANTICS_SOURCE_MISMATCH", detail="cannot load frozen laws")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


laws = _load_laws()
obs = laws.engine
ResourceState, Type, UseSummary = obs.ResourceState, obs.Type, obs.UseSummary


def _source_stamps():
    _check_sources()
    return {"profile": PROFILE_REVISION, "obs": EXPECTED_OBS_SHA256,
            "laws": EXPECTED_LAWS_SHA256, "calls": sha256(Path(__file__).read_bytes()).hexdigest()}


def _json_measure(value, path="$", *, node_limit=MAX_SOURCE_JSON_NODES):
    """Bound traversal before freezing/canonicalizing user-supplied JSON."""
    stack, count, strings, maximum_depth, ast_nodes = [(value, 0)], 0, 0, 0, 0
    while stack:
        item, depth = stack.pop()
        count += 1
        maximum_depth = max(maximum_depth, depth)
        if count > node_limit:
            raise CallError("SOURCE_LIMIT", path, "JSON item budget")
        if depth > obs.MAX_AST_DEPTH:
            raise CallError("SOURCE_LIMIT", path, "JSON depth budget")
        if type(item) is str:
            obs._text(item, path, empty=True)
            if len(item) > MAX_SOURCE_STRING_BYTES:
                raise CallError("SOURCE_LIMIT", path, "string byte budget")
            strings += len(item.encode("utf-8"))
            if strings > MAX_SOURCE_STRING_BYTES:
                raise CallError("SOURCE_LIMIT", path, "string byte budget")
        elif isinstance(item, Mapping):
            if len(item) * 2 + count > node_limit:
                raise CallError("SOURCE_LIMIT", path, "JSON object budget")
            if "op" in item:
                ast_nodes += 1
            for key, child in item.items():
                if type(key) is not str:
                    raise obs.ProfileError("INVALID_JSON_KEY", path)
                stack.append((key, depth + 1))
                stack.append((child, depth + 1))
        elif isinstance(item, (tuple, list)):
            if len(item) + count > node_limit:
                raise CallError("SOURCE_LIMIT", path, "JSON array budget")
            stack.extend((child, depth + 1) for child in item)
    return count, strings, maximum_depth, ast_nodes


def _freeze(value, path="$"):
    _json_measure(value, path)
    return obs._freeze_json(value, path)


def _limited_tuple(values, limit, code):
    try:
        iterator = iter(values)
    except TypeError as error:
        raise CallError(code, detail="an iterable is required") from error
    result = []
    for item in iterator:
        if len(result) == limit:
            raise CallError(code)
        result.append(item)
    return tuple(result)


def _text(value, path, *, empty=False):
    result = obs._text(value, path, empty=empty)
    if len(result) > MAX_SOURCE_STRING_BYTES or len(result.encode("utf-8")) > MAX_SOURCE_STRING_BYTES:
        raise CallError("SOURCE_LIMIT", path, "string byte budget")
    return result


@dataclass(frozen=True)
class Param:
    name: str
    type: Any

    def __post_init__(self):
        _text(self.name, "$.param.name")
        annotation = _freeze(self.type, "$.param.type")
        obs._annotation(annotation, "$.param.type")
        object.__setattr__(self, "type", annotation)


@dataclass(frozen=True)
class Function:
    stable_id: str
    params: tuple[Param, ...]
    return_type: Any
    body: Mapping | None
    alias: str = ""

    def __post_init__(self):
        _text(self.stable_id, "$.function.stable_id")
        _text(self.alias, "$.function.alias", empty=True)
        params = _limited_tuple(self.params, MAX_PARAMETERS, "PARAMETER_LIMIT")
        if not all(isinstance(p, Param) for p in params):
            raise CallError("INVALID_PARAMETER")
        if len({p.name for p in params}) != len(params):
            raise CallError("DUPLICATE_PARAMETER")
        annotation = _freeze(self.return_type, "$.function.return_type")
        obs._annotation(annotation, "$.function.return_type")
        object.__setattr__(self, "params", params)
        object.__setattr__(self, "return_type", annotation)
        if self.body is not None:
            object.__setattr__(self, "body", _freeze(self.body, "$.function.body"))

    @property
    def signature_revision(self):
        return obs.digest({"params": self.params, "return_type": self.return_type})

    @property
    def definition_revision(self):
        return obs.digest({"signature": self.signature_revision, "body": self.body})


@dataclass(frozen=True)
class Registry:
    functions: tuple[Function, ...] = ()

    def __post_init__(self):
        functions = _limited_tuple(self.functions, MAX_FUNCTIONS, "FUNCTION_LIMIT")
        if not all(isinstance(f, Function) for f in functions):
            raise CallError("INVALID_FUNCTION")
        if len({f.stable_id for f in functions}) != len(functions):
            raise CallError("DUPLICATE_FUNCTION_ID")
        object.__setattr__(self, "functions", tuple(sorted(functions, key=lambda f: f.stable_id)))

    @property
    def manifest_stamp(self):
        return obs.digest(tuple((f.stable_id, f.signature_revision, f.definition_revision)
                                for f in self.functions))


@dataclass(frozen=True)
class Consumer:
    stable_id: str
    program: Mapping
    compile_config: Mapping[str, bool] = field(default_factory=dict)
    provider_revision: str = SUPPORTED_PROVIDER
    requirements: Mapping[str, str] = field(default_factory=dict)
    alias: str = ""

    def __post_init__(self):
        _text(self.stable_id, "$.consumer.stable_id")
        _text(self.provider_revision, "$.consumer.provider_revision")
        _text(self.alias, "$.consumer.alias", empty=True)
        object.__setattr__(self, "program", _freeze(self.program))
        _json_measure(self.compile_config)
        object.__setattr__(self, "compile_config", obs._config(self.compile_config))
        if not isinstance(self.requirements, Mapping):
            raise CallError("INVALID_REQUIREMENTS")
        _json_measure(self.requirements)
        requirements = {}
        for identifier, revision in self.requirements.items():
            _text(identifier, "$.requirements.id")
            _text(revision, "$.requirements.revision")
            requirements[identifier] = revision
        object.__setattr__(self, "requirements", MappingProxyType(requirements))

    @property
    def program_revision(self):
        return obs.digest(self.program)

    @property
    def input_stamp(self):
        return obs.digest({"stable_id": self.stable_id, "program": self.program,
                           "config": self.compile_config, "provider": self.provider_revision,
                           "requirements": self.requirements, "profile": PROFILE_REVISION})


@dataclass(frozen=True)
class Program:
    entry: Consumer
    registry: Registry

    def __post_init__(self):
        if not isinstance(self.entry, Consumer) or not isinstance(self.registry, Registry):
            raise CallError("INVALID_PROGRAM")


def _program_budget(program):
    counts = [0, 0, 0]
    roots = [program.entry.program, program.entry.compile_config, program.entry.requirements]
    roots += [f.body for f in program.registry.functions if f.body is not None]
    roots += [f.return_type for f in program.registry.functions]
    roots += [p.type for f in program.registry.functions for p in f.params]
    roots += [program.entry.stable_id, program.entry.provider_revision, program.entry.alias]
    roots += [text for f in program.registry.functions for text in (f.stable_id, f.alias)]
    roots += [p.name for f in program.registry.functions for p in f.params]
    for root in roots:
        nodes, strings, _, ast_nodes = _json_measure(root)
        counts[0] += nodes
        counts[1] += strings
        counts[2] += ast_nodes
        if (counts[0] > MAX_SOURCE_JSON_NODES or counts[1] > MAX_SOURCE_STRING_BYTES
                or counts[2] > MAX_SOURCE_AST_NODES):
            raise CallError("SOURCE_LIMIT", detail="whole Program budget")


def _op(ast, path):
    if not isinstance(ast, Mapping) or type(ast.get("op")) is not str:
        raise obs.ProfileError("INVALID_AST_OPERATION", path)
    return _text(ast["op"], path + ".op")


def _children(ast, path="$"):
    op = _op(ast, path)
    rules = {
        "const": (("value",), (), ()), "read": (("view",), (), ()),
        "var": (("name",), (), ()), "config": (("key",), (), ()),
        "let": (("name", "value", "body"), (), ("value", "body")),
        "if": (("condition", "then", "else"), (), ("condition", "then", "else")),
        "size": (("value",), (), ("value",)), "to_set": (("value",), (), ("value",)),
        "head": (("value",), (), ("value",)),
        "contains": (("collection", "item"), (), ("collection", "item")),
        "eq": (("left", "right"), (), ("left", "right")),
        "pair": (("left", "right"), (), ("left", "right")),
        "fail": (("code", "type"), (), ()), "unknown": (("type",), ("reason",), ()),
    }
    if op in rules:
        required, optional, names = rules[op]
        obs._fields(ast, required, optional, path)
        return tuple((name,) for name in names)
    if op in {"tuple", "seq"}:
        obs._fields(ast, ("items",), path=path)
        items = obs._items(ast["items"], path + ".items", nonempty=op == "seq")
        return tuple(("items", i) for i in range(len(items)))
    if op == "emit":
        obs._fields(ast, ("label", "value"), ("then",), path)
        return (("value",), ("then",)) if "then" in ast else (("value",),)
    if op == "opaque":
        obs._fields(ast, ("name", "type"), ("kind", "args"), path)
        args = obs._items(ast.get("args", ()), path + ".args")
        return tuple(("args", i) for i in range(len(args)))
    if op == "call":
        obs._fields(ast, ("target", "args", "type"), path=path)
        _text(ast["target"], path + ".target")
        obs._annotation(ast["type"], path + ".type")
        args = obs._items(ast["args"], path + ".args")
        if len(args) > MAX_PARAMETERS:
            raise CallError("PARAMETER_LIMIT", path)
        return tuple(("args", i) for i in range(len(args)))
    raise obs.ProfileError("UNSUPPORTED_AST_OPERATION", path + ".op", op)


def _at(ast, path):
    for token in path:
        ast = ast[token]
    return ast


def _shell(ast, replacements):
    result = dict(ast)
    for path, value in replacements:
        if len(path) == 1:
            result[path[0]] = value
        else:
            if not isinstance(result[path[0]], list):
                result[path[0]] = list(result[path[0]])
            result[path[0]][path[1]] = value
    return result


def _primitive(ast, parts, env, config):
    """Pinned primitive checks with typed var shells; no fake fail/unknown."""
    local_env, substitutions = dict(env), []
    used = set(env)
    if ast["op"] == "let":
        used.add(ast["name"])
    serial = 0
    for path, typ, _ in parts:
        name = f"__call_type_{serial}"
        while name in used:
            serial += 1
            name = f"__call_type_{serial}"
        used.add(name)
        serial += 1
        local_env[name] = typ
        substitutions.append((path, {"op": "var", "name": name}))
    typ, intrinsic = obs._analyze(_shell(ast, substitutions), local_env, config)
    return typ, obs._merge(intrinsic, *(use for _, _, use in parts))


def _unknown(reason):
    return UseSummary(complete=False, may_errors=frozenset({"*"}),
                      effects=frozenset({"*"}), reasons=(reason,))


def _signature(ast, arg_types, functions, path):
    annotation = obs._annotation(ast["type"], path + ".type")
    function = functions.get(ast["target"])
    if function is not None:
        if len(arg_types) != len(function.params):
            raise CallError("CALL_ARITY_MISMATCH", path)
        for index, (actual, parameter) in enumerate(zip(arg_types, function.params)):
            if actual != obs._annotation(parameter.type, path):
                raise CallError("CALL_ARGUMENT_TYPE_MISMATCH", path + f".args[{index}]")
        if annotation != obs._annotation(function.return_type, path):
            raise CallError("CALL_RESULT_TYPE_MISMATCH", path + ".type")
    return annotation, function


class _Walker:
    def __init__(self, program, *, compose):
        self.program, self.compose = program, compose
        self.functions = {f.stable_id: f for f in program.registry.functions}
        self.config = program.entry.compile_config
        self.steps, self.memo, self.seen = 0, {}, {}

    def walk(self, ast, env, path="$", depth=0, active=()):
        self.steps += 1
        if self.steps > MAX_ANALYSIS_STEPS:
            raise CallError("ANALYSIS_STEP_LIMIT", path)
        if depth > obs.MAX_AST_DEPTH:
            raise CallError("ANALYSIS_DEPTH_LIMIT", path)
        children = _children(ast, path)
        op = ast["op"]
        parts = []
        if op == "let":
            name = _text(ast["name"], path + ".name")
            typ, use = self.walk(ast["value"], env, path + ".value", depth + 1, active)
            parts.append((("value",), typ, use))
            local = dict(env)
            local[name] = typ
            typ, use = self.walk(ast["body"], local, path + ".body", depth + 1, active)
            parts.append((("body",), typ, use))
        else:
            for child_path in children:
                typ, use = self.walk(_at(ast, child_path), env,
                                     path + "." + ".".join(map(str, child_path)), depth + 1, active)
                parts.append((child_path, typ, use))
        if op != "call":
            return _primitive(ast, parts, env, self.config)
        typ, function = _signature(ast, [t for _, t, _ in parts], self.functions, path)
        argument_use = obs._merge(*(u for _, _, u in parts))
        if not self.compose:
            return typ, argument_use
        if function is None:
            return typ, obs._merge(argument_use, _unknown("MISSING_CALLEE:" + ast["target"]))
        body_use = self.function_use(function, active, depth + 1)
        return typ, obs._merge(argument_use, body_use)

    def function_use(self, function, active, depth):
        identifier = function.stable_id
        if function.body is None:
            use = _unknown("EXTERNAL_CALLEE:" + identifier)
            self.seen[identifier] = use
            return use
        if identifier in active:
            return _unknown("CALL_CYCLE:" + identifier)
        if len(active) >= MAX_CALL_DEPTH:
            raise CallError("CALL_DEPTH_LIMIT", detail=identifier)
        if identifier in self.memo:
            return self.memo[identifier]
        env = {p.name: obs._annotation(p.type, "$.params") for p in function.params}
        _, use = self.walk(function.body, env, "$.functions." + identifier, depth, active + (identifier,))
        self.seen[identifier] = use
        if not any(r.startswith("CALL_CYCLE:") for r in use.reasons):
            self.memo[identifier] = use
        return use


def validate_program(program: Program) -> Type:
    _check_sources()
    if not isinstance(program, Program):
        raise CallError("INVALID_PROGRAM")
    _program_budget(program)
    walker = _Walker(program, compose=False)
    for function in program.registry.functions:
        if function.body is None:
            continue
        env = {p.name: obs._annotation(p.type, "$.params") for p in function.params}
        typ, _ = walker.walk(function.body, env, "$.functions." + function.stable_id)
        if typ != obs._annotation(function.return_type, "$.return_type"):
            raise CallError("FUNCTION_RETURN_TYPE_MISMATCH", detail=function.stable_id)
    result_type = walker.walk(program.entry.program, {})[0]
    # This guard is independent of summary memoization.  A cached shallow
    # callee summary cannot conceal a longer caller-to-leaf path.
    memo = {}
    def call_depth(identifier, active):
        if identifier in active:
            return 0  # Recursion is reported as incomplete by analysis.
        function = walker.functions.get(identifier)
        if function is None or function.body is None:
            return 0
        if identifier in memo:
            return memo[identifier]
        depth = 1 + max((call_depth(target, active + (identifier,))
                         for target in sorted(_calls(function.body))), default=0)
        if depth > MAX_CALL_DEPTH:
            raise CallError("CALL_DEPTH_LIMIT", detail=identifier)
        memo[identifier] = depth
        return depth
    for target in sorted(_calls(program.entry.program)):
        call_depth(target, ())
    return result_type


@dataclass(frozen=True)
class LookupBinding:
    target_id: str
    state: str
    signature_revision: str | None
    definition_revision: str | None


def _calls(ast):
    stack, result = [ast], set()
    while stack:
        node = stack.pop()
        paths = _children(node)
        if node["op"] == "call":
            result.add(node["target"])
        stack.extend(_at(node, path) for path in paths)
    return result


def _closure(ast, functions):
    pending, bindings = list(_calls(ast)), {}
    while pending:
        identifier = pending.pop()
        if identifier in bindings:
            continue
        function = functions.get(identifier)
        if function is None:
            bindings[identifier] = LookupBinding(identifier, "MISSING", None, None)
        else:
            bindings[identifier] = LookupBinding(identifier, "EXTERNAL" if function.body is None else "PRESENT",
                                                  function.signature_revision, function.definition_revision)
            if function.body is not None:
                pending.extend(_calls(function.body) - bindings.keys())
    return tuple(bindings[k] for k in sorted(bindings))


@dataclass(frozen=True)
class FunctionSummary:
    function_id: str
    definition_revision: str
    result_type: Type
    use: UseSummary
    closure: tuple[LookupBinding, ...]
    closure_stamp: str


@dataclass(frozen=True)
class Analysis:
    result_type: Type
    use: UseSummary
    closure: tuple[LookupBinding, ...]
    closure_stamp: str
    registry_stamp: str
    function_summaries: tuple[FunctionSummary, ...]
    entry_stamp: str
    semantic_stamp: str


def analyze(program: Program) -> Analysis:
    result_type = validate_program(program)
    walker = _Walker(program, compose=True)
    _, use = walker.walk(program.entry.program, {})
    closure = _closure(program.entry.program, walker.functions)
    if program.entry.provider_revision != SUPPORTED_PROVIDER:
        use = obs._merge(use, _unknown("UNSUPPORTED_PROVIDER_REVISION:" + program.entry.provider_revision))
    summaries = []
    for identifier in sorted(walker.seen):
        function = walker.functions[identifier]
        subclosure = () if function.body is None else _closure(function.body, walker.functions)
        summaries.append(FunctionSummary(identifier, function.definition_revision,
                                         obs._annotation(function.return_type, "$.return_type"),
                                         walker.seen[identifier], subclosure, obs.digest(subclosure)))
    closure_stamp = obs.digest(closure)
    semantic_stamp = obs.digest({"entry": program.entry.input_stamp, "closure": closure_stamp,
                                 "sources": _source_stamps()})
    return Analysis(result_type, use, closure, closure_stamp, program.registry.manifest_stamp,
                    tuple(summaries), program.entry.input_stamp, semantic_stamp)


def _evaluate(ast, env, program, functions, resource, trace, active, budget, depth=0):
    budget[0] += 1
    if budget[0] > MAX_EXECUTION_STEPS:
        raise CallError("EXECUTION_STEP_LIMIT")
    if depth > obs.MAX_AST_DEPTH:
        raise CallError("EXECUTION_DEPTH_LIMIT")
    op = ast["op"]
    config = program.entry.compile_config
    def ev(child, local_env=env):
        return _evaluate(child, local_env, program, functions, resource, trace, active, budget, depth + 1)
    if op == "call":
        # Do not mark the outer target active while evaluating its arguments.
        values = [ev(argument) for argument in ast["args"]]
        target = ast["target"]
        function = functions.get(target)
        if function is None:
            raise obs._RuntimeUnknown("MISSING_CALLEE:" + target)
        if function.body is None:
            raise obs._RuntimeUnknown("EXTERNAL_CALLEE:" + target)
        if target in active:
            raise obs._RuntimeUnknown("CALL_CYCLE:" + target)
        if len(active) >= MAX_CALL_DEPTH:
            raise CallError("CALL_DEPTH_LIMIT", detail=target)
        local = {p.name: value for p, value in zip(function.params, values)}
        return _evaluate(function.body, local, program, functions, resource, trace, active + (target,), budget, depth + 1)
    if op == "let":
        value = ev(ast["value"])
        local = dict(env)
        local[ast["name"]] = value
        return ev(ast["body"], local)
    if op == "if":
        return ev(ast["then"] if ev(ast["condition"]) else ast["else"])
    if op == "emit":
        value = ev(ast["value"])
        trace.append(obs.Effect(ast["label"], value))
        return ev(ast["then"]) if "then" in ast else None
    paths = _children(ast)
    if not paths:
        return obs._evaluate(ast, resource, config, env, trace)
    local, replacements = {}, []
    for i, path in enumerate(paths):
        name = "__call_value_" + str(i)
        local[name] = ev(_at(ast, path))
        replacements.append((path, {"op": "var", "name": name}))
    return obs._evaluate(_shell(ast, replacements), resource, config, local, trace)


def execute(program: Program, resource: ResourceState | None) -> obs.Execution:
    validate_program(program)
    obs._resource(resource)
    if program.entry.provider_revision != SUPPORTED_PROVIDER:
        return obs.Execution("unknown", complete=False,
                             unknown_reason="UNSUPPORTED_PROVIDER_REVISION:" + program.entry.provider_revision)
    functions = {f.stable_id: f for f in program.registry.functions}
    trace = []
    try:
        value = _evaluate(program.entry.program, {}, program, functions, resource, trace, (), [0])
        return obs.Execution("ok", value, trace=tuple(trace))
    except obs._RuntimeFault as error:
        return obs.Execution("error", error=str(error), trace=tuple(trace))
    except obs._RuntimeUnknown as unknown:
        return obs.Execution("unknown", trace=tuple(trace), complete=False, unknown_reason=str(unknown))


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _same(left, right):
    def text(value):
        return json.dumps(obs.to_data(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    return text(left) == text(right)


@dataclass(frozen=True)
class ExpansionContext:
    entry_stamp: str
    registry_stamp: str
    closure_stamp: str
    profile_revision: str
    obs_sha256: str
    laws_sha256: str
    call_engine_sha256: str


@dataclass(frozen=True)
class ExpansionBinding:
    call_path: tuple[str | int, ...]
    target_id: str
    definition_revision: str
    parameter_names: tuple[str, ...]
    temporary_names: tuple[str, ...]

    def __post_init__(self):
        object.__setattr__(self, "call_path", tuple(self.call_path))
        object.__setattr__(self, "parameter_names", tuple(self.parameter_names))
        object.__setattr__(self, "temporary_names", tuple(self.temporary_names))


@dataclass(frozen=True)
class Expansion:
    context: ExpansionContext
    expanded_ast: Mapping
    bindings: tuple[ExpansionBinding, ...]

    def __post_init__(self):
        # Expanded source has its own AST bound, larger than input source.
        _json_measure(self.expanded_ast, node_limit=MAX_SOURCE_JSON_NODES * 4)
        object.__setattr__(self, "expanded_ast", obs._freeze_json(self.expanded_ast))
        bindings = _limited_tuple(self.bindings, MAX_EXPANDED_AST_NODES, "EXPANSION_NODE_LIMIT")
        if not all(isinstance(b, ExpansionBinding) for b in bindings):
            raise CallError("MALFORMED_EXPANSION")
        object.__setattr__(self, "bindings", bindings)


@dataclass(frozen=True)
class VerifiedExpansion:
    expansion: Expansion
    consumer: obs.Consumer
    summary: UseSummary


@dataclass(frozen=True)
class BridgeRefinement:
    expansion: Expansion
    derivation: laws.Derivation
    summary: UseSummary
    saturated: bool


def _expansion_context(program, analysis):
    stamps = _source_stamps()
    return ExpansionContext(program.entry.input_stamp, analysis.registry_stamp, analysis.closure_stamp,
                            PROFILE_REVISION, stamps["obs"], stamps["laws"], stamps["calls"])


def _expansion_metrics(ast, functions, memo, active=(), traversal_depth=0):
    if traversal_depth > obs.MAX_AST_DEPTH:
        raise CallError("EXPANSION_DEPTH_LIMIT")
    paths = _children(ast)
    child_metrics = [(path, _expansion_metrics(_at(ast, path), functions, memo, active, traversal_depth + 1))
                     for path in paths]
    if ast["op"] == "call":
        function = functions[ast["target"]]
        identifier = function.stable_id
        if identifier in active or function.body is None:
            raise CallError("BRIDGE_UNSUPPORTED")
        if len(active) >= MAX_CALL_DEPTH:
            raise CallError("CALL_DEPTH_LIMIT")
        if identifier not in memo:
            memo[identifier] = _expansion_metrics(function.body, functions, memo, active + (identifier,),
                                                   traversal_depth + 1)
        nodes, depth = memo[identifier]
        for _, (argument_nodes, argument_depth) in reversed(child_metrics):
            nodes += 1 + argument_nodes
            depth = max(1, 1 + argument_depth, 1 + depth)
    else:
        nodes = 1 + sum(metric[0] for _, metric in child_metrics)
        shell = _shell(ast, [(path, None) for path in paths])
        depth = _json_measure(shell)[2]
        depth = max([depth] + [len(path) + metric[1] for path, metric in child_metrics])
    if nodes > MAX_EXPANDED_AST_NODES:
        raise CallError("EXPANSION_NODE_LIMIT")
    if depth > obs.MAX_AST_DEPTH:
        raise CallError("EXPANSION_DEPTH_LIMIT")
    return nodes, depth


def _source_names(program):
    names = {p.name for f in program.registry.functions for p in f.params}
    stack = [program.entry.program] + [f.body for f in program.registry.functions if f.body is not None]
    while stack:
        ast = stack.pop()
        if ast["op"] in {"var", "let"}:
            names.add(ast["name"])
        stack.extend(_at(ast, path) for path in _children(ast))
    return names


def _generate_expansion(program, analysis):
    if not analysis.use.complete:
        raise CallError("BRIDGE_UNSUPPORTED", detail=";".join(analysis.use.reasons))
    functions = {f.stable_id: f for f in program.registry.functions}
    _expansion_metrics(program.entry.program, functions, {})
    used, bindings, serial = _source_names(program), [], 0

    def fresh():
        nonlocal serial
        name = "__call_" + str(serial)
        while name in used:
            serial += 1
            name = "__call_" + str(serial)
        used.add(name)
        serial += 1
        return name

    def lower(ast, env, path, active):
        op = ast["op"]
        if op == "var":
            return {"op": "var", "name": env[ast["name"]]}
        if op == "let":
            value = lower(ast["value"], env, path + ("value",), active)
            name = fresh()
            local = dict(env)
            local[ast["name"]] = name
            body = lower(ast["body"], local, path + ("body",), active)
            return {"op": "let", "name": name, "value": value, "body": body}
        if op == "call":
            # All argument ASTs retain the caller lexical environment.
            arguments = [lower(arg, env, path + ("args", i), active) for i, arg in enumerate(ast["args"])]
            function = functions[ast["target"]]
            if function.stable_id in active or len(active) >= MAX_CALL_DEPTH:
                raise CallError("BRIDGE_UNSUPPORTED")
            temporaries = tuple(fresh() for _ in function.params)
            bindings.append(ExpansionBinding(path, function.stable_id, function.definition_revision,
                                             tuple(p.name for p in function.params), temporaries))
            local = {p.name: name for p, name in zip(function.params, temporaries)}
            body = lower(function.body, local, path + ("callee", function.stable_id, "body"),
                         active + (function.stable_id,))
            for name, argument in reversed(tuple(zip(temporaries, arguments))):
                body = {"op": "let", "name": name, "value": argument, "body": body}
            return body
        return _shell(_plain(ast), [(child, lower(_at(ast, child), env, path + child, active))
                                    for child in _children(ast)])

    tree = lower(program.entry.program, {}, ("entry",), ())
    if obs.validate_program(tree, program.entry.compile_config) != analysis.result_type:
        raise CallError("EXPANSION_TYPE_MISMATCH")
    return Expansion(_expansion_context(program, analysis), tree, tuple(bindings))


def expand(program: Program) -> Expansion:
    return _generate_expansion(program, analyze(program))


def verify_expansion(program: Program, certificate: Expansion) -> VerifiedExpansion:
    analysis = analyze(program)
    if not isinstance(certificate, Expansion):
        raise CallError("MALFORMED_EXPANSION")
    if not _same(certificate.context, _expansion_context(program, analysis)):
        raise CallError("EXPANSION_CONTEXT_MISMATCH")
    reconstructed = _generate_expansion(program, analysis)
    if not _same(certificate.expanded_ast, reconstructed.expanded_ast):
        raise CallError("EXPANSION_AST_MISMATCH")
    if not _same(certificate.bindings, reconstructed.bindings):
        raise CallError("EXPANSION_BINDINGS_MISMATCH")
    entry = program.entry
    consumer = obs.Consumer(entry.stable_id, certificate.expanded_ast, entry.compile_config,
                            entry.provider_revision, entry.requirements, entry.alias)
    summary = obs.infer_use(consumer.program, consumer.compile_config)
    if summary != analysis.use:
        raise CallError("COMPOSITION_BRIDGE_MISMATCH")
    return VerifiedExpansion(certificate, consumer, summary)


def refined_bridge_use(program: Program, *, expansion: Expansion | None = None,
                       derivation: laws.Derivation | None = None) -> BridgeRefinement:
    checked = verify_expansion(program, expand(program) if expansion is None else expansion)
    refined = laws.refined_use(checked.consumer, derivation)
    return BridgeRefinement(checked.expansion, refined.derivation, refined.summary, refined.saturated)


def _requirements(before, after):
    old = {} if before is None else before.entry.requirements
    new = {} if after is None else after.entry.requirements
    return tuple(obs.RequirementReview(identifier,
                                       "REMOVAL_OPEN" if identifier not in new else
                                       "UNCHANGED_UNASSESSED" if old.get(identifier) == new[identifier] else "OPEN",
                                       old.get(identifier), new.get(identifier))
                 for identifier in sorted(set(old) | set(new)))


def _assessment(before, after, before_resource, after_resource, *, refined):
    if before is None and after is None:
        raise CallError("NO_CONSUMER_TO_ASSESS")
    if before is not None and after is not None and before.entry.stable_id != after.entry.stable_id:
        raise CallError("CONSUMER_ID_MISMATCH")
    old = None if before is None else analyze(before)
    new = None if after is None else analyze(after)
    combined = obs._merge(*(a.use for a in (old, new) if a is not None))
    delta = obs.exact_delta(before_resource, after_resource)
    requirements = _requirements(before, after)
    reasons = []
    changed = old is None or new is None or old.semantic_stamp != new.semantic_stamp
    if old is None:
        reasons.append("CONSUMER_ADDED")
    elif new is None:
        reasons.append("CONSUMER_REMOVED")
    else:
        for label, left, right in (
            ("PROGRAM_REVISION_CHANGED", before.entry.program_revision, after.entry.program_revision),
            ("COMPILE_CONFIG_CHANGED", obs.digest(before.entry.compile_config), obs.digest(after.entry.compile_config)),
            ("PROVIDER_REVISION_CHANGED", before.entry.provider_revision, after.entry.provider_revision),
            ("REQUIREMENTS_CHANGED", obs.digest(before.entry.requirements), obs.digest(after.entry.requirements)),
            ("CALL_CLOSURE_CHANGED", old.closure_stamp, new.closure_stamp)):
            if left != right:
                reasons.append(f"{label}:{left}->{right}")
    for review in requirements:
        if review.status in {"OPEN", "REMOVAL_OPEN"}:
            reasons.append("REQUIREMENT_" + review.status + ":" + review.requirement_id)
    basis = "r04_modular_composition"
    if refined and combined.complete and not changed:
        first, second = refined_bridge_use(before), refined_bridge_use(after)
        combined = obs._merge(first.summary, second.summary)
        basis = "r04_verified_expansion_r03"
        reasons.append("VERIFIED_EXPANSION:" + obs.digest(first.expansion))
        reasons.append("REPLAYED_DERIVATION:" + obs.digest(first.derivation))
    affected = combined.required_observations & delta.changed
    if not combined.complete:
        decision = "UNKNOWN"
        reasons.extend("INCOMPLETE_USE:" + reason for reason in combined.reasons)
    elif changed or affected:
        decision = "RECHECK"
        reasons.extend("REQUIRED_OBSERVATION_CHANGED:" + name for name in sorted(affected))
    else:
        decision = "EXCLUDED"
        reasons.append("ALL_REQUIRED_OBSERVATIONS_EQUAL")
    identifier = (after if after is not None else before).entry.stable_id
    return obs.Assessment(identifier, decision, tuple(reasons), delta.changed,
                          combined.required_observations, requirements, basis)


def assess(before: Program | None, after: Program | None,
           before_resource: ResourceState | None, after_resource: ResourceState | None) -> obs.Assessment:
    return _assessment(before, after, before_resource, after_resource, refined=False)


def assess_refined(before: Program | None, after: Program | None,
                   before_resource: ResourceState | None, after_resource: ResourceState | None) -> obs.Assessment:
    return _assessment(before, after, before_resource, after_resource, refined=True)


@dataclass(frozen=True)
class ProjectGraph:
    registry: Registry
    consumers: tuple[Consumer, ...]
    analyses: tuple[Analysis, ...]
    manifest_stamp: str

    def __post_init__(self):
        object.__setattr__(self, "consumers", tuple(self.consumers))
        object.__setattr__(self, "analyses", tuple(self.analyses))


def _consumers(consumers):
    if isinstance(consumers, Mapping):
        if len(consumers) > MAX_CONSUMERS:
            raise CallError("CONSUMER_LIMIT")
        for key, value in consumers.items():
            if not isinstance(value, Consumer) or key != value.stable_id:
                raise CallError("CONSUMER_KEY_MISMATCH")
        values = tuple(consumers.values())
    else:
        values = _limited_tuple(consumers, MAX_CONSUMERS, "CONSUMER_LIMIT")
    if not all(isinstance(c, Consumer) for c in values):
        raise CallError("INVALID_CONSUMER")
    if len({c.stable_id for c in values}) != len(values):
        raise CallError("DUPLICATE_CONSUMER_ID")
    return tuple(sorted(values, key=lambda c: c.stable_id))


def extract_project(registry: Registry, consumers: Mapping[str, Consumer] | Iterable[Consumer]) -> ProjectGraph:
    if not isinstance(registry, Registry):
        raise CallError("INVALID_REGISTRY")
    consumers = _consumers(consumers)
    analyses = tuple(analyze(Program(c, registry)) for c in consumers)
    # An empty consumer set still commits to the whole registry and context.
    manifest = obs.digest({"registry": registry.manifest_stamp,
                           "consumers": tuple((c.stable_id, c.input_stamp) for c in consumers),
                           "sources": _source_stamps()})
    return ProjectGraph(registry, consumers, analyses, manifest)


def _validated_graph(graph):
    if not isinstance(graph, ProjectGraph):
        raise CallError("PROJECT_GRAPH_MISMATCH")
    fresh = extract_project(graph.registry, graph.consumers)
    if not _same(graph, fresh):
        raise CallError("PROJECT_GRAPH_MISMATCH")
    return fresh


@dataclass(frozen=True)
class ReverseResult:
    target: str
    kind: str
    items: tuple[str, ...]
    complete: bool
    premise_stamp: str


def reverse_query(graph: ProjectGraph, target: str, *, kind: str = "function") -> ReverseResult:
    graph = _validated_graph(graph)
    _text(target, "$.target")
    if kind not in {"function", "resource"} or (kind == "resource" and target != obs.RESOURCE_ID):
        raise CallError("UNSUPPORTED_QUERY_TARGET")
    items = []
    for consumer, analysis in zip(graph.consumers, graph.analyses):
        matched = (any(b.target_id == target for b in analysis.closure) if kind == "function"
                   else bool(analysis.use.required_observations))
        if matched:
            items.append(consumer.stable_id)
    return ReverseResult(target, kind, tuple(items), all(a.use.complete for a in graph.analyses),
                         obs.digest({"manifest": graph.manifest_stamp, "target": target, "kind": kind}))


def assess_project(old: ProjectGraph, new: ProjectGraph,
                   before_resource: ResourceState | None, after_resource: ResourceState | None,
                   *, refined: bool = False) -> tuple[obs.Assessment, ...]:
    old, new = _validated_graph(old), _validated_graph(new)
    before, after = {c.stable_id: c for c in old.consumers}, {c.stable_id: c for c in new.consumers}
    function = assess_refined if refined else assess
    return tuple(function(None if identifier not in before else Program(before[identifier], old.registry),
                          None if identifier not in after else Program(after[identifier], new.registry),
                          before_resource, after_resource)
                 for identifier in sorted(set(before) | set(after)))
