"""R02 finite observation research AST, not a bagaev compiler or runtime.

Dependency summaries are inferred from the closed AST below. Resource deltas
are computed by actual observation functions on two concrete finite states.
The ordinary assessment API never accepts a caller-supplied use summary.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Callable


PROFILE_REVISION = "authorship-observation-profile/r02-v1"
EXTRACTOR_REVISION = "closed-ast-conservative-union/r02-v1"
RESOURCE_ID = "authorship"
OBSERVATIONS = ("ordered_members", "member_set", "count", "read_status")
MAX_AST_DEPTH = 128
MIN_INTEGER, MAX_INTEGER = -(2 ** 63), 2 ** 63 - 1


class ProfileError(ValueError):
    def __init__(self, code: str, path: str = "$", detail: str = ""):
        self.code, self.path, self.detail = code, path, detail
        super().__init__(f"{code} at {path}" + (f": {detail}" if detail else ""))


def to_data(value: Any) -> Any:
    """Canonical JSON-compatible public representation; sets retain their tag."""
    if is_dataclass(value):
        return {f.name: to_data(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {k: to_data(value[k]) for k in sorted(value)}
    if isinstance(value, (set, frozenset)):
        items = [to_data(v) for v in value]
        items.sort(key=lambda v: json.dumps(v, sort_keys=True, separators=(",", ":")))
        return {"$set": items}
    if isinstance(value, (list, tuple)):
        return [to_data(v) for v in value]
    return value


canonical = to_data


def digest(value: Any) -> str:
    payload = json.dumps(to_data(value), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _freeze_json(value: Any, path: str = "$", depth: int = 0) -> Any:
    if depth > MAX_AST_DEPTH:
        raise ProfileError("AST_DEPTH_LIMIT", path)
    if value is None or type(value) in (bool, int, str):
        if type(value) is str:
            _text(value, path, empty=True)
        elif type(value) is int:
            _integer(value, path)
        return value
    if isinstance(value, Mapping):
        if not all(type(k) is str for k in value):
            raise ProfileError("INVALID_JSON_KEY", path)
        for key in value:
            _text(key, path + ".<key>", empty=True)
        return MappingProxyType({k: _freeze_json(v, f"{path}.{k}", depth + 1) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(v, f"{path}[{i}]", depth + 1) for i, v in enumerate(value))
    raise ProfileError("NON_JSON_AST_VALUE", path, type(value).__name__)


def _text(value: Any, path: str, *, empty: bool = False) -> str:
    if type(value) is not str or (not empty and not value):
        raise ProfileError("EXPECTED_STRING", path)
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ProfileError("INVALID_UNICODE_SCALAR", path)
    return value


def _integer(value: int, path: str) -> int:
    if not MIN_INTEGER <= value <= MAX_INTEGER:
        raise ProfileError("INTEGER_OUT_OF_RANGE", path, "signed 64-bit integer required")
    return value


def _config(config: Mapping[str, bool] | None) -> Mapping[str, bool]:
    if config is not None and not isinstance(config, Mapping):
        raise ProfileError("INVALID_COMPILE_CONFIG")
    result = {} if config is None else dict(config)
    if not all(type(k) is str and k and type(v) is bool for k, v in result.items()):
        raise ProfileError("INVALID_COMPILE_CONFIG")
    for key in result:
        _text(key, "$.compile_config.<key>")
    return MappingProxyType(result)


@dataclass(frozen=True)
class Type:
    name: str
    args: tuple["Type", ...] = ()


BOOL, INT, STRING, UNIT = (Type(n) for n in ("bool", "int", "string", "unit"))
ORDERED, MEMBERS = Type("ordered_members"), Type("member_set")
_BASIC_TYPES = {t.name: t for t in (BOOL, INT, STRING, UNIT, ORDERED, MEMBERS)}


def _annotation(value: Any, path: str, depth: int = 0) -> Type:
    if depth > MAX_AST_DEPTH:
        raise ProfileError("TYPE_DEPTH_LIMIT", path)
    if type(value) is str and value in _BASIC_TYPES:
        return _BASIC_TYPES[value]
    if isinstance(value, Mapping) and set(value) == {"tuple"}:
        items = _items(value["tuple"], path + ".tuple")
        return Type("tuple", tuple(_annotation(v, f"{path}.tuple[{i}]", depth + 1) for i, v in enumerate(items)))
    raise ProfileError("UNSUPPORTED_TYPE", path)


@dataclass(frozen=True)
class ResourceState:
    members: tuple[str, ...]
    read_error: str | None = None

    def __post_init__(self):
        if not isinstance(self.members, (tuple, list)):
            raise ProfileError("INVALID_AUTHORSHIP_MEMBERS")
        members = tuple(self.members)
        if not all(type(v) is str and v for v in members):
            raise ProfileError("INVALID_AUTHOR_ID")
        for identifier in members:
            _text(identifier, "$.members")
        if len(set(members)) != len(members):
            raise ProfileError("DUPLICATE_AUTHOR_ID")
        if self.read_error is not None:
            _text(self.read_error, "$.read_error")
        object.__setattr__(self, "members", members)


def _resource(resource: ResourceState | None):
    if resource is not None and not isinstance(resource, ResourceState):
        raise ProfileError("INVALID_RESOURCE_STATE")


def _read_error(resource: ResourceState | None) -> str | None:
    return "MISSING_RESOURCE" if resource is None else resource.read_error


@dataclass(frozen=True)
class Observation:
    status: str
    value: Any = None
    error: str | None = None


def observe(resource: ResourceState | None, name: str) -> Observation:
    _resource(resource)
    if name not in OBSERVATIONS:
        raise ProfileError("UNKNOWN_OBSERVATION", detail=name)
    error = _read_error(resource)
    if name == "read_status":
        return Observation("ok", "ok" if error is None else "error:" + error)
    if error is not None:
        return Observation("error", error=error)
    if name == "ordered_members":
        value = resource.members
    elif name == "member_set":
        value = frozenset(resource.members)
    else:
        value = len(resource.members)
    return Observation("ok", value)


@dataclass(frozen=True)
class ObservationDelta:
    changed: frozenset[str]
    before: Mapping[str, Observation]
    after: Mapping[str, Observation]


def exact_delta(before: ResourceState | None, after: ResourceState | None) -> ObservationDelta:
    old = {name: observe(before, name) for name in OBSERVATIONS}
    new = {name: observe(after, name) for name in OBSERVATIONS}
    changed = frozenset(name for name in OBSERVATIONS if old[name] != new[name])
    return ObservationDelta(changed, MappingProxyType(old), MappingProxyType(new))


@dataclass(frozen=True)
class UseSummary:
    required_observations: frozenset[str] = frozenset()
    complete: bool = True
    may_errors: frozenset[str] = frozenset()
    effects: frozenset[str] = frozenset()
    config_keys: frozenset[str] = frozenset()
    reasons: tuple[str, ...] = ()


def _merge(*summaries: UseSummary) -> UseSummary:
    return UseSummary(
        frozenset().union(*(s.required_observations for s in summaries)),
        all(s.complete for s in summaries),
        frozenset().union(*(s.may_errors for s in summaries)),
        frozenset().union(*(s.effects for s in summaries)),
        frozenset().union(*(s.config_keys for s in summaries)),
        tuple(sorted({r for s in summaries for r in s.reasons})))


def _fields(ast: Any, required: tuple[str, ...], optional: tuple[str, ...] = (), path: str = "$"):
    if not isinstance(ast, Mapping):
        raise ProfileError("EXPECTED_AST_OBJECT", path)
    if not all(type(key) is str for key in ast):
        raise ProfileError("INVALID_JSON_KEY", path)
    for key in ast:
        _text(key, path + ".<key>", empty=True)
    missing = set(("op",) + required) - set(ast)
    extra = set(ast) - set(("op",) + required + optional)
    if missing:
        raise ProfileError("MISSING_AST_FIELD", path, ",".join(sorted(missing)))
    if extra:
        raise ProfileError("UNKNOWN_AST_FIELD", path, ",".join(sorted(extra)))


def _items(value: Any, path: str, *, nonempty: bool = False):
    if not isinstance(value, (list, tuple)) or (nonempty and not value):
        raise ProfileError("EXPECTED_AST_ARRAY", path)
    return value


def _expect(actual: Type, expected: Type | tuple[Type, ...], path: str):
    choices = expected if isinstance(expected, tuple) else (expected,)
    if actual not in choices:
        raise ProfileError("TYPE_MISMATCH", path,
                           f"got {actual}; expected {choices}")


def _analyze(ast: Any, env: Mapping[str, Type], config: Mapping[str, bool],
             path: str = "$", depth: int = 0) -> tuple[Type, UseSummary]:
    if depth > MAX_AST_DEPTH:
        raise ProfileError("AST_DEPTH_LIMIT", path)
    if not isinstance(ast, Mapping) or type(ast.get("op")) is not str:
        raise ProfileError("INVALID_AST_OPERATION", path)
    op = _text(ast["op"], path + ".op")
    def child(name: str, local_env=None):
        return _analyze(ast[name], env if local_env is None else local_env,
                        config, f"{path}.{name}", depth + 1)
    empty = UseSummary()
    if op == "const":
        _fields(ast, ("value",), path=path)
        value = ast["value"]
        kinds = {bool: BOOL, int: INT, str: STRING, type(None): UNIT}
        if type(value) not in kinds:
            raise ProfileError("INVALID_LITERAL_TYPE", path + ".value")
        if type(value) is str:
            _text(value, path + ".value", empty=True)
        elif type(value) is int:
            _integer(value, path + ".value")
        return kinds[type(value)], empty
    if op == "read":
        _fields(ast, ("view",), path=path)
        name = _text(ast["view"], path + ".view")
        types = {"ordered_members": ORDERED, "member_set": MEMBERS,
                 "count": INT, "read_status": STRING}
        if name not in types:
            raise ProfileError("UNSUPPORTED_RESOURCE_VIEW", path + ".view", name)
        observations = frozenset({name, "read_status"})
        errors = frozenset() if name == "read_status" else frozenset({"RESOURCE_READ_ERROR"})
        return types[name], UseSummary(observations, may_errors=errors)
    if op == "var":
        _fields(ast, ("name",), path=path)
        name = _text(ast["name"], path + ".name")
        if name not in env:
            raise ProfileError("UNBOUND_VARIABLE", path + ".name", name)
        return env[name], empty
    if op == "config":
        _fields(ast, ("key",), path=path)
        key = _text(ast["key"], path + ".key")
        if key not in config:
            raise ProfileError("MISSING_COMPILE_CONFIG", path + ".key", key)
        return BOOL, UseSummary(config_keys=frozenset({key}))
    if op == "let":
        _fields(ast, ("name", "value", "body"), path=path)
        name = _text(ast["name"], path + ".name")
        value_type, value_use = child("value")
        local_env = dict(env)
        local_env[name] = value_type
        body_type, body_use = child("body", local_env)
        return body_type, _merge(value_use, body_use)
    if op == "if":
        _fields(ast, ("condition", "then", "else"), path=path)
        condition_type, condition_use = child("condition")
        _expect(condition_type, BOOL, path + ".condition")
        then_type, then_use = child("then")
        else_type, else_use = child("else")
        _expect(else_type, then_type, path + ".else")
        return then_type, _merge(condition_use, then_use, else_use)
    if op in {"size", "to_set", "head"}:
        _fields(ast, ("value",), path=path)
        value_type, value_use = child("value")
        _expect(value_type, ORDERED if op == "head" else (ORDERED, MEMBERS), path + ".value")
        if op == "head":
            return STRING, _merge(value_use, UseSummary(may_errors=frozenset({"EMPTY_HEAD"})))
        # Deliberately no narrowing: size(read ordered) still requires order.
        return (INT if op == "size" else MEMBERS), value_use
    if op == "contains":
        _fields(ast, ("collection", "item"), path=path)
        collection_type, collection_use = child("collection")
        item_type, item_use = child("item")
        _expect(collection_type, (ORDERED, MEMBERS), path + ".collection")
        _expect(item_type, STRING, path + ".item")
        return BOOL, _merge(collection_use, item_use)
    if op in {"eq", "pair"}:
        _fields(ast, ("left", "right"), path=path)
        left_type, left_use = child("left")
        right_type, right_use = child("right")
        if op == "eq":
            _expect(right_type, left_type, path + ".right")
        return (BOOL if op == "eq" else Type("tuple", (left_type, right_type))), _merge(left_use, right_use)
    if op in {"tuple", "seq"}:
        _fields(ast, ("items",), path=path)
        items = _items(ast["items"], path + ".items", nonempty=op == "seq")
        parts = [_analyze(v, env, config, f"{path}.items[{i}]", depth + 1)
                 for i, v in enumerate(items)]
        output_type = parts[-1][0] if op == "seq" else Type("tuple", tuple(t for t, _ in parts))
        return output_type, _merge(*(s for _, s in parts))
    if op == "emit":
        _fields(ast, ("label", "value"), ("then",), path)
        label = _text(ast["label"], path + ".label")
        _, payload_use = child("value")
        then_type, then_use = child("then") if "then" in ast else (UNIT, empty)
        return then_type, _merge(payload_use, then_use, UseSummary(effects=frozenset({label})))
    if op == "fail":
        _fields(ast, ("code", "type"), path=path)
        code = _text(ast["code"], path + ".code")
        return _annotation(ast["type"], path + ".type"), UseSummary(may_errors=frozenset({code}))
    if op in {"opaque", "unknown"}:
        if op == "opaque":
            _fields(ast, ("name", "type"), ("kind", "args"), path)
            name = _text(ast["name"], path + ".name")
            kind = _text(ast.get("kind", "external"), path + ".kind")
            if kind not in {"external", "hidden_read"}:
                raise ProfileError("UNSUPPORTED_OPAQUE_KIND", path + ".kind")
            args = _items(ast.get("args", ()), path + ".args")
            uses = [_analyze(v, env, config, f"{path}.args[{i}]", depth + 1)[1]
                    for i, v in enumerate(args)]
            reason = f"OPAQUE_{kind.upper()}:{name}"
            unknown_use = UseSummary(complete=False, may_errors=frozenset({"*"}),
                                     effects=frozenset({"*"}), reasons=(reason,))
        else:
            _fields(ast, ("type",), ("reason",), path)
            reason = "RUNTIME_UNKNOWN:" + _text(ast.get("reason", "explicit"), path + ".reason")
            uses = []
            unknown_use = UseSummary(complete=False, reasons=(reason,))
        return _annotation(ast["type"], path + ".type"), _merge(*uses, unknown_use)
    raise ProfileError("UNSUPPORTED_AST_OPERATION", path + ".op", op)


def validate_program(ast: Mapping[str, Any], config: Mapping[str, bool] | None = None) -> Type:
    return _analyze(ast, {}, _config(config))[0]


def infer_use(ast: Mapping[str, Any], config: Mapping[str, bool] | None = None) -> UseSummary:
    return _analyze(ast, {}, _config(config))[1]


@dataclass(frozen=True)
class Effect:
    label: str
    value: Any


@dataclass(frozen=True)
class Execution:
    status: str
    value: Any = None
    error: str | None = None
    trace: tuple[Effect, ...] = ()
    complete: bool = True
    unknown_reason: str | None = None


class _RuntimeFault(Exception):
    pass


class _RuntimeUnknown(Exception):
    pass


def _evaluate(ast, resource, config, env, trace):
    op = ast["op"]
    def ev(name):
        return _evaluate(ast[name], resource, config, env, trace)
    if op == "const":
        return ast["value"]
    if op == "read":
        observed = observe(resource, ast["view"])
        if observed.status == "error":
            raise _RuntimeFault(observed.error)
        return observed.value
    if op == "var":
        return env[ast["name"]]
    if op == "config":
        return config[ast["key"]]
    if op == "let":
        value = ev("value")
        local_env = dict(env)
        local_env[ast["name"]] = value
        return _evaluate(ast["body"], resource, config, local_env, trace)
    if op == "if":
        return ev("then" if ev("condition") else "else")
    if op == "size":
        return len(ev("value"))
    if op == "to_set":
        return frozenset(ev("value"))
    if op == "head":
        values = ev("value")
        if not values:
            raise _RuntimeFault("EMPTY_HEAD")
        return values[0]
    if op == "contains":
        collection = ev("collection")
        return ev("item") in collection
    if op in {"eq", "pair"}:
        left, right = ev("left"), ev("right")
        return left == right if op == "eq" else (left, right)
    if op in {"tuple", "seq"}:
        values = [_evaluate(v, resource, config, env, trace) for v in ast["items"]]
        return tuple(values) if op == "tuple" else values[-1]
    if op == "emit":
        value = ev("value")
        trace.append(Effect(ast["label"], value))
        return ev("then") if "then" in ast else None
    if op == "fail":
        raise _RuntimeFault(ast["code"])
    if op == "opaque":
        for argument in ast.get("args", ()):
            _evaluate(argument, resource, config, env, trace)
        raise _RuntimeUnknown(f"OPAQUE_{ast.get('kind', 'external').upper()}:{ast['name']}")
    if op == "unknown":
        raise _RuntimeUnknown("RUNTIME_UNKNOWN:" + ast.get("reason", "explicit"))
    raise ProfileError("UNSUPPORTED_AST_OPERATION", detail=op)


def execute(ast: Mapping[str, Any], resource: ResourceState | None,
            config: Mapping[str, bool] | None = None) -> Execution:
    config = _config(config)
    validate_program(ast, config)
    _resource(resource)
    trace = []
    try:
        value = _evaluate(ast, resource, config, {}, trace)
        return Execution("ok", value, trace=tuple(trace))
    except _RuntimeFault as error:
        return Execution("error", error=str(error), trace=tuple(trace))
    except _RuntimeUnknown as unknown:
        return Execution("unknown", trace=tuple(trace), complete=False, unknown_reason=str(unknown))


@dataclass(frozen=True)
class Consumer:
    stable_id: str
    program: Mapping[str, Any]
    compile_config: Mapping[str, bool] = field(default_factory=dict)
    provider_revision: str = "provider/v1"
    requirements: Mapping[str, str] = field(default_factory=dict)
    alias: str = ""

    def __post_init__(self):
        _text(self.stable_id, "$.stable_id")
        _text(self.provider_revision, "$.provider_revision")
        _text(self.alias, "$.alias", empty=True)
        config = _config(self.compile_config)
        program = _freeze_json(self.program)
        validate_program(program, config)
        if not isinstance(self.requirements, Mapping):
            raise ProfileError("INVALID_REQUIREMENTS")
        requirements = dict(self.requirements)
        for identifier, revision in requirements.items():
            _text(identifier, "$.requirements.id")
            _text(revision, "$.requirements.revision")
        object.__setattr__(self, "program", program)
        object.__setattr__(self, "compile_config", config)
        object.__setattr__(self, "requirements", MappingProxyType(requirements))

    @property
    def program_revision(self) -> str:
        return digest(self.program)

    @property
    def input_stamp(self) -> str:
        return digest({"stable_id": self.stable_id, "program": self.program,
                       "config": self.compile_config, "provider": self.provider_revision,
                       "requirements": self.requirements, "profile": PROFILE_REVISION})


@dataclass(frozen=True)
class RequirementReview:
    requirement_id: str
    status: str
    before_revision: str | None
    after_revision: str | None


@dataclass(frozen=True)
class Assessment:
    consumer_id: str
    decision: str
    reasons: tuple[str, ...]
    changed_observations: frozenset[str]
    required_observations: frozenset[str]
    requirements: tuple[RequirementReview, ...]
    basis: str = "automatic_ast_inference"


def _assess(before, after, before_resource, after_resource, infer_fn, basis):
    if before is None and after is None:
        raise ProfileError("NO_CONSUMER_TO_ASSESS")
    if before is not None and after is not None and before.stable_id != after.stable_id:
        raise ProfileError("CONSUMER_ID_MISMATCH")
    consumer_id = (after if after is not None else before).stable_id
    delta = exact_delta(before_resource, after_resource)
    summaries = [infer_fn(c.program, c.compile_config) for c in (before, after) if c is not None]
    if not all(isinstance(summary, UseSummary) for summary in summaries):
        raise ProfileError("INVALID_USE_SUMMARY")
    combined = _merge(*summaries)
    old_requirements = {} if before is None else before.requirements
    new_requirements = {} if after is None else after.requirements
    requirements = tuple(RequirementReview(
        identifier,
        "REMOVAL_OPEN" if identifier not in new_requirements else
        "UNCHANGED_UNASSESSED" if old_requirements.get(identifier) == new_requirements[identifier]
        else "OPEN",
        old_requirements.get(identifier), new_requirements.get(identifier))
        for identifier in sorted(set(old_requirements) | set(new_requirements)))
    reasons = []
    structural_change = before is None or after is None
    if before is None:
        reasons.append("CONSUMER_ADDED")
    elif after is None:
        reasons.append("CONSUMER_REMOVED")
    else:
        changes = (
            ("PROGRAM_REVISION_CHANGED", before.program_revision, after.program_revision),
            ("COMPILE_CONFIG_CHANGED", digest(before.compile_config), digest(after.compile_config)),
            ("PROVIDER_REVISION_CHANGED", before.provider_revision, after.provider_revision),
            ("REQUIREMENTS_CHANGED", digest(before.requirements), digest(after.requirements)))
        for label, old, new in changes:
            if old != new:
                structural_change = True
                reasons.append(f"{label}:{old}->{new}")
    reasons.extend("REQUIREMENT_OPEN:" + r.requirement_id for r in requirements if r.status == "OPEN")
    reasons.extend("REQUIREMENT_REMOVAL_OPEN:" + r.requirement_id
                   for r in requirements if r.status == "REMOVAL_OPEN")
    affected = combined.required_observations & delta.changed
    reasons.extend("REQUIRED_OBSERVATION_CHANGED:" + name for name in sorted(affected))
    if not combined.complete:
        decision = "UNKNOWN"
        reasons.extend("INCOMPLETE_USE:" + reason for reason in combined.reasons)
        if not combined.reasons:
            reasons.append("INCOMPLETE_USE")
    elif structural_change or affected:
        decision = "RECHECK"
    else:
        decision = "EXCLUDED"
        reasons.append("ALL_REQUIRED_OBSERVATIONS_EQUAL")
    return Assessment(consumer_id, decision, tuple(reasons), delta.changed,
                      combined.required_observations, requirements, basis)


def assess(before: Consumer | None, after: Consumer | None,
           before_resource: ResourceState | None, after_resource: ResourceState | None) -> Assessment:
    return _assess(before, after, before_resource, after_resource,
                   infer_use, "automatic_ast_inference")


def assess_with_test_analyzer(before: Consumer | None, after: Consumer | None,
                             before_resource: ResourceState | None, after_resource: ResourceState | None,
                             *, infer_fn: Callable) -> Assessment:
    """Mutation-test seam only. Its output is explicitly untrusted, never normal evidence."""
    return _assess(before, after, before_resource, after_resource,
                   infer_fn, "TEST_ONLY_UNTRUSTED")


@dataclass(frozen=True, order=True)
class Edge:
    source: str
    target: str | None
    observation: str


@dataclass(frozen=True)
class ProjectGraph:
    manifest_stamp: str
    generation: str
    consumers: tuple[Consumer, ...]
    summaries: tuple[tuple[str, UseSummary], ...]
    edges: tuple[Edge, ...]
    unknown_consumers: tuple[str, ...]
    extractor_revision: str = EXTRACTOR_REVISION
    reused: tuple[str, ...] = ()
    reextracted: tuple[str, ...] = ()


def _project(project: Mapping[str, Consumer] | Iterable[Consumer]) -> tuple[Consumer, ...]:
    if isinstance(project, Mapping):
        for identifier, consumer in project.items():
            if not isinstance(consumer, Consumer) or identifier != consumer.stable_id:
                raise ProfileError("PROJECT_REGISTRY_ID_MISMATCH")
        consumers = tuple(project.values())
    else:
        consumers = tuple(project)
    if not all(isinstance(c, Consumer) for c in consumers):
        raise ProfileError("INVALID_PROJECT_CONSUMER")
    if len({c.stable_id for c in consumers}) != len(consumers):
        raise ProfileError("DUPLICATE_CONSUMER_ID")
    return tuple(sorted(consumers, key=lambda c: c.stable_id))


def _edge_key(edge: Edge):
    return edge.source, "" if edge.target is None else edge.target, edge.observation


def _build_graph(consumers, summaries, reused=(), reextracted=()) -> ProjectGraph:
    manifest = digest({"consumers": consumers, "profile": PROFILE_REVISION,
                       "extractor": EXTRACTOR_REVISION})
    generation = digest({"manifest": manifest, "extractor": EXTRACTOR_REVISION})
    edges, unknown = [], []
    for identifier, summary in summaries:
        edges.extend(Edge(identifier, RESOURCE_ID, name) for name in sorted(summary.required_observations))
        if not summary.complete:
            unknown.append(identifier)
            edges.append(Edge(identifier, None, "TOP"))
    return ProjectGraph(manifest, generation, tuple(consumers), tuple(summaries),
                        tuple(sorted(edges, key=_edge_key)), tuple(unknown),
                        extractor_revision=EXTRACTOR_REVISION,
                        reused=tuple(reused), reextracted=tuple(reextracted))


def extract_project(project: Mapping[str, Consumer] | Iterable[Consumer]) -> ProjectGraph:
    consumers = _project(project)
    summaries = tuple((c.stable_id, infer_use(c.program, c.compile_config)) for c in consumers)
    return _build_graph(consumers, summaries, reextracted=tuple(c.stable_id for c in consumers))


def graph_content(graph: ProjectGraph) -> dict:
    """Semantic graph content, excluding cache-work accounting."""
    return {f.name: to_data(getattr(graph, f.name)) for f in fields(graph)
            if f.name not in {"reused", "reextracted"}}


def validate_graph(graph: ProjectGraph):
    if not isinstance(graph, ProjectGraph):
        raise ProfileError("INVALID_PROJECT_GRAPH")
    if graph.extractor_revision != EXTRACTOR_REVISION:
        raise ProfileError("EXTRACTOR_REVISION_MISMATCH")
    expected = extract_project(graph.consumers)
    if graph_content(graph) != graph_content(expected):
        raise ProfileError("GRAPH_CONTENT_MISMATCH")


def incremental_extract(previous: ProjectGraph,
                        project: Mapping[str, Consumer] | Iterable[Consumer]) -> ProjectGraph:
    # This baseline revalidates previous contents by full extraction. Reuse is
    # modeled explicitly, but this implementation makes no speed claim.
    validate_graph(previous)
    consumers = _project(project)
    old = {c.stable_id: c for c in previous.consumers}
    old_summaries = dict(previous.summaries)
    summaries, reused, extracted = [], [], []
    for consumer in consumers:
        identifier = consumer.stable_id
        if identifier in old and consumer.input_stamp == old[identifier].input_stamp:
            summary = old_summaries[identifier]
            reused.append(identifier)
        else:
            summary = infer_use(consumer.program, consumer.compile_config)
            extracted.append(identifier)
        summaries.append((identifier, summary))
    return _build_graph(consumers, summaries, reused, extracted)


@dataclass(frozen=True)
class ReverseResult:
    consumers: tuple[str, ...]
    complete: bool
    manifest_stamp: str


def reverse_query(graph: ProjectGraph, target: str = RESOURCE_ID) -> ReverseResult:
    validate_graph(graph)
    if target != RESOURCE_ID:
        raise ProfileError("UNSUPPORTED_QUERY_RESOURCE", detail=target)
    consumers = tuple(sorted({e.source for e in graph.edges if e.target in {target, None}}))
    return ReverseResult(consumers, not graph.unknown_consumers, graph.manifest_stamp)


@dataclass(frozen=True)
class GraphDelta:
    added: tuple[Edge, ...]
    removed: tuple[Edge, ...]
    union: tuple[Edge, ...]
    old_generation: str
    new_generation: str


def graph_delta(old: ProjectGraph, new: ProjectGraph) -> GraphDelta:
    validate_graph(old)
    validate_graph(new)
    before, after = set(old.edges), set(new.edges)
    ordered = lambda edges: tuple(sorted(edges, key=_edge_key))
    return GraphDelta(ordered(after - before), ordered(before - after),
                      ordered(before | after), old.generation, new.generation)


def assess_project(old: ProjectGraph, new: ProjectGraph,
                   before_resource: ResourceState | None,
                   after_resource: ResourceState | None) -> tuple[Assessment, ...]:
    validate_graph(old)
    validate_graph(new)
    before, after = ({c.stable_id: c for c in graph.consumers} for graph in (old, new))
    return tuple(assess(before.get(identifier), after.get(identifier), before_resource, after_resource)
                 for identifier in sorted(set(before) | set(after)))
