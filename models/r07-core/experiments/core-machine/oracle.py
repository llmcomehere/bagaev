"""Independent, finite-profile derivation evaluator for CORE-0.1.

This module imports neither the CEK engine nor earlier research interpreters.
Evaluation uses pending derivation goals and value slots.  Each goal performs
one action from the published charge table.  It is not a second typechecker:
the verifier gives it independently authored, accepted programs.  Invalid
fixtures cause OracleError, never a fabricated language result.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Mapping


PROFILE_REVISION = "core-machine/r06-v1"
PRIMITIVE_REVISION = "core-i64/r06-v1"
MIN_I64 = -(2 ** 63)
MAX_I64 = 2 ** 63 - 1


class OracleError(ValueError):
    """A broken assumption of this independently implemented test oracle."""


def copied(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def artifact_digest(program: Mapping[str, Any]) -> str:
    program = dict(program)
    program.setdefault("profile_revision", PROFILE_REVISION)
    preimage = {
        "profile_revision": PROFILE_REVISION,
        "primitive_revision": PRIMITIVE_REVISION,
        "program": program,
    }
    text = json.dumps(preimage, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    return sha256(text.encode("utf-8")).hexdigest()


def substitute(annotation: Any, bindings: Mapping[str, Any]) -> Any:
    """Independent structural substitution, only over the closed type grammar."""
    if isinstance(annotation, str):
        return annotation
    tag = annotation["tag"]
    if tag == "var":
        if annotation["id"] not in bindings:
            raise OracleError("uninstantiated runtime type variable")
        return copied(bindings[annotation["id"]])
    if tag == "fn":
        return {"tag": "fn",
                "params": [substitute(t, bindings) for t in annotation["params"]],
                "result": substitute(annotation["result"], bindings)}
    if tag == "result":
        return {"tag": "result", "ok": substitute(annotation["ok"], bindings)}
    raise OracleError("type outside oracle grammar")


def immutable(bindings: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(bindings))


@dataclass(frozen=True)
class Data:
    type: Any
    value: Any


@dataclass(frozen=True)
class Result:
    type: Any
    tag: str
    payload: Any


@dataclass(frozen=True)
class Group:
    node: Mapping[str, Any]
    captured: Mapping[str, Any]
    type_environment: Mapping[str, Any]


@dataclass(frozen=True)
class Scheme:
    group: Group
    member: int


@dataclass(frozen=True)
class Function:
    type: Any
    definition: Mapping[str, Any]
    captured: Mapping[str, Any]
    type_environment: Mapping[str, Any]
    code_node: str
    member: int | None = None
    group: Group | None = None


def instantiate(scheme: Scheme, arguments: list[Any]) -> Function:
    group = scheme.group
    variables = group.node["type_params"]
    if len(arguments) != len(variables):
        raise OracleError("generic fixture arity")
    types = dict(group.type_environment)
    types.update(zip(variables, arguments))
    definition = group.node["functions"][scheme.member]
    signature = {
        "tag": "fn", "params": [p["type"] for p in definition["params"]],
        "result": definition["result_type"],
    }
    return Function(substitute(signature, types), definition, group.captured,
                    immutable(types), group.node["nid"], scheme.member, group)


def observe(value: Any, content_digest: str) -> dict[str, Any]:
    if isinstance(value, Data):
        return {"type": copied(value.type), "value": value.value}
    if isinstance(value, Result):
        return {"type": copied(value.type), "tag": value.tag,
                "value": observe(value.payload, content_digest)}
    if isinstance(value, Function):
        return {"type": copied(value.type), "kind": "Function",
                "code": {"content_digest": content_digest,
                         "node_id": value.code_node, "member": value.member}}
    raise OracleError("unobservable oracle value")


def primitive(name: str, operands: list[Any]) -> Any:
    if len(operands) != 2 or any(not isinstance(x, Data) or x.type != "Int64"
                                 for x in operands):
        raise OracleError("primitive fixture not typed")
    a, b = (x.value for x in operands)
    if name == "i64.eq":
        return Data("Bool", a == b)
    if name == "i64.lt":
        return Data("Bool", a < b)
    result_type = {"tag": "result", "ok": "Int64"}
    if name in {"i64.div", "i64.rem"} and b == 0:
        return Result(result_type, "Err", Data("ArithmeticError", "DivisionByZero"))
    if name == "i64.add":
        answer = a + b
    elif name == "i64.sub":
        answer = a - b
    elif name in {"i64.div", "i64.rem"}:
        # Exact integer arithmetic, independently avoiding host floor division
        # for signed operands and avoiding float conversion at Int64 limits.
        magnitude = abs(a) // abs(b)
        quotient = -magnitude if (a < 0) != (b < 0) else magnitude
        answer = quotient if name == "i64.div" else a - quotient * b
    else:
        raise OracleError("unknown primitive in fixture")
    if answer < MIN_I64 or answer > MAX_I64:
        return Result(result_type, "Err", Data("ArithmeticError", "Overflow"))
    return Result(result_type, "Ok", Data("Int64", answer))


@dataclass(frozen=True)
class Goal:
    """A derivation premise or combination; no imported control/K representation."""
    action: str
    node: Mapping[str, Any]
    environment: Mapping[str, Any]
    type_environment: Mapping[str, Any]
    output: int
    details: tuple[Any, ...] = ()


class Derivation:
    def __init__(self, program: Mapping[str, Any]):
        self.program = copied(program)
        self.content_digest = artifact_digest(self.program)
        self.slots: dict[int, Any] = {}
        self.next_slot = 1
        self.goals = [Goal("evaluate", self.program["entry"], immutable({}),
                           immutable({}), 0)]

    def slot(self) -> int:
        result = self.next_slot
        self.next_slot += 1
        return result

    def evaluate(self, node: Mapping[str, Any], environment: Mapping[str, Any],
                 types: Mapping[str, Any], output: int) -> None:
        self.goals.append(Goal("evaluate", node, environment, types, output))

    def await_value(self, action: str, parent: Goal, child: Mapping[str, Any],
                    details: tuple[Any, ...] = ()) -> None:
        child_slot = self.slot()
        self.goals.append(Goal(action, parent.node, parent.environment,
                               parent.type_environment, parent.output,
                               (child_slot,) + details))
        self.evaluate(child, parent.environment, parent.type_environment, child_slot)

    def invoke(self, function: Any, arguments: list[Any], output: int) -> None:
        if not isinstance(function, Function):
            raise OracleError("call of nonfunction")
        definition = function.definition
        if len(arguments) != len(definition["params"]):
            raise OracleError("call fixture arity")
        lexical = dict(function.captured)
        if function.group is not None:
            group = function.group
            exact_arguments = [function.type_environment[t] for t in group.node["type_params"]]
            for index, member in enumerate(group.node["functions"]):
                lexical[member["binder"]] = instantiate(Scheme(group, index), exact_arguments)
        lexical.update((p["binder"], value)
                       for p, value in zip(definition["params"], arguments))
        self.evaluate(definition["body"], immutable(lexical),
                      function.type_environment, output)

    def advance(self) -> tuple[str, str]:
        goal = self.goals.pop()
        node, env, types, out = (goal.node, goal.environment,
                                 goal.type_environment, goal.output)
        action = goal.action
        if action == "evaluate":
            op = node["op"]
            if op == "const":
                self.slots[out] = Data(substitute(node["type"], types), node["value"])
                rule = "CONST"
            elif op == "var":
                value = env[node["binder"]]
                arguments = [substitute(t, types) for t in node["type_args"]]
                if isinstance(value, Scheme):
                    value = instantiate(value, arguments)
                elif arguments:
                    raise OracleError("type arguments on monomorphic fixture binding")
                self.slots[out] = value
                rule = "VAR"
            elif op == "lambda":
                signature = {"tag": "fn", "params": [p["type"] for p in node["params"]],
                             "result": node["result_type"]}
                self.slots[out] = Function(substitute(signature, types), node, env,
                                           types, node["nid"])
                rule = "LAMBDA"
            elif op == "let":
                self.await_value("bind", goal, node["value"])
                rule = "LET_ENTER"
            elif op == "if":
                self.await_value("branch", goal, node["condition"])
                rule = "IF_ENTER"
            elif op == "letrec":
                group = Group(node, env, types)
                lexical = dict(env)
                for index, definition in enumerate(node["functions"]):
                    lexical[definition["binder"]] = Scheme(group, index)
                self.evaluate(node["body"], immutable(lexical), types, out)
                rule = "LETREC"
            elif op == "call":
                self.await_value("call_function", goal, node["fn"])
                rule = "CALL_ENTER"
            elif op == "prim":
                self.await_value("primitive_argument", goal, node["args"][0], (0, ()))
                rule = "PRIM_ENTER"
            elif op == "result":
                self.await_value("wrap", goal, node["value"])
                rule = "RESULT_ENTER"
            elif op == "match_result":
                self.await_value("match", goal, node["value"])
                rule = "MATCH_ENTER"
            else:
                raise OracleError("form outside independent oracle grammar")
        elif action == "bind":
            lexical = dict(env)
            lexical[node["binder"]] = self.slots[goal.details[0]]
            self.evaluate(node["body"], immutable(lexical), types, out)
            rule = "LET_BIND"
        elif action == "branch":
            condition = self.slots[goal.details[0]]
            if not isinstance(condition, Data) or condition.type != "Bool":
                raise OracleError("if fixture condition not Bool")
            branch = "then" if condition.value else "else"
            self.evaluate(node[branch], env, types, out)
            rule = "IF_THEN" if condition.value else "IF_ELSE"
        elif action == "call_function":
            function = self.slots[goal.details[0]]
            if node["args"]:
                self.await_value("call_argument", goal, node["args"][0],
                                 (function, 0, ()))
                rule = "CALL_ARGS"
            else:
                self.invoke(function, [], out)
                rule = "CALL_BODY"
        elif action == "call_argument":
            argument_slot, function, index, previous = goal.details
            arguments = previous + (self.slots[argument_slot],)
            if index + 1 < len(node["args"]):
                self.await_value("call_argument", goal, node["args"][index + 1],
                                 (function, index + 1, arguments))
                rule = "CALL_NEXT"
            else:
                self.invoke(function, list(arguments), out)
                rule = "CALL_BODY"
        elif action == "primitive_argument":
            argument_slot, index, previous = goal.details
            arguments = previous + (self.slots[argument_slot],)
            if index + 1 < len(node["args"]):
                self.await_value("primitive_argument", goal, node["args"][index + 1],
                                 (index + 1, arguments))
                rule = "PRIM_NEXT"
            else:
                self.slots[out] = primitive(node["name"], list(arguments))
                rule = "PRIM_APPLY"
        elif action == "wrap":
            self.slots[out] = Result({"tag": "result", "ok": substitute(node["ok_type"], types)},
                                     node["tag"], self.slots[goal.details[0]])
            rule = "RESULT_WRAP"
        elif action == "match":
            result = self.slots[goal.details[0]]
            if not isinstance(result, Result):
                raise OracleError("match fixture not Result")
            arm = "ok" if result.tag == "Ok" else "err"
            lexical = dict(env)
            lexical[node[arm + "_binder"]] = result.payload
            self.evaluate(node[arm + "_body"], immutable(lexical), types, out)
            rule = "MATCH_OK" if result.tag == "Ok" else "MATCH_ERR"
        else:
            raise OracleError("unknown derivation goal")
        return rule, node["nid"]


def run(program: Mapping[str, Any], budget: int, *, cancel_at: int | None = None,
        cancel_request_id: str = "cancel") -> dict[str, Any]:
    """Execute accepted fixture IR, comparing the entire public data observation.

    This oracle deliberately does not model physical heap/continuation/type
    allocation limits.  The conformance matrix stays below them.  Such guards
    are checked separately against manually specified ImplementationStop cases.
    """
    if type(budget) is not int or budget < 0:
        raise OracleError("invalid oracle budget")
    if cancel_at is not None and (type(cancel_at) is not int or cancel_at < 0):
        raise OracleError("invalid oracle cancellation")
    machine = Derivation(program)
    trace: list[dict[str, Any]] = []
    remaining = budget
    while True:
        # Completion is a property of the derivation, not a charged RETURN goal.
        if not machine.goals:
            termination, code = "RETURNED", "RETURNED"
            value = observe(machine.slots[0], machine.content_digest)
            cancellation = None
            break
        if cancel_at is not None and len(trace) >= cancel_at:
            termination, code, value = "SEMANTIC_STOP", "CANCELLED", None
            cancellation = cancel_request_id
            break
        if remaining == 0:
            termination, code, value = "SEMANTIC_STOP", "BUDGET_EXCEEDED", None
            cancellation = None
            break
        rule, node_id = machine.advance()
        remaining -= 1
        trace.append({"step_index": len(trace) + 1, "rule": rule, "node_id": node_id})
    return {
        "profile_revision": PROFILE_REVISION,
        "content_digest": machine.content_digest,
        "termination": termination, "code": code, "value": value,
        "steps": len(trace), "remaining": remaining, "trace": trace,
        "cancel_request_id": cancellation,
    }
