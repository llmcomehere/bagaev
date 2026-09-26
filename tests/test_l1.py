"""L1 generation tests and runtime cases for a separately admitted checker.

A focused regression runs generated refusal code in memory with mocked input
inside the admitted test guest, without file or process writes. runtime_cases()
describes inputs and expected observations; assert_runtime_observations()
checks complete observations supplied by an external checker. These tests
alone are not full runtime equivalence evidence. All code here requires an
execution profile.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for module_name in ("bagaev_l0", "bagaev_l1"):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / "src" / (module_name + ".py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
L0 = sys.modules["bagaev_l0"]
L1 = sys.modules["bagaev_l1"]


def ref(node_id: str) -> dict:
    return {"ref": node_id}


def program(nodes: list[dict], result: str) -> dict:
    return {"schema": "bagaev/l0-program/v1", "nodes": nodes, "result": ref(result)}


def input_program(type_name: str) -> dict:
    return program([{"id": "value", "op": "input", "name": "x", "type": type_name}], "value")


def literal_program(value: Any, type_name: str = "int") -> dict:
    return program([{"id": "value", "op": "literal", "type": type_name, "value": value}], "value")


def whole_program(result: str = "negated") -> dict:
    return program([
        {"id": "tags", "op": "input", "name": "tags", "type": "string_list"},
        {"id": "prefix", "op": "literal", "type": "string_list", "value": ["c"]},
        {"id": "joined", "op": "list.concat", "items": [ref("tags"), ref("prefix")]},
        {"id": "copied", "op": "identity", "value": ref("joined")},
        {"id": "unique", "op": "list.unique", "value": ref("copied")},
        {"id": "sorted", "op": "list.sort", "value": ref("unique")},
        {"id": "length", "op": "list.length", "value": ref("sorted")},
        {"id": "one", "op": "literal", "type": "int", "value": 1},
        {"id": "sum", "op": "int.add", "left": ref("length"), "right": ref("one")},
        {"id": "four", "op": "literal", "type": "int", "value": 4},
        {"id": "equal", "op": "int.equal", "left": ref("sum"), "right": ref("four")},
        {"id": "negated", "op": "bool.not", "value": ref("equal")},
    ], result)


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def typed_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without equating bool, int, and float."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(typed_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


@dataclass(frozen=True)
class RuntimeCase:
    name: str
    document: dict
    inputs: bytes
    result_type: str | None = None
    result: Any = None
    error_code: str | None = None


def runtime_cases() -> tuple[RuntimeCase, ...]:
    """Fixed observations; constructing these cases does not execute artifacts."""
    cases = []

    def success(name, document, inputs, result_type, result):
        cases.append(RuntimeCase(name, document, inputs, result_type, result))

    def refusal(name, document, inputs, code):
        cases.append(RuntimeCase(name, document, inputs, error_code=code))

    for node, expected_type, expected in (
        ("tags", "string_list", ["b", "a", "b"]),
        ("prefix", "string_list", ["c"]),
        ("joined", "string_list", ["b", "a", "b", "c"]),
        ("copied", "string_list", ["b", "a", "b", "c"]),
        ("unique", "string_list", ["b", "a", "c"]),
        ("sorted", "string_list", ["a", "b", "c"]),
        ("length", "int", 3), ("sum", "int", 4),
        ("equal", "bool", True), ("negated", "bool", False),
    ):
        success("operation-" + node, whole_program(node), b'{"tags":["b","a","b"]}',
                expected_type, expected)
    success("equal-false", whole_program("equal"), b'{"tags":[]}', "bool", False)
    success("not-true", whole_program(), b'{"tags":[]}', "bool", True)
    for type_name, value in (("int", -9223372036854775808), ("int", 9223372036854775807),
                             ("bool", False), ("bool", True), ("string", ""),
                             ("string", "é" * 2048), ("string", "a" * 4096),
                             ("string_list", []), ("string_list", ["a"] * 256)):
        success("input-bound-" + str(len(cases)), input_program(type_name),
                json_bytes({"x": value}), type_name, value)
    for type_name, value in (("int", 0), ("bool", True), ("string", "λ\n'\"\\"),
                             ("string_list", ["z", "é", "z"])):
        success("literal-" + type_name, literal_program(value, type_name), b"{}", type_name, value)
    text = "'); __import__('os').system('false'); #\n\x00\u2028"
    success("literal-inert-text", literal_program(text, "string"), b"{}", "string", text)
    # The input-file byte cap does not cap a checked in-memory program or its
    # output envelope. Every literal item here still meets the L0 type bounds.
    large_literal = ["a" * 4096] * 256
    success("large-literal-output", literal_program(large_literal, "string_list"),
            b"{}", "string_list", large_literal)
    empty_concat = program([
        {"id": "empty", "op": "literal", "type": "string_list", "value": []},
        {"id": "joined", "op": "list.concat", "items": [ref("empty")] * 32},
    ], "joined")
    success("concat-32", empty_concat, b"{}", "string_list", [])
    chain = [{"id": "n000", "op": "input", "name": "x", "type": "int"}]
    chain.extend({"id": f"n{i:03d}", "op": "identity", "value": ref(f"n{i-1:03d}")}
                 for i in range(1, 256))
    success("nodes-256", program(chain, "n255"), b'{"x":0}', "int", 0)
    success("json-byte-limit", literal_program(0), b"{}" + b" " * 1048574, "int", 0)
    refusal("json-byte-overflow", literal_program(0), b"{}" + b" " * 1048575, "limit.json_bytes")
    for name, type_name, value, code in (
        ("bool-as-int", "int", True, "value.type"),
        ("float-as-int", "int", 1.0, "value.type"),
        ("int-as-bool", "bool", 1, "value.type"),
        ("string-as-list", "string_list", "x", "value.type"),
        ("invalid-list-item", "string_list", [1], "value.type"),
        ("list-overflow", "string_list", ["a"] * 257, "limit.list"),
        ("string-overflow", "string", "a" * 4097, "limit.string"),
        ("utf8-byte-overflow", "string", "é" * 2049, "limit.string"),
        ("list-string-byte-overflow", "string_list", ["é" * 2049], "limit.string"),
    ):
        refusal(name, input_program(type_name), json_bytes({"x": value}), code)
    for name, raw, code in (
        ("missing", b"{}", "input.missing"),
        ("unexpected", b'{"x":1,"extra":0}', "input.unexpected"),
        ("missing-before-unexpected", b'{"extra":0}', "input.missing"),
        ("duplicate-key", b'{"x":1,"x":2}', "json.duplicate_key"),
        ("integer-overflow", b'{"x":9223372036854775808}', "integer.overflow"),
        ("integer-underflow", b'{"x":-9223372036854775809}', "integer.overflow"),
        ("huge-integer", b'{"x":' + b"9" * 5000 + b"}", "integer.overflow"),
        ("invalid-utf8", b'{"x":"\xff"}', "json.encoding"),
        ("syntax", b"{", "json.syntax"),
        ("trailing-document", b'{"x":1}{}', "json.syntax"),
        ("nan", b'{"x":NaN}', "json.constant"),
        ("not-object", b"[]", "structure.object"),
    ):
        refusal(name, input_program("int"), raw, code)
    refusal("unicode-surrogate", input_program("string"), b'{"x":"\\ud800"}', "value.string")
    overflow = program([
        {"id": "result", "op": "literal", "type": "int", "value": 0},
        {"id": "max", "op": "literal", "type": "int", "value": 9223372036854775807},
        {"id": "one", "op": "literal", "type": "int", "value": 1},
        {"id": "unused", "op": "int.add", "left": ref("max"), "right": ref("one")},
    ], "result")
    refusal("eager-unreachable-overflow", overflow, b"{}", "integer.overflow")
    concat = program([
        {"id": "a", "op": "input", "name": "a", "type": "string_list"},
        {"id": "b", "op": "input", "name": "b", "type": "string_list"},
        {"id": "joined", "op": "list.concat", "items": [ref("a"), ref("b")]},
    ], "joined")
    refusal("concat-result-overflow", concat, json_bytes({"a": ["a"] * 256, "b": ["a"] * 256}),
            "limit.list")
    success("concat-result-limit", concat, json_bytes({"a": ["a"] * 128, "b": ["b"] * 128}),
            "string_list", ["a"] * 128 + ["b"] * 128)
    # Input names have the reverse order to node IDs; validation must precede
    # eager operations and use sorted input names, not the topological order.
    precedence = copy.deepcopy(overflow)
    precedence["nodes"].extend([
        {"id": "aa", "op": "input", "name": "z", "type": "int"},
        {"id": "zz", "op": "input", "name": "a", "type": "string"},
    ])
    refusal("input-order-before-eager-overflow", precedence,
            json_bytes({"a": "é" * 2049, "z": True}), "limit.string")
    return tuple(cases)


def assert_observation(test: unittest.TestCase, case: RuntimeCase,
                       digest: str, stdout: bytes, returncode: int) -> None:
    """Check supplied observations only; this function never runs artifacts."""
    test.assertIs(type(stdout), bytes)
    test.assertIs(type(returncode), int)
    test.assertTrue(stdout.endswith(b"\n"))
    test.assertEqual(stdout.count(b"\n"), 1, "expected one JSON output line")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate output key")
            result[key] = value
        return result

    def reject_constant(_value):
        raise ValueError("non-JSON output constant")

    try:
        payload = json.loads(stdout.decode("utf-8"), object_pairs_hook=unique_pairs,
                             parse_constant=reject_constant)
    except (ValueError, RecursionError):
        test.fail("invalid JSON output")
    test.assertIs(type(payload), dict)
    if case.error_code is None:
        expected = {
            "schema": "bagaev/l0-result/v1", "ok": True, "command": "run",
            "program_digest": digest, "result_type": case.result_type, "result": case.result,
        }
        test.assertEqual(returncode, 0)
        test.assertTrue(typed_equal(payload, expected), "typed success envelope differs")
    else:
        test.assertEqual(returncode, 2)
        test.assertEqual(set(payload), {"schema", "ok", "command", "error"})
        test.assertEqual(payload["schema"], "bagaev/l0-result/v1")
        test.assertIs(payload["ok"], False)
        test.assertEqual(payload["command"], "run")
        test.assertIs(type(payload["error"]), dict)
        test.assertEqual(set(payload["error"]), {"code", "message"})
        test.assertEqual(payload["error"]["code"], case.error_code)
        test.assertIs(type(payload["error"]["message"]), str)
        test.assertTrue(payload["error"]["message"])


def assert_runtime_observations(test: unittest.TestCase, observations: dict) -> None:
    """Require every local case, with no skips or missing observations.

    The external checker owns source/artifact hash binding, isolation, runtime
    identity and path-disclosure checks. This is not the profile's 41-case
    acceptance runner and does not supply evidence for those obligations.
    Each observation has (program_digest, stdout_bytes, process_exit_code).
    """
    cases = runtime_cases()
    test.assertTrue(cases)
    test.assertEqual(len({case.name for case in cases}), len(cases))
    test.assertEqual(set(observations), {case.name for case in cases})
    for case in cases:
        with test.subTest(case=case.name):
            digest, stdout, returncode = observations[case.name]
            test.assertEqual(digest, L0.compile_program(case.document).digest)
            assert_observation(test, case, digest, stdout, returncode)


class GenerationTests(unittest.TestCase):
    def test_canonical_determinism_and_metadata(self):
        def reverse_keys(value):
            if type(value) is dict:
                return {key: reverse_keys(value[key]) for key in reversed(value)}
            if type(value) is list:
                return [reverse_keys(item) for item in value]
            return value

        original = whole_program()
        reordered = reverse_keys(original)
        reordered["nodes"].reverse()
        first = L1.generate_source(L0.compile_program(original))
        second = L1.generate_source(L0.compile_program(reordered))
        self.assertEqual(first, second)
        self.assertEqual(first, L1.generate_source(L0.compile_program(original)))
        self.assertIs(type(first.source), bytes)
        first.source.decode("utf-8", errors="strict")
        self.assertEqual(first.program_digest, L0.compile_program(original).digest)
        self.assertEqual(first.generator_revision, L1.GENERATOR_REVISION)
        self.assertEqual(first.artifact_sha256, hashlib.sha256(first.source).hexdigest())

    def test_mutated_plan_fields_are_rejected(self):
        base = L0.compile_program(whole_program())
        mutations = [
            replace(base, digest="sha256:" + "0" * 64),
            replace(base, canonical_json=base.canonical_json + b" "),
            replace(base, canonical_json=b"{"),
            replace(base, order=tuple(reversed(base.order))),
            replace(base, order=list(base.order)),
            replace(base, inputs=()),
            replace(base, inputs=(("tags", "int", "tags"),)),
            replace(base, result_id="equal"),
            replace(base, types={**base.types, "negated": "int"}),
        ]
        for field, value in (("node_id", "different"), ("op", "unknown"),
                             ("references", ("four",))):
            candidate = copy.deepcopy(base)
            candidate.nodes["one"] = replace(candidate.nodes["one"], **{field: value})
            mutations.append(candidate)
        for value in (True, 1.0, "1"):
            candidate = copy.deepcopy(base)
            candidate.nodes["one"].args["value"] = value
            mutations.append(candidate)
        candidate = copy.deepcopy(base)
        candidate.nodes["joined"].args["items"][0]["ref"] = "prefix"
        mutations.append(candidate)
        candidate = copy.deepcopy(base)
        candidate.nodes["prefix"].args["value"] = ["c"]  # tuple/list distinction
        mutations.append(candidate)
        candidate = copy.deepcopy(base)
        candidate.nodes["one"].args["extra"] = 0
        mutations.append(candidate)
        candidate = copy.deepcopy(base)
        del candidate.nodes["negated"]
        mutations.append(candidate)
        for index, candidate in enumerate(mutations):
            with self.subTest(mutation=index):
                with self.assertRaises(L1.L1Error):
                    L1.generate_source(candidate)

    def test_generation_does_not_mutate_the_plan(self):
        checked = L0.compile_program(whole_program())
        before = copy.deepcopy(checked)
        L1.generate_source(checked)
        self.assertEqual(checked, before)

    def test_program_text_is_inert_and_operations_are_lowered(self):
        text = "'); __import__('os').system('false'); #\n\x00\u2028"
        artifact = L1.generate_source(L0.compile_program(literal_program(text, "string")))
        self.assertNotIn(text.encode("utf-8"), artifact.source)
        source = L1.generate_source(L0.compile_program(whole_program())).source.decode("utf-8")
        self.assertNotIn("bagaev_l0", source)
        self.assertNotIn("node.op", source)
        self.assertNotIn("compile_program", source)
        self.assertIn("tuple(dict.fromkeys(v", source)
        self.assertIn("tuple(sorted(v", source)
        self.assertIn(" = not v", source)

    def test_every_runtime_case_has_a_generatable_program(self):
        for case in runtime_cases():
            with self.subTest(case=case.name):
                artifact = L1.generate_source(L0.compile_program(case.document))
                self.assertTrue(artifact.source)

    def test_generated_refusals_keep_arbitrary_keys_out_of_messages(self):
        document = input_program("int")
        checked = L0.compile_program(document)
        artifact = L1.generate_source(checked)
        namespace = {"__name__": "l1_message_regression"}
        # This execution belongs only to the separately admitted test guest.
        exec(compile(artifact.source, "<generated-l1>", "exec"), namespace)
        for index, key in enumerate(("/synthetic/path", "C:\\synthetic\\path",
                                     "a" * 10000, "ключ")):
            key_bytes = json_bytes(key)
            for code, raw in (
                ("json.duplicate_key", b"{" + key_bytes + b":0," + key_bytes + b":1}"),
                ("input.unexpected", b'{"x":0,' + key_bytes + b":1}"),
            ):
                with self.subTest(key_case=index, code=code):
                    output = io.StringIO()
                    with patch("builtins.open", return_value=io.BytesIO(raw)) as opened, \
                         contextlib.redirect_stdout(output):
                        returncode = namespace["main"](["synthetic-input"])
                    opened.assert_called_once_with("synthetic-input", "rb")
                    stdout = output.getvalue().encode("utf-8")
                    case = RuntimeCase("message-boundary", document, raw, error_code=code)
                    assert_observation(self, case, checked.digest, stdout, returncode)
                    message = json.loads(stdout)["error"]["message"]
                    self.assertLessEqual(len(message), 200)
                    self.assertTrue(all(32 <= ord(char) <= 126 for char in message))
                    self.assertFalse(any(char in message for char in ("/", "\\", ":", "~")))
                    self.assertNotIn(key, message)


class ObservationContractTests(unittest.TestCase):
    def test_equality_is_type_sensitive_recursively(self):
        for left, right in ((True, 1), (False, 0), (1, 1.0), ([True], [1]),
                            ({"nested": [False]}, {"nested": [0]})):
            self.assertFalse(typed_equal(left, right))
        self.assertTrue(typed_equal({"nested": [False, 0, "x"]}, {"nested": [False, 0, "x"]}))

    def test_exact_success_envelope_and_exit(self):
        case = RuntimeCase("boolean", literal_program(True, "bool"), b"{}", "bool", True)
        digest = L0.compile_program(case.document).digest
        valid = {"schema": "bagaev/l0-result/v1", "ok": True, "command": "run",
                 "program_digest": digest, "result_type": "bool", "result": True}
        assert_observation(self, case, digest, json_bytes(valid) + b"\n", 0)
        for invalid in ({**valid, "result": 1}, {**valid, "extra": 0},
                        {**valid, "ok": 1}, {**valid, "program_digest": "other"}):
            with self.assertRaises(AssertionError):
                assert_observation(self, case, digest, json_bytes(invalid) + b"\n", 0)
        with self.assertRaises(AssertionError):
            assert_observation(self, case, digest, json_bytes(valid) + b"\n", 2)
        with self.assertRaises(AssertionError):
            assert_observation(self, case, digest, json_bytes(valid) + b"\n{}\n", 0)

    def test_exact_refusal_envelope_and_exit(self):
        case = RuntimeCase("refusal", input_program("int"), b'{"x":true}', error_code="value.type")
        valid = {"schema": "bagaev/l0-result/v1", "ok": False, "command": "run",
                 "error": {"code": "value.type", "message": "input must be an integer"}}
        assert_observation(self, case, "unused", json_bytes(valid) + b"\n", 2)
        for invalid in ({**valid, "result": None}, {**valid, "ok": 0},
                        {**valid, "error": {"code": "value.type"}},
                        {**valid, "error": {"code": "wrong", "message": "refused"}}):
            with self.assertRaises(AssertionError):
                assert_observation(self, case, "unused", json_bytes(invalid) + b"\n", 2)
        with self.assertRaises(AssertionError):
            assert_observation(self, case, "unused", json_bytes(valid) + b"\n", 0)

    def test_empty_observations_cannot_pass_runtime_check(self):
        with self.assertRaises(AssertionError):
            assert_runtime_observations(self, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
