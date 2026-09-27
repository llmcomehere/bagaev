"""Bounded M3 acceptance cases; execution requires separate authorization."""
import ast
import contextlib
import copy
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src import bagaev as CLI
from src import bagaev_l2 as L2
from src import bagaev_l2_backend as BACKEND

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def argument_snapshot(value):
    # Keep borrowed inputs as text: isolated surrogates need not encode as UTF-8.
    # Preserve surrogate pairs versus single scalars; identities stay canonical.
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def pinned(body, definitions=None, entry="main"):
    definitions = copy.deepcopy(definitions or {})
    if body is not ...:
        definitions["main"] = {"params": ["x"], "body": body}
    graph = {}
    for name, definition in definitions.items():
        calls, todo = set(), [definition["body"]]
        while todo:
            item = todo.pop()
            if type(item) is list:
                if item and item[0] == "literal":
                    continue
                if item and item[0] == "call":
                    calls.add(item[1])
                todo.extend(item)
            elif type(item) is dict:
                todo.extend(item.values())
        graph[name] = calls
    pins = {}
    while len(pins) < len(definitions):
        ready = [name for name, deps in graph.items() if name not in pins and deps <= pins.keys()]
        if not ready:
            break
        for name in ready:
            pins[name] = digest({"schema": "bagaev-l2-definition/1",
                                "definition": definitions[name],
                                "dependencies": {d: pins[d] for d in graph[name]}})
    return {"schema": "bagaev-l2/1", "entry": entry, "definitions": definitions, "pins": pins}


def nested(depth, leaf=None):
    for _ in range(depth):
        leaf = [leaf]
    return leaf


def containers(value):
    todo, identities = [value], set()
    while todo:
        item = todo.pop()
        if type(item) in (dict, list) and id(item) not in identities:
            identities.add(id(item))
            todo.extend(item.values() if type(item) is dict else item)
    return identities


def compiled(program):
    artifact = BACKEND.compile_program(program)
    namespace = {}
    exec(compile(BACKEND.verify_artifact(artifact, program), "<test-artifact>", "exec"), namespace)
    return namespace, artifact


def boundary(case):
    name, body, argument = case["id"], case.get("body"), None
    if name.startswith("ARRAY-"):
        argument = [None] * (256 if name == "ARRAY-MAX" else 257)
    elif name in ("STRING-MAX", "STRING-OVER"):
        argument = "a" * (4096 if name == "STRING-MAX" else 4097)
    elif name == "UTF8-OVER":
        argument = "é" * 2049
    elif name == "STRING-UNICODE-BEFORE-BOUND":
        argument = {"a": "a" * 4097, "b": "\ud800"}
    elif name.startswith("EXPORT-DEPTH-"):
        argument = nested(63 if name.endswith("MAX") else 64)
    elif name.startswith("EXPRESSION-DEPTH-"):
        body = False
        for _ in range(63 if name.endswith("MAX") else 64):
            body = ["not", body]
    elif name.startswith("STEP-"):
        argument = [None] * (45 if name == "STEP-UNDER" else 46)
    elif name.startswith("DEFINITION-"):
        n = 64 if name.endswith("MAX") else 65
        definitions = {f"d{i}": {"params": ["x"], "body":
            ["call", f"d{i+1}", ["var", "x"]] if i < n-1 else True} for i in range(n)}
        return pinned(..., definitions, "d0"), None
    elif name.startswith("EXPRESSION-COUNT-"):
        definitions = {f"d{i}": {"params": ["x"], "body": ["array"] + [False] *
            (256 if i < 31 else (224 if name.endswith("MAX") else 225))} for i in range(32)}
        return pinned(..., definitions, "d0"), None
    elif name.startswith("EXPORT-NODES-"):
        argument = [[None] * 255 for _ in range(256)]
        if name.endswith("MAX"):
            argument[0].pop()
    elif name.startswith("EXPORT-BYTES-"):
        argument = ["a" * 4096] * 255 + ["a" * (3327 if name.endswith("MAX") else 3328)]
    elif name.startswith("JSON-BYTES-"):
        data = canonical(pinned(["var", "x"]))
        return data + b" " * (1048576 + name.endswith("OVER") - len(data)), None
    else:
        raise AssertionError("Missing fixed boundary construction")
    return pinned(body), argument


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = read("examples/l2/oracle.json")
        cls.app = read("examples/beta/catalog-cases.json")
        cls.snapshots = [L2.check_program((ROOT / "examples/l2/catalog.json").read_bytes())]
        for patch in ("catalog-01.patch", "catalog-12.patch", "catalog-23.patch"):
            cls.snapshots.append(L2.apply_patch(cls.snapshots[-1], (ROOT / "examples/l2" / patch).read_bytes()))
        cls.modules = [compiled(p)[0] for p in cls.snapshots]

    def observe(self, function, argument, expected):
        before = argument_snapshot(argument)
        result = function(argument)
        self.assertEqual(canonical(result), canonical(expected))
        self.assertEqual(argument_snapshot(argument), before)
        self.assertFalse(containers(result) & containers(argument))
        again = function(argument)
        self.assertEqual(canonical(again), canonical(expected))
        self.assertFalse(containers(result) & containers(again))
        return result

    def test_expression_oracle_and_independent_runtime(self):
        self.assertEqual(len(self.oracle["expressions"]), 42)
        for case in self.oracle["expressions"]:
            with self.subTest(case=case["id"]):
                checked = L2.check_program(pinned(case["body"], case.get("definitions")))
                module, artifact = compiled(checked)
                tree = ast.parse(json.loads(artifact)["python"])
                self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)))
                if "error" in case:
                    with self.assertRaises(L2.L2Error) as reference:
                        L2.evaluate(checked, case["argument"])
                    with self.assertRaises(module["L2RuntimeError"]) as generated:
                        module["evaluate"](case["argument"])
                    self.assertEqual(reference.exception.code, case["error"])
                    self.assertEqual(generated.exception.code, case["error"])
                    self.assertIn(generated.exception.location["definition"], L2.program_value(checked)["pins"])
                else:
                    self.observe(lambda x: L2.evaluate(checked, x), case["argument"], case["value"])
                    with mock.patch.object(L2, "evaluate", side_effect=AssertionError("Reference delegation")):
                        self.observe(module["evaluate"], case["argument"], case["value"])

    def test_boundary_oracle(self):
        self.assertEqual(len(self.oracle["boundaries"]), 23)
        for case in self.oracle["boundaries"]:
            with self.subTest(case=case["id"]):
                source, arg = boundary(case)
                module = None
                try:
                    checked = L2.check_program(source)
                    module, _ = compiled(checked)
                    actual = module["evaluate"](arg) if "check" not in case else None
                except Exception as error:
                    allowed = (L2.L2Error,) if module is None else (L2.L2Error, module["L2RuntimeError"])
                    self.assertIsInstance(error, allowed)
                    self.assertEqual(error.code, case.get("error"))
                else:
                    self.assertNotIn("error", case)
                    if "check" not in case:
                        self.assertEqual(canonical(actual), canonical(case.get("value", arg)))
                        self.assertFalse(containers(actual) & containers(arg))

    def test_catalog_all_revisions_and_retained_snapshots(self):
        self.assertEqual(len(self.app["cases"]), 99)
        for revision, module in enumerate(self.modules):
            self.assertEqual(self.snapshots[revision].digest, self.oracle["catalog"]["snapshots"][revision]["digest"])
            for case in self.app["cases"]:
                with self.subTest(revision=revision, case=case["id"]):
                    request = self.app["requests"][case["request"]]
                    selector = request.get("behavior_revision") if type(request) is dict else None
                    expected = self.app["responses"][case["expect"]]
                    if type(selector) is int and 0 <= selector <= 3 and selector > revision:
                        expected = {"kind": "refusal", "reason": "invalid-request"}
                    self.assertEqual(canonical(L2.evaluate(self.snapshots[revision], request)), canonical(expected))
                    result = self.observe(module["evaluate"], request, expected)
                    if result["kind"] == "success":
                        self.observe(module["evaluate"], {**request, "state": result["state"]}, expected)

    def test_actual_evolution_and_replay(self):
        cases = {c["id"]: c for c in self.app["cases"]}
        for revisions in ((0, 1, 2, 3), (3, 3, 3, 3)):
            previous = None
            for revision, name in zip(revisions, self.app["chains"][0]["cases"]):
                case = cases[name]
                request = copy.deepcopy(self.app["requests"][case["request"]])
                if previous is not None:
                    request["state"] = previous
                previous = self.observe(self.modules[revision]["evaluate"], request,
                                        self.app["responses"][case["expect"]])["state"]
            self.observe(self.modules[3]["evaluate"], {**self.app["requests"]["REPLAY-OLDER"], "state": previous},
                         self.app["responses"]["REPLAY-OLDER"])

    def test_borrowed_deep_input_and_combined_legal_depth(self):
        for depth in (0, 64, 65, 4096):
            request = {"interface": "catalog-application/2", "behavior_revision": 3,
                       "state": {"entries": [{"id": "a", "title": "A", "manual_tags": [],
                                 "indexed_tags": [], "date": nested(depth, {})}]}, "reindex": None}
            identities = containers(request)
            self.assertEqual(self.modules[3]["evaluate"](request), {"kind": "refusal", "reason": "invalid-date"})
            self.assertEqual(containers(request), identities)
            request["extra"] = 0
            self.assertEqual(self.modules[3]["evaluate"](request), {"kind": "refusal", "reason": "invalid-request"})
        self.assertEqual(self.modules[3]["evaluate"](nested(4096)), {"kind": "refusal", "reason": "invalid-request"})
        definitions = {}
        for i in range(64):
            body = ["call", f"d{i+1}", ["var", "x"]] if i < 63 else False
            for _ in range(62):
                body = ["not", body]
            definitions[f"d{i}"] = {"params": ["x"], "body": body}
        module, _ = compiled(pinned(..., definitions, "d0"))
        self.assertIs(module["evaluate"](None), False)

    def test_priority_locations_and_data_escaping(self):
        for op in ("unique", "sort", "increasing"):
            module, _ = compiled(pinned(["length", [op, ["var", "x"]]]))
            with self.assertRaises(module["L2RuntimeError"]) as error:
                module["evaluate"](["a" * 4097, "\ud800"])
            self.assertEqual(error.exception.code, "L2_TYPE")
            self.assertEqual(error.exception.location["expression"], "/body/1")
        body = ["let", [["a", ["object", {"x/y~z": ["get", ["var", "x"], "missing"]}]]], ["var", "a"]]
        module, _ = compiled(pinned(body))
        with self.assertRaises(module["L2RuntimeError"]) as error:
            module["evaluate"]({})
        self.assertEqual(error.exception.location["expression"], "/body/1/0/1/1/x~1y~0z")
        text = "'); raise RuntimeError('injection') #\n\\\"\u2028"
        module, _ = compiled(pinned(["literal", {text: [text]}]))
        self.assertEqual(module["evaluate"](None), {text: [text]})

    def test_determinism_identity_and_tamper(self):
        source = self.snapshots[0]
        first = BACKEND.compile_program(source)
        self.assertEqual(first, BACKEND.compile_program(source))
        self.assertEqual(first, BACKEND.compile_program(json.dumps(L2.program_value(source), indent=2)))
        document = json.loads(first)
        self.assertEqual(document["artifact"], digest({k: v for k, v in document.items() if k != "artifact"}))
        corruptions = [first + b"\n", first[:-1], b"{}"]
        for field, value in (("python", document["python"] + "\nraise RuntimeError()\n"),
                             ("generator", "sha256:" + "0" * 64), ("definitions", {}),
                             ("source", self.snapshots[1].digest), ("extra", True)):
            changed = {**document, field: value}
            changed["artifact"] = digest({k: v for k, v in changed.items() if k != "artifact"})
            corruptions.append(canonical(changed))
        for artifact in corruptions:
            with self.assertRaises(BACKEND.ArtifactError):
                BACKEND.verify_artifact(artifact, source)
        with self.assertRaises(BACKEND.ArtifactError):
            BACKEND.verify_artifact(first, self.snapshots[1])


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bagaev-toolchain-test-")
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)
        self.source = ROOT / "examples/l2/catalog.json"
        self.input = ROOT / "examples/l2/catalog-input.json"

    def cli(self, *args, status=0):
        result = subprocess.run([sys.executable, "-B", "-m", "src.bagaev", *map(str, args)],
                                cwd=ROOT, env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, status, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout.count(b"\n"), 1)
        response = json.loads(result.stdout)
        self.assertEqual(response["schema"], "bagaev-toolchain/1")
        self.assertEqual(response["ok"], status == 0)
        self.assertNotIn(str(self.output), result.stdout.decode())
        return response["result"] if status == 0 else response["error"]

    def test_clean_checkout_walkthrough(self):
        before = self.source.read_bytes()
        for flag in ("--help", "--version"):
            result = subprocess.run([sys.executable, "-B", "-m", "src.bagaev", flag], cwd=ROOT,
                                    env={"PATH": os.defpath}, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(result.stdout)
            self.assertEqual(result.stderr, b"")
        self.assertEqual(self.cli("check", self.source)["source"], L2.check_program(before).digest)
        inspected = self.cli("inspect", self.source)
        self.assertEqual([d["id"] for d in inspected["definitions"]], sorted(d["id"] for d in inspected["definitions"]))
        expected = {"kind": "success", "state": {"entries": []}, "entry_ids": []}
        self.assertEqual(self.cli("run", self.source, "--input", self.input)["value"], expected)
        previous = self.source
        for i, name in enumerate(("catalog-01.patch", "catalog-12.patch", "catalog-23.patch"), 1):
            output = self.output / f"a{i}.json"
            self.cli("patch", previous, ROOT / "examples/l2" / name, "--output", output)
            previous = output
        changes = self.cli("diff", self.source, previous)
        self.assertTrue(changes["changed"])
        self.assertGreater(len(changes["pins_changed"]), len(changes["changed"]))
        artifact = self.output / "a3.cpython.json"
        self.cli("compile", previous, "--output", artifact)
        self.assertEqual(self.cli("run", previous, "--input", self.input, "--artifact", artifact)["value"], expected)
        self.assertEqual(self.cli("run", self.source, "--input", self.input, "--artifact", artifact, status=2)["code"], "TOOL_ARTIFACT")
        self.assertEqual(self.cli("patch", self.output / "a1.json", ROOT / "examples/l2/catalog-01.patch",
                                  "--output", self.output / "stale.json", status=2)["code"], "L2_STALE")
        self.assertFalse((self.output / "stale.json").exists())
        self.assertEqual(self.source.read_bytes(), before)

    def test_transport_file_kinds_and_size(self):
        bad = self.output / "bad.json"
        for payload in (b'{"x":0,"x":1}', b'NaN', b'1e9999', b'\xef\xbb\xbfnull',
                        b'[' * 129 + b'null' + b']' * 129, b'1' * 4097,
                        b' ' * 1048577, b'\xff'):
            bad.write_bytes(payload)
            self.assertEqual(self.cli("run", self.source, "--input", bad, status=2)["code"], "TOOL_TRANSPORT")
        for payload in (b'1' * 4096, b'"\\ud800"', b'1.0'):
            bad.write_bytes(payload)
            self.assertEqual(self.cli("run", self.source, "--input", bad)["value"],
                             {"kind": "refusal", "reason": "invalid-request"})
        fifo = self.output / "fifo"
        os.mkfifo(fifo)
        link = self.output / "link"
        link.symlink_to(self.input)
        for path in (fifo, link, self.output, self.output / "absent"):
            self.assertEqual(self.cli("run", self.source, "--input", path, status=2)["code"], "TOOL_INPUT")
        self.assertEqual(self.cli("unknown", status=2)["code"], "TOOL_USAGE")
        self.assertEqual(self.cli("check", status=2)["code"], "TOOL_USAGE")

    def test_exclusive_output_and_tamper_before_execution(self):
        existing = self.output / "existing"
        existing.write_bytes(b"retained")
        link = self.output / "link"
        link.symlink_to(existing)
        for path in (existing, link, self.output):
            self.assertEqual(self.cli("compile", self.source, "--output", path, status=2)["code"], "TOOL_OUTPUT")
        self.assertEqual(existing.read_bytes(), b"retained")
        artifact = self.output / "compiled"
        self.cli("compile", self.source, "--output", artifact)
        artifact.write_bytes(artifact.read_bytes() + b"\n")
        with mock.patch("builtins.compile", side_effect=AssertionError("Unverified execution")):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = CLI.main(["run", str(self.source), "--input", str(self.input), "--artifact", str(artifact)])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(stdout.getvalue())["error"]["code"], "TOOL_ARTIFACT")

    def test_partial_write_cleanup_and_host_failure(self):
        output = self.output / "partial"
        real_write = os.write
        calls = 0
        def broken_write(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_write(fd, data[:7])
            raise OSError(errno.EIO, "synthetic write failure")
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(CLI.os, "write", side_effect=broken_write), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = CLI.main(["compile", str(self.source), "--output", str(output)])
        self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "Toolchain host failure\n")
        self.assertFalse(output.exists())

    def test_diff_typed_structure_and_literal_dependencies(self):
        left, right = self.output / "left", self.output / "right"
        left.write_bytes(canonical(pinned(True)))
        right.write_bytes(canonical(pinned(1)))
        self.assertEqual(self.cli("diff", left, right)["changed"], ["main"])
        left.write_bytes(canonical(pinned(["literal", ["call", "not-a-dependency"]])))
        self.assertEqual(self.cli("inspect", left)["definitions"][0]["dependencies"], [])


if __name__ == "__main__":
    unittest.main()
