#!/usr/bin/env python3
"""Reference interpreter and CLI for the bounded bagaev L0 prototype."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROGRAM_SCHEMA = "bagaev/l0-program/v1"
PATCH_SCHEMA = "bagaev/l0-patch/v1"
RESULT_SCHEMA = "bagaev/l0-result/v1"

MAX_JSON_BYTES = 1024 * 1024
MAX_NODES = 256
MAX_CONCAT_ITEMS = 32
MAX_STRING_BYTES = 4096
MAX_LIST_ITEMS = 256
INT_MIN = -(2**63)
INT_MAX = 2**63 - 1

TYPES = frozenset({"int", "bool", "string", "string_list"})
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,63}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")

OP_FIELDS = {
    "input": frozenset({"id", "op", "name", "type"}),
    "literal": frozenset({"id", "op", "type", "value"}),
    "identity": frozenset({"id", "op", "value"}),
    "list.concat": frozenset({"id", "op", "items"}),
    "list.unique": frozenset({"id", "op", "value"}),
    "list.sort": frozenset({"id", "op", "value"}),
    "list.length": frozenset({"id", "op", "value"}),
    "int.add": frozenset({"id", "op", "left", "right"}),
    "int.equal": frozenset({"id", "op", "left", "right"}),
    "bool.not": frozenset({"id", "op", "value"}),
}


class L0Error(ValueError):
    """A deterministic rejection with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Node:
    node_id: str
    op: str
    args: dict[str, Any]
    references: tuple[str, ...]


@dataclass(frozen=True)
class CompiledProgram:
    digest: str
    canonical_json: bytes
    nodes: dict[str, Node]
    order: tuple[str, ...]
    types: dict[str, str]
    inputs: tuple[tuple[str, str, str], ...]
    result_id: str

    @property
    def result_type(self) -> str:
        return self.types[self.result_id]

    def document(self) -> dict[str, Any]:
        return json.loads(self.canonical_json.decode("utf-8"))


def _reject(code: str, message: str) -> None:
    raise L0Error(code, message)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _reject("json.duplicate_key", f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _parse_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > 19:
        _reject("integer.overflow", "JSON integer is outside signed 64-bit range")
    parsed = int(value)
    if parsed < INT_MIN or parsed > INT_MAX:
        _reject("integer.overflow", "JSON integer is outside signed 64-bit range")
    return parsed


def loads_json(data: bytes | str) -> Any:
    """Load bounded JSON and reject duplicate keys and non-JSON constants."""
    if isinstance(data, str):
        try:
            encoded = data.encode("utf-8")
        except UnicodeEncodeError:
            _reject("json.encoding", "JSON input is not valid UTF-8 text")
    elif isinstance(data, bytes):
        encoded = data
    else:
        _reject("json.type", "JSON input must be bytes or text")
    if len(encoded) > MAX_JSON_BYTES:
        _reject("limit.json_bytes", "JSON input exceeds 1048576 bytes")
    try:
        text = encoded.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=lambda _value: _reject("json.constant", "non-JSON numeric constant"),
            parse_int=_parse_integer,
        )
    except L0Error:
        raise
    except UnicodeDecodeError:
        _reject("json.encoding", "JSON input is not valid UTF-8 text")
    except (json.JSONDecodeError, RecursionError, ValueError):
        _reject("json.syntax", "invalid JSON document")


def load_json_file(path: Path) -> Any:
    with path.open("rb") as stream:
        return loads_json(stream.read(MAX_JSON_BYTES + 1))


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _reject("structure.object", f"{context} must be an object")
    return value


def _fields(value: dict[str, Any], expected: frozenset[str], context: str) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    if missing:
        _reject("structure.missing_field", f"{context} is missing field {missing[0]!r}")
    unknown = sorted(actual - expected)
    if unknown:
        _reject("structure.unknown_field", f"{context} has unknown field {unknown[0]!r}")


def _identifier(value: Any, context: str) -> str:
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        _reject("identifier.invalid", f"{context} must match {IDENTIFIER.pattern}")
    return value


def _type_name(value: Any, context: str) -> str:
    if not isinstance(value, str) or value not in TYPES:
        _reject("type.unknown", f"{context} has an unknown type")
    return value


def _reference(value: Any, context: str) -> str:
    reference = _object(value, context)
    _fields(reference, frozenset({"ref"}), context)
    return _identifier(reference["ref"], f"{context}.ref")


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        _reject("value.type", f"{context} must be a string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        _reject("value.string", f"{context} contains an invalid Unicode scalar value")
    if size > MAX_STRING_BYTES:
        _reject("limit.string", f"{context} exceeds {MAX_STRING_BYTES} UTF-8 bytes")
    return value


def _value(value: Any, type_name: str, context: str) -> Any:
    if type_name == "int":
        if type(value) is not int:
            _reject("value.type", f"{context} must be an integer")
        if value < INT_MIN or value > INT_MAX:
            _reject("integer.overflow", f"{context} is outside signed 64-bit range")
        return value
    if type_name == "bool":
        if type(value) is not bool:
            _reject("value.type", f"{context} must be a boolean")
        return value
    if type_name == "string":
        return _string(value, context)
    if not isinstance(value, list):
        _reject("value.type", f"{context} must be a string list")
    if len(value) > MAX_LIST_ITEMS:
        _reject("limit.list", f"{context} exceeds {MAX_LIST_ITEMS} items")
    return tuple(_string(item, f"{context}[{index}]") for index, item in enumerate(value))


def _node(raw: Any) -> Node:
    obj = _object(raw, "node")
    if "id" not in obj:
        _reject("structure.missing_field", "node is missing field 'id'")
    if "op" not in obj:
        _reject("structure.missing_field", "node is missing field 'op'")
    node_id = _identifier(obj["id"], "node.id")
    op = obj["op"]
    if not isinstance(op, str) or op not in OP_FIELDS:
        _reject("operation.unknown", f"node {node_id!r} has an unknown operation")
    _fields(obj, OP_FIELDS[op], f"node {node_id!r}")

    args = {key: value for key, value in obj.items() if key not in {"id", "op"}}
    references: tuple[str, ...]
    if op == "input":
        args["name"] = _identifier(args["name"], f"node {node_id!r}.name")
        args["type"] = _type_name(args["type"], f"node {node_id!r}")
        references = ()
    elif op == "literal":
        args["type"] = _type_name(args["type"], f"node {node_id!r}")
        args["value"] = _value(args["value"], args["type"], f"node {node_id!r}.value")
        references = ()
    elif op == "list.concat":
        if not isinstance(args["items"], list):
            _reject("structure.array", f"node {node_id!r}.items must be an array")
        if not 1 <= len(args["items"]) <= MAX_CONCAT_ITEMS:
            _reject(
                "limit.concat_items",
                f"node {node_id!r}.items must contain 1 to {MAX_CONCAT_ITEMS} references",
            )
        references = tuple(
            _reference(item, f"node {node_id!r}.items[{index}]")
            for index, item in enumerate(args["items"])
        )
    elif op in {"identity", "list.unique", "list.sort", "list.length", "bool.not"}:
        references = (_reference(args["value"], f"node {node_id!r}.value"),)
    else:
        references = (
            _reference(args["left"], f"node {node_id!r}.left"),
            _reference(args["right"], f"node {node_id!r}.right"),
        )
    return Node(node_id=node_id, op=op, args=copy.deepcopy(args), references=references)


def _topological(nodes: dict[str, Node]) -> tuple[str, ...]:
    state: dict[str, int] = {}
    order: list[str] = []

    def visit(node_id: str) -> None:
        marker = state.get(node_id, 0)
        if marker == 1:
            _reject("graph.cycle", f"graph contains a cycle involving node {node_id!r}")
        if marker == 2:
            return
        state[node_id] = 1
        for dependency in nodes[node_id].references:
            visit(dependency)
        state[node_id] = 2
        order.append(node_id)

    for node_id in sorted(nodes):
        visit(node_id)
    return tuple(order)


def _require_type(types: dict[str, str], node: Node, wanted: str) -> None:
    for reference in node.references:
        if types[reference] != wanted:
            _reject(
                "type.mismatch",
                f"node {node.node_id!r} requires {wanted}, got {types[reference]} from {reference!r}",
            )


def compile_program(document: Any) -> CompiledProgram:
    """Validate the complete graph and return its execution plan."""
    program = _object(document, "program")
    _fields(program, frozenset({"schema", "nodes", "result"}), "program")
    if program["schema"] != PROGRAM_SCHEMA:
        _reject("schema.program", f"program schema must be {PROGRAM_SCHEMA!r}")
    if not isinstance(program["nodes"], list):
        _reject("structure.array", "program.nodes must be an array")
    if not 1 <= len(program["nodes"]) <= MAX_NODES:
        _reject("limit.nodes", f"program.nodes must contain 1 to {MAX_NODES} nodes")

    nodes: dict[str, Node] = {}
    raw_nodes: dict[str, dict[str, Any]] = {}
    input_names: set[str] = set()
    for raw in program["nodes"]:
        node = _node(raw)
        if node.node_id in nodes:
            _reject("node.duplicate", f"duplicate node id {node.node_id!r}")
        if node.op == "input":
            name = node.args["name"]
            if name in input_names:
                _reject("input.duplicate", f"duplicate input name {name!r}")
            input_names.add(name)
        nodes[node.node_id] = node
        raw_nodes[node.node_id] = copy.deepcopy(raw)

    result_id = _reference(program["result"], "program.result")
    for node_id in sorted(nodes):
        for reference in nodes[node_id].references:
            if reference not in nodes:
                _reject("reference.missing", f"node {node_id!r} references missing node {reference!r}")
    if result_id not in nodes:
        _reject("reference.missing", f"program.result references missing node {result_id!r}")

    order = _topological(nodes)
    types: dict[str, str] = {}
    for node_id in order:
        node = nodes[node_id]
        if node.op in {"input", "literal"}:
            result_type = node.args["type"]
        elif node.op == "identity":
            result_type = types[node.references[0]]
        elif node.op in {"list.concat", "list.unique", "list.sort"}:
            _require_type(types, node, "string_list")
            result_type = "string_list"
        elif node.op == "list.length":
            _require_type(types, node, "string_list")
            result_type = "int"
        elif node.op == "int.add":
            _require_type(types, node, "int")
            result_type = "int"
        elif node.op == "int.equal":
            _require_type(types, node, "int")
            result_type = "bool"
        else:
            _require_type(types, node, "bool")
            result_type = "bool"
        types[node_id] = result_type

    canonical_document = {
        "schema": PROGRAM_SCHEMA,
        "nodes": [raw_nodes[node_id] for node_id in sorted(raw_nodes)],
        "result": {"ref": result_id},
    }
    try:
        canonical_json = json.dumps(
            canonical_document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        _reject("value.json", "program contains a value outside the JSON contract")
    digest = "sha256:" + hashlib.sha256(canonical_json).hexdigest()
    inputs = tuple(
        sorted(
            (node.args["name"], node.args["type"], node.node_id)
            for node in nodes.values()
            if node.op == "input"
        )
    )
    return CompiledProgram(
        digest=digest,
        canonical_json=canonical_json,
        nodes=nodes,
        order=order,
        types=types,
        inputs=inputs,
        result_id=result_id,
    )


def program_digest(document: Any) -> str:
    return compile_program(document).digest


def _external(value: Any) -> Any:
    return list(value) if isinstance(value, tuple) else value


def run_program(document: Any, inputs: Any) -> Any:
    """Validate program and all inputs, then evaluate the pure graph."""
    compiled = compile_program(document)
    supplied = _object(inputs, "inputs")
    expected = {name for name, _type, _node_id in compiled.inputs}
    missing = sorted(expected - set(supplied))
    if missing:
        _reject("input.missing", f"missing input {missing[0]!r}")
    unexpected = sorted(set(supplied) - expected)
    if unexpected:
        _reject("input.unexpected", f"unexpected input {unexpected[0]!r}")

    validated: dict[str, Any] = {}
    for name, type_name, _node_id in compiled.inputs:
        validated[name] = _value(supplied[name], type_name, f"input {name!r}")

    values: dict[str, Any] = {}
    for node_id in compiled.order:
        node = compiled.nodes[node_id]
        if node.op == "input":
            value = validated[node.args["name"]]
        elif node.op == "literal":
            value = node.args["value"]
        elif node.op == "identity":
            value = values[node.references[0]]
        elif node.op == "list.concat":
            combined = tuple(item for reference in node.references for item in values[reference])
            if len(combined) > MAX_LIST_ITEMS:
                _reject("limit.list", f"node {node_id!r} result exceeds {MAX_LIST_ITEMS} items")
            value = combined
        elif node.op == "list.unique":
            value = tuple(dict.fromkeys(values[node.references[0]]))
        elif node.op == "list.sort":
            value = tuple(sorted(values[node.references[0]]))
        elif node.op == "list.length":
            value = len(values[node.references[0]])
        elif node.op == "int.add":
            value = values[node.references[0]] + values[node.references[1]]
            if value < INT_MIN or value > INT_MAX:
                _reject("integer.overflow", f"node {node_id!r} overflowed signed 64-bit integer")
        elif node.op == "int.equal":
            value = values[node.references[0]] == values[node.references[1]]
        else:
            value = not values[node.references[0]]
        values[node_id] = value
    return _external(values[compiled.result_id])


def apply_patch(program: Any, patch: Any) -> dict[str, Any]:
    """Atomically return a validated replacement graph; never mutate inputs."""
    base = compile_program(program)
    change = _object(patch, "patch")
    _fields(change, frozenset({"schema", "base", "add", "replace"}), "patch")
    if change["schema"] != PATCH_SCHEMA:
        _reject("schema.patch", f"patch schema must be {PATCH_SCHEMA!r}")
    if not isinstance(change["base"], str) or DIGEST.fullmatch(change["base"]) is None:
        _reject("patch.base", "patch.base must be a canonical sha256 digest")
    if change["base"] != base.digest:
        _reject("patch.stale", "patch base digest does not match the program")
    if not isinstance(change["add"], list) or not isinstance(change["replace"], list):
        _reject("structure.array", "patch.add and patch.replace must be arrays")
    if len(change["add"]) + len(change["replace"]) > MAX_NODES:
        _reject("limit.patch_nodes", f"patch changes exceed {MAX_NODES} nodes")

    candidate = base.document()
    positions = {node["id"]: index for index, node in enumerate(candidate["nodes"])}
    seen: set[str] = set()
    replacements: list[tuple[str, dict[str, Any]]] = []
    additions: list[tuple[str, dict[str, Any]]] = []
    for mode, raw_nodes, target in (
        ("replace", change["replace"], replacements),
        ("add", change["add"], additions),
    ):
        for raw in raw_nodes:
            obj = _object(raw, f"patch.{mode} node")
            if "id" not in obj:
                _reject("structure.missing_field", f"patch.{mode} node is missing field 'id'")
            node_id = _node(obj).node_id
            if node_id in seen:
                _reject("patch.duplicate", f"patch changes node {node_id!r} more than once")
            seen.add(node_id)
            if mode == "replace" and node_id not in positions:
                _reject("patch.replace_missing", f"cannot replace absent node {node_id!r}")
            if mode == "add" and node_id in positions:
                _reject("patch.add_existing", f"cannot add existing node {node_id!r}")
            target.append((node_id, copy.deepcopy(obj)))

    for node_id, replacement in replacements:
        candidate["nodes"][positions[node_id]] = replacement
    candidate["nodes"].extend(addition for _node_id, addition in additions)
    return compile_program(candidate).document()


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check and run bounded bagaev L0 programs.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser("check", help="validate a program")
    check_parser.add_argument("program", type=Path)
    run_parser = subparsers.add_parser("run", help="run a program with an inputs object")
    run_parser.add_argument("program", type=Path)
    run_parser.add_argument("inputs", type=Path)
    patch_parser = subparsers.add_parser("patch", help="apply and print an atomic structural patch")
    patch_parser.add_argument("program", type=Path)
    patch_parser.add_argument("patch", type=Path)
    arguments = parser.parse_args(argv)
    try:
        program = load_json_file(arguments.program)
        compiled = compile_program(program)
        if arguments.command == "check":
            payload = {
                "schema": RESULT_SCHEMA,
                "ok": True,
                "command": "check",
                "program_digest": compiled.digest,
                "node_count": len(compiled.nodes),
                "input_names": [name for name, _type, _node_id in compiled.inputs],
                "result_type": compiled.result_type,
            }
        elif arguments.command == "run":
            result = run_program(program, load_json_file(arguments.inputs))
            payload = {
                "schema": RESULT_SCHEMA,
                "ok": True,
                "command": "run",
                "program_digest": compiled.digest,
                "result_type": compiled.result_type,
                "result": result,
            }
        else:
            patched = apply_patch(program, load_json_file(arguments.patch))
            patched_compiled = compile_program(patched)
            payload = {
                "schema": RESULT_SCHEMA,
                "ok": True,
                "command": "patch",
                "base_digest": compiled.digest,
                "program_digest": patched_compiled.digest,
                "program": patched,
            }
        _emit(payload)
        return 0
    except L0Error as error:
        _emit({
            "schema": RESULT_SCHEMA,
            "ok": False,
            "command": getattr(arguments, "command", None),
            "error": {"code": error.code, "message": error.message},
        })
        return 2
    except OSError:
        _emit({
            "schema": RESULT_SCHEMA,
            "ok": False,
            "command": getattr(arguments, "command", None),
            "error": {"code": "io.error", "message": "unable to read an input file"},
        })
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
