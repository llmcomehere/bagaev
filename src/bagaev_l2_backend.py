"""Deterministic L2-to-CPython lowering and exact artifact verification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import bagaev_l2 as L2

SCHEMA = "bagaev-l2-cpython/1"
GENERATOR_VERSION = "bagaev-l2-lowering/1"
ARTIFACT_LIMIT = 16777216


class ArtifactError(ValueError):
    code = "TOOL_ARTIFACT"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _pointer(path, part):
    return path + "/" + str(part).replace("~", "~0").replace("/", "~1")


class _Lowering:
    def __init__(self, program):
        self.program = program
        self.roots = {name: i for i, name in enumerate(sorted(program["definitions"]))}
        self.next_node = len(self.roots)
        self.functions = {}

    def node(self, expr, name, path, number=None):
        if number is None:
            number = self.next_node
            self.next_node += 1
        # Every expression is a specialized Python generator. Yielding child
        # calls avoids CPython recursion and static-block limits at legal L2 depths.
        lines = [f"def _n{number}(budget, env, depth):",
                 f"    c = _Frame(budget, {name!r}, {self.program['pins'][name]!r}, {path!r})",
                 "    c.charge()", "    if False:", "        yield None"]

        def emit(text, indent=1):
            lines.append("    " * indent + text)

        def child(value, part, target, indent=1, environment="env"):
            child_path = path
            for component in part if type(part) is tuple else (part,):
                child_path = _pointer(child_path, component)
            n = self.node(value, name, child_path)
            emit(f"{target} = yield (_n{n}, {environment}, depth)", indent)

        if type(expr) is not list:
            emit(f"return {expr!r}")
        else:
            op = expr[0]
            if op == "literal":
                emit(f"return {expr[1]!r}")
            elif op == "var":
                emit(f"return env[{expr[1]!r}]")
            elif op == "if":
                child(expr[1], 1, "condition")
                emit("if c.boolean(condition):")
                child(expr[2], 2, "answer", 2)
                emit("else:")
                child(expr[3], 3, "answer", 2)
                emit("return answer")
            elif op in ("and", "or"):
                for i, value in enumerate(expr[1:], 1):
                    child(value, i, "answer")
                    emit(f"if c.boolean(answer) is {op == 'or'}:")
                    emit("return answer", 2)
                emit("return answer")
            elif op == "let":
                emit("local = dict(env)")
                for i, (binding, value) in enumerate(expr[1]):
                    child(value, (1, i, 1), "answer", environment="local")
                    emit(f"local[{binding!r}] = answer")
                child(expr[2], 2, "answer", environment="local")
                emit("return answer")
            elif op in ("map", "all", "any", "sort.by"):
                child(expr[1], 1, "items")
                emit("c.array(items)")
                if op == "sort.by":
                    emit("c.charge(len(items) ** 2)")
                emit("answers = []")
                emit("for item in items:")
                emit(f"local = {{**env, {expr[2]!r}: item}}", 2)
                child(expr[3], 3, "answer", 2, "local")
                if op in ("all", "any"):
                    emit(f"if c.boolean(answer) is {op == 'any'}:", 2)
                    emit("return answer", 3)
                elif op == "sort.by":
                    emit("answer = c.key(answer, answers[0] if answers else None)", 2)
                emit("answers.append(answer)", 2)
                if op in ("all", "any"):
                    emit(f"return {op == 'all'}")
                elif op == "sort.by":
                    emit("return [items[i] for i in sorted(range(len(items)), key=answers.__getitem__)]")
                else:
                    emit("return answers")
            else:
                if op in ("object", "set"):
                    fields = sorted(expr[-1])
                    if op == "set":
                        child(expr[1], 1, "base")
                    for i, key in enumerate(fields):
                        n = self.node(expr[-1][key], name,
                                      _pointer(_pointer(path, len(expr) - 1), key))
                        emit(f"a{i} = yield (_n{n}, env, depth)")
                    record = "{" + ", ".join(f"{k!r}: a{i}" for i, k in enumerate(fields)) + "}"
                    emit(f"return c.update(base, {record})" if op == "set" else f"return {record}")
                else:
                    start = 2 if op == "call" else 1
                    metadata = op in ("get", "has", "shape", "int.range", "text", "array.bound")
                    operands = expr[1:2] if metadata else expr[start:]
                    for i, value in enumerate(operands):
                        child(value, start + i, f"a{i}")
                    args = ", ".join(f"a{i}" for i in range(len(operands)))
                    if op == "call":
                        emit("c.require(depth < 64, 'L2_BOUNDS')")
                        params = self.program["definitions"][expr[1]]["params"]
                        bindings = "{" + ", ".join(f"{p!r}: a{i}" for i, p in enumerate(params)) + "}"
                        emit(f"answer = yield (_n{self.roots[expr[1]]}, {bindings}, depth + 1)")
                        emit("return answer")
                    elif op == "array":
                        emit(f"return [{args}]")
                    elif op == "get":
                        emit(f"return c.get(a0, {expr[2]!r})")
                    elif op == "has":
                        emit(f"return type(a0) is dict and {expr[2]!r} in a0")
                    elif op == "null":
                        emit("return a0 is None")
                    elif op == "shape":
                        emit(f"required, optional = {expr[2]!r}, {expr[3]!r}")
                        emit("return (type(a0) is dict and len(required) <= len(a0) <= len(required) + len(optional) and all(k in a0 for k in required) and all(k in required or k in optional for k in a0))")
                    elif op == "int.range":
                        emit(f"return type(a0) is int and {expr[2]!r} <= a0 <= {expr[3]!r}")
                    elif op == "array.bound":
                        emit(f"return type(a0) is list and len(a0) <= {expr[2]!r}")
                    elif op == "text":
                        emit(f"first, rest = {expr[4]!r}, {expr[5]!r}")
                        emit(f"return (type(a0) is str and {expr[2]} <= len(a0) <= {expr[3]} and all(any(lo <= ord(c) <= hi for lo, hi in (first if i == 0 else rest)) for i, c in enumerate(a0)))")
                    elif op == "eq":
                        emit("return type(a0) in (str, int, float, bool, type(None)) and type(a0) is type(a1) and a0 == a1")
                    elif op == "not":
                        emit("return not c.boolean(a0)")
                    elif op == "length":
                        emit("return len(c.array(a0))")
                    else:
                        emit(f"return c.{op}({args})")
        self.functions[number] = "\n".join(lines)
        return number

    def source(self, runtime):
        for name, number in self.roots.items():
            self.node(self.program["definitions"][name]["body"], name, "/body", number)
        entry = self.program["entry"]
        param = self.program["definitions"][entry]["params"][0]
        footer = ("def evaluate(argument):\n"
                  "    budget = _Budget()\n"
                  f"    result = _drive(_n{self.roots[entry]}, {{{param!r}: argument}}, budget)\n"
                  f"    return _Frame(budget, {entry!r}, {self.program['pins'][entry]!r}, '/body').export(result)\n")
        return runtime + "\n\n" + "\n\n".join(self.functions[k] for k in sorted(self.functions)) + "\n\n" + footer


def compile_program(program):
    """Return deterministic artifact bytes; never execute or write an artifact."""
    checked = L2.check_program(program)
    value = L2.program_value(checked)
    runtime = Path(__file__).with_name("bagaev_l2_runtime.py").read_bytes()
    generator = Path(__file__).read_bytes()
    identity = digest(canonical({"version": GENERATOR_VERSION,
                                 "generator": digest(generator), "runtime": digest(runtime)}))
    payload = {"schema": SCHEMA, "source": checked.digest, "generator": identity,
               "definitions": value["pins"],
               "python": _Lowering(value).source(runtime.decode("utf-8"))}
    return canonical({**payload, "artifact": digest(canonical(payload))})


def verify_artifact(artifact_bytes, expected_program):
    """Compare captured bytes with fresh trusted lowering, never trust hash fields."""
    if type(artifact_bytes) is not bytes:
        raise ArtifactError("Artifact content mismatch")
    expected = compile_program(expected_program)
    if artifact_bytes != expected:
        raise ArtifactError("Artifact content mismatch")
    return json.loads(expected)["python"].encode("utf-8")
