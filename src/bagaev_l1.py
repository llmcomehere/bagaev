"""Deterministic whole-L0 source lowering for the bounded CPython L1 profile.

generate_source returns bytes and identities; it never executes or writes them.
Generated artifacts require separate admission before execution. There is no
concurrent-mutation guarantee for caller-owned plans; emission uses only the
fresh, private plan after checking every supplied field against that plan.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from typing import Any

from bagaev_l0 import CompiledProgram, L0Error, Node, compile_program

GENERATOR_REVISION = "bagaev/l1-cpython/v1"


class L1Error(ValueError):
    """Generation refusal; no artifact has been returned."""

    code = "l1.program_mismatch"


@dataclass(frozen=True)
class SourceArtifact:
    source: bytes
    program_digest: str
    generator_revision: str
    artifact_sha256: str


def _same(left: Any, right: Any) -> bool:
    """Exact structural equality, including container and scalar types."""
    if type(left) is not type(right):
        return False
    kind = type(left)
    if kind in (str, bytes, int, bool, type(None)):
        return left == right
    if kind in (tuple, list):
        return len(left) == len(right) and all(
            _same(a, b) for a, b in zip(left, right)
        )
    if kind is dict:
        # All dictionaries in an admitted execution plan have string keys.
        if any(type(key) is not str for key in left):
            return False
        if any(type(key) is not str for key in right):
            return False
        return left.keys() == right.keys() and all(
            _same(left[key], right[key]) for key in left
        )
    if kind in (Node, CompiledProgram):
        return all(
            _same(getattr(left, field.name), getattr(right, field.name))
            for field in fields(kind)
        )
    return False


def _revalidate(program: CompiledProgram) -> CompiledProgram:
    if type(program) is not CompiledProgram or type(program.canonical_json) is not bytes:
        raise L1Error("expected a checked L0 program")
    try:
        # Do not impose the input-file byte limit on an in-memory L0 program.
        # Exact canonical byte comparison below also rejects duplicate keys,
        # noncanonical encodings, whitespace, and non-JSON numeric constants.
        document = json.loads(program.canonical_json.decode("utf-8"))
        checked = compile_program(document)
        matches = _same(program, checked)
    except (L0Error, ValueError, TypeError, RecursionError, AttributeError, KeyError):
        raise L1Error("program does not match its canonical execution plan") from None
    if not matches:
        raise L1Error("program does not match its canonical execution plan")
    return checked


# This fixed runtime implements the input/output boundary, not an operation
# interpreter. All graph operations and input types are lowered at generation.
_RUNTIME = '''import argparse
import json


class _Refusal(ValueError):
    def __init__(self, code, message):
        self.code = code
        self.message = message


def _reject(code, message):
    raise _Refusal(code, message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject("json.duplicate_key", "duplicate JSON key")
        result[key] = value
    return result


def _integer_token(value):
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > 19:
        _reject("integer.overflow", "JSON integer is outside signed 64-bit range")
    parsed = int(value)
    if parsed < -9223372036854775808 or parsed > 9223372036854775807:
        _reject("integer.overflow", "JSON integer is outside signed 64-bit range")
    return parsed


def _load(data):
    if len(data) > 1048576:
        _reject("limit.json_bytes", "JSON input exceeds 1048576 bytes")
    try:
        return json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_int=_integer_token,
            parse_constant=lambda _value: _reject("json.constant", "non-JSON numeric constant"),
        )
    except _Refusal:
        raise
    except UnicodeDecodeError:
        _reject("json.encoding", "JSON input is not valid UTF-8 text")
    except (json.JSONDecodeError, RecursionError, ValueError):
        _reject("json.syntax", "invalid JSON document")


def _int(value, context):
    if type(value) is not int:
        _reject("value.type", context + " must be an integer")
    if value < -9223372036854775808 or value > 9223372036854775807:
        _reject("integer.overflow", context + " is outside signed 64-bit range")
    return value


def _bool(value, context):
    if type(value) is not bool:
        _reject("value.type", context + " must be a boolean")
    return value


def _string(value, context):
    if not isinstance(value, str):
        _reject("value.type", context + " must be a string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        _reject("value.string", context + " contains an invalid Unicode scalar value")
    if size > 4096:
        _reject("limit.string", context + " exceeds 4096 UTF-8 bytes")
    return value


def _string_list(value, context):
    if not isinstance(value, list):
        _reject("value.type", context + " must be a string list")
    if len(value) > 256:
        _reject("limit.list", context + " exceeds 256 items")
    return tuple(_string(item, context + "[" + str(index) + "]")
                 for index, item in enumerate(value))


def _input_keys(supplied, names):
    if not isinstance(supplied, dict):
        _reject("structure.object", "inputs must be an object")
    missing = sorted(set(names) - set(supplied))
    if missing:
        _reject("input.missing", "missing input " + repr(missing[0]))
    unexpected = sorted(set(supplied) - set(names))
    if unexpected:
        _reject("input.unexpected", "unexpected input")


def _emit(payload):
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a fixed bounded bagaev L1 program.")
    parser.add_argument("inputs")
    arguments = parser.parse_args(argv)
    try:
        with open(arguments.inputs, "rb") as stream:
            supplied = _load(stream.read(1048577))
        result = _run(supplied)
        payload = {
            "schema": "bagaev/l0-result/v1", "ok": True, "command": "run",
            "program_digest": _DATA[0], "result_type": _DATA[1], "result": result,
        }
    except _Refusal as error:
        _emit({
            "schema": "bagaev/l0-result/v1", "ok": False, "command": "run",
            "error": {"code": error.code, "message": error.message},
        })
        return 2
    except OSError:
        _emit({
            "schema": "bagaev/l0-result/v1", "ok": False, "command": "run",
            "error": {"code": "io.error", "message": "unable to read an input file"},
        })
        return 2
    _emit(payload)
    return 0
'''


def generate_source(program: CompiledProgram) -> SourceArtifact:
    """Revalidate a complete plan, then return deterministic UTF-8 source.

    artifact_sha256 is the lowercase hex SHA-256 of source; program_digest
    keeps the L0 sha256: prefix. No artifact is returned on plan mismatch.
    """
    checked = _revalidate(program)
    data: list[Any] = [checked.digest, checked.result_type]

    def datum(value: Any) -> str:
        index = len(data)
        data.append(value)
        return f"_DATA[{index}]"

    names = datum([name for name, _type, _node in checked.inputs])
    lines = ["def _run(supplied):", f"    _input_keys(supplied, {names})"]
    validators = {"int": "_int", "bool": "_bool", "string": "_string",
                  "string_list": "_string_list"}
    input_vars: dict[str, str] = {}
    # Validate all inputs in the oracle's sorted-name order before any node.
    for index, (name, type_name, node_id) in enumerate(checked.inputs):
        variable = f"i{index}"
        input_vars[node_id] = variable
        name_data = datum(name)
        context_data = datum(f"input {name!r}")
        lines.append(
            f"    {variable} = {validators[type_name]}(supplied[{name_data}], {context_data})"
        )

    variables = {node_id: f"v{index}" for index, node_id in enumerate(checked.order)}
    for node_id in checked.order:
        node = checked.nodes[node_id]
        target = variables[node_id]
        refs = [variables[ref] for ref in node.references]
        if node.op == "input":
            expression = input_vars[node_id]
        elif node.op == "literal":
            expression = datum(node.args["value"])
            if node.args["type"] == "string_list":
                expression = f"tuple({expression})"
        elif node.op == "identity":
            expression = refs[0]
        elif node.op == "list.concat":
            expression = " + ".join(refs)
        elif node.op == "list.unique":
            expression = f"tuple(dict.fromkeys({refs[0]}))"
        elif node.op == "list.sort":
            expression = f"tuple(sorted({refs[0]}))"
        elif node.op == "list.length":
            expression = f"len({refs[0]})"
        elif node.op == "int.add":
            expression = f"{refs[0]} + {refs[1]}"
        elif node.op == "int.equal":
            expression = f"{refs[0]} == {refs[1]}"
        elif node.op == "bool.not":
            expression = f"not {refs[0]}"
        else:
            raise L1Error("program contains an unknown operation")
        lines.append(f"    {target} = {expression}")
        if node.op == "list.concat":
            message = datum(f"node {node_id!r} result exceeds 256 items")
            lines.extend([
                f"    if len({target}) > 256:",
                f'        _reject("limit.list", {message})',
            ])
        elif node.op == "int.add":
            message = datum(f"node {node_id!r} overflowed signed 64-bit integer")
            lines.extend([
                f"    if {target} < -9223372036854775808 or {target} > 9223372036854775807:",
                f'        _reject("integer.overflow", {message})',
            ])
    result = variables[checked.result_id]
    if checked.result_type == "string_list":
        result = f"list({result})"
    lines.append(f"    return {result}")

    # Only hex digits cross the data/source boundary. Node IDs, strings, input
    # names, and diagnostic text never become executable Python tokens.
    encoded = json.dumps(data, ensure_ascii=True, allow_nan=False,
                         separators=(",", ":")).encode("ascii").hex()
    source = (
        "# Generated by " + GENERATOR_REVISION + "; fixed L0 program.\n"
        + _RUNTIME + "\n\n_DATA = json.loads(bytes.fromhex(\"" + encoded
        + "\").decode(\"ascii\"))\n\n\n" + "\n".join(lines)
        + '\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
    ).encode("utf-8")
    return SourceArtifact(
        source=source,
        program_digest=checked.digest,
        generator_revision=GENERATOR_REVISION,
        artifact_sha256=hashlib.sha256(source).hexdigest(),
    )
