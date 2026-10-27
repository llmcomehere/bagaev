"""Independent interpreter for the finite R02 research AST.

This module deliberately does not import engine.py. Its inputs are JSON-shaped
programs, resource specifications, and fixed configuration dictionaries. It is
an executable oracle on a declared finite domain, not a proof about bagaev.
"""
from __future__ import annotations

from dataclasses import dataclass


class OracleInputError(ValueError):
    pass


class _ProgramError(Exception):
    pass


class _UnknownExecution(Exception):
    pass


@dataclass(frozen=True)
class Execution:
    status: str
    value: object = None
    error: str | None = None
    trace: tuple = ()
    complete: bool = True


def json_value(value):
    if isinstance(value, (set, frozenset)):
        return {"$set": sorted(json_value(x) for x in value)}
    if isinstance(value, (tuple, list)):
        return [json_value(x) for x in value]
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in sorted(value.items())}
    return value


def observations(result: Execution):
    """The complete visible trace of this research semantics."""
    return {"status": result.status, "value": json_value(result.value),
            "error": result.error, "trace": json_value(result.trace),
            "complete": result.complete}


def _resource(spec):
    if spec is None:
        return (), "MISSING_RESOURCE"
    if not isinstance(spec, dict) or "members" not in spec:
        raise OracleInputError("RESOURCE_SPEC")
    members = spec["members"]
    if not isinstance(members, (list, tuple)) or any(type(x) is not str for x in members):
        raise OracleInputError("RESOURCE_MEMBERS")
    if len(set(members)) != len(members):
        raise OracleInputError("DUPLICATE_AUTHOR")
    error = spec.get("read_error")
    if error is not None and type(error) is not str:
        raise OracleInputError("RESOURCE_ERROR")
    return tuple(members), error


def resource_observations(spec):
    members, error = _resource(spec)
    status = "ok" if error is None else "error:" + error
    values = {"ordered_members": members, "member_set": frozenset(members),
              "count": len(members)}
    return {**{name: ("error", error) if error is not None else ("ok", value)
               for name, value in values.items()}, "read_status": status}


def changed_observations(before, after):
    left, right = resource_observations(before), resource_observations(after)
    return frozenset(name for name in left if left[name] != right[name])


def execute(program: dict, resource_spec, config=None) -> Execution:
    members, resource_error = _resource(resource_spec)
    configuration = dict(config or {})
    effects = []

    def evaluate(node, environment):
        op = node["op"]
        if op == "const":
            return node["value"]
        if op == "read":
            view = node["view"]
            if view == "read_status":
                return "ok" if resource_error is None else "error:" + resource_error
            if resource_error is not None:
                raise _ProgramError(resource_error)
            if view == "ordered_members":
                return members
            if view == "member_set":
                return frozenset(members)
            if view == "count":
                return len(members)
            raise OracleInputError("UNKNOWN_VIEW")
        if op == "var":
            if node["name"] not in environment:
                raise OracleInputError("UNBOUND_VARIABLE")
            return environment[node["name"]]
        if op == "config":
            key = node["key"]
            if key not in configuration or type(configuration[key]) is not bool:
                raise OracleInputError("CONFIG_BOOL_REQUIRED")
            return configuration[key]
        if op == "let":
            value = evaluate(node["value"], environment)
            inner = dict(environment)
            inner[node["name"]] = value
            return evaluate(node["body"], inner)
        if op == "if":
            condition = evaluate(node["condition"], environment)
            if type(condition) is not bool:
                raise OracleInputError("CONDITION_BOOL_REQUIRED")
            return evaluate(node["then"] if condition else node["else"], environment)
        if op == "contains":
            collection = evaluate(node["collection"], environment)
            item = evaluate(node["item"], environment)
            return item in collection
        if op == "size":
            return len(evaluate(node["value"], environment))
        if op == "to_set":
            return frozenset(evaluate(node["value"], environment))
        if op == "head":
            value = evaluate(node["value"], environment)
            if len(value) == 0:
                raise _ProgramError("EMPTY_HEAD")
            return value[0]
        if op == "eq":
            left = evaluate(node["left"], environment)
            right = evaluate(node["right"], environment)
            return left == right
        if op == "pair":
            left = evaluate(node["left"], environment)
            right = evaluate(node["right"], environment)
            return left, right
        if op == "tuple":
            return tuple(evaluate(item, environment) for item in node["items"])
        if op == "seq":
            if not node["items"]:
                raise OracleInputError("EMPTY_SEQUENCE")
            value = None
            for item in node["items"]:
                value = evaluate(item, environment)
            return value
        if op == "emit":
            value = evaluate(node["value"], environment)
            effects.append({"label": node["label"], "value": value})
            return evaluate(node["then"], environment) if "then" in node else None
        if op == "fail":
            raise _ProgramError(node["code"])
        if op == "opaque":
            for arg in node.get("args", ()):
                evaluate(arg, environment)
            raise _UnknownExecution(node.get("name", "opaque"))
        if op == "unknown":
            raise _UnknownExecution(node.get("reason", "unknown"))
        raise OracleInputError("UNKNOWN_AST_OPERATION:" + str(op))

    try:
        value = evaluate(program, {})
        return Execution("ok", value, trace=tuple(effects))
    except _ProgramError as error:
        return Execution("error", error=str(error), trace=tuple(effects))
    except _UnknownExecution:
        return Execution("unknown", trace=tuple(effects), complete=False)
