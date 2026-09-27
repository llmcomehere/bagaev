"""Literal L2 acceptance plus depth/ownership/priority regressions.

Fixtures and expected values are independent of the evaluator. This module has
no authority to run itself; a maintained execution profile is a separate gate.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bagaev_l2", ROOT / "src/bagaev_l2.py")
L2 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = L2
SPEC.loader.exec_module(L2)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True,
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def pinned(body, definitions=None, entry="main"):
    """Independent literal-data identity construction, never evaluator output."""
    definitions = copy.deepcopy(definitions or {})
    if body is not ...:
        definitions["main"] = {"params": ["x"], "body": body}
    graph = {}
    for name, definition in definitions.items():
        calls, pending = set(), [definition["body"]]
        while pending:
            item = pending.pop()
            if type(item) is list:
                if item and item[0] == "literal":
                    continue
                if item and item[0] == "call":
                    calls.add(item[1])
                pending.extend(item)
            elif type(item) is dict:
                pending.extend(item.values())
        graph[name] = calls
    pins = {}
    while len(pins) < len(definitions):
        ready = [k for k, deps in graph.items() if k not in pins and deps <= pins.keys()]
        if not ready:
            break  # Invalid reference/cycle cases are checked before pin validity.
        for k in ready:
            pins[k] = digest({"schema": "bagaev-l2-definition/1",
                "definition": definitions[k], "dependencies": {d: pins[d] for d in graph[k]}})
    return {"schema": "bagaev-l2/1", "entry": entry, "definitions": definitions, "pins": pins}


def same(a, b):
    todo = [(a, b)]
    while todo:
        left, right = todo.pop()
        if type(left) is not type(right):
            return False
        if type(left) is dict:
            if left.keys() != right.keys():
                return False
            todo.extend((left[k], right[k]) for k in left)
        elif type(left) is list:
            if len(left) != len(right):
                return False
            todo.extend(zip(left, right))
        elif left != right:
            return False
    return True


def containers(value):
    todo, found = [value], set()
    while todo:
        item = todo.pop()
        if type(item) in (dict, list):
            if id(item) in found:
                continue
            found.add(id(item))
            todo.extend(item.values() if type(item) is dict else item)
    return found


def nested(n, leaf=None):
    for _ in range(n):
        leaf = [leaf]
    return leaf


def unchecked(body):
    """A complete envelope for failures that must precede pin validation."""
    return {"schema":"bagaev-l2/1", "entry":"main", "pins":{},
            "definitions":{"main":{"params":["x"], "body":body}}}


def boundary(case):
    """Finite constructions fixed by oracle prose, including literal outcomes."""
    name = case["id"]
    body, arg = case.get("body"), None
    if name.startswith("ARRAY-"):
        arg = [None] * (256 if name == "ARRAY-MAX" else 257)
    elif name in ("STRING-MAX", "STRING-OVER"):
        arg = "a" * (4096 if name == "STRING-MAX" else 4097)
    elif name == "UTF8-OVER":
        arg = "é" * 2049
    elif name == "STRING-UNICODE-BEFORE-BOUND":
        arg = {"a": "a" * 4097, "b": "\ud800"}
    elif name.startswith("EXPORT-DEPTH-"):
        arg = nested(63 if name.endswith("MAX") else 64)
    elif name.startswith("EXPRESSION-DEPTH-"):
        body = False
        for _ in range(63 if name.endswith("MAX") else 64):
            body = ["not", body]
    elif name.startswith("STEP-"):
        arg = [None] * (45 if name == "STEP-UNDER" else 46)
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
        arg = [[None] * 255 for _ in range(256)]
        if name.endswith("MAX"):
            arg[0].pop()
    elif name.startswith("EXPORT-BYTES-"):
        arg = ["a" * 4096] * 255 + ["a" * (3327 if name.endswith("MAX") else 3328)]
    elif name.startswith("JSON-BYTES-"):
        data = json.dumps(pinned(["var", "x"]), ensure_ascii=False, separators=(",", ":")).encode()
        return data + b" " * (1048576 + (name.endswith("OVER")) - len(data)), None
    else:
        raise AssertionError("unimplemented boundary")
    return pinned(body), arg


class L2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = read("examples/l2/oracle.json")
        cls.app = read("examples/beta/catalog-cases.json")
        cls.a0 = read("examples/l2/catalog.json")
        cls.patches = [read("examples/l2/" + name) for name in
                       ("catalog-01.patch", "catalog-12.patch", "catalog-23.patch")]
        cls.snapshots = [L2.check_program(cls.a0)]
        for patch in cls.patches:
            cls.snapshots.append(L2.apply_patch(cls.snapshots[-1], patch))

    def code(self, code, fn):
        with self.assertRaises(L2.L2Error) as error:
            fn()
        self.assertEqual(error.exception.code, code)

    def observation(self, program, arg, expected):
        before = copy.deepcopy(arg)
        first = L2.evaluate(program, arg)
        second = L2.evaluate(program, arg)
        self.assertTrue(same(first, expected))
        self.assertTrue(same(second, expected))
        self.assertTrue(same(before, arg))
        self.assertFalse(containers(arg) & containers(first))
        self.assertFalse(containers(first) & containers(second))
        return first

    def test_expression_oracle(self):
        self.assertEqual(len(self.oracle["expressions"]), 42)
        for case in self.oracle["expressions"]:
            with self.subTest(case=case["id"]):
                program = L2.check_program(pinned(case["body"], case.get("definitions")))
                if "error" in case:
                    self.code(case["error"], lambda: L2.evaluate(program, case["argument"]))
                else:
                    self.observation(program, case["argument"], case["value"])

    def test_checking_oracle(self):
        self.assertEqual(len(self.oracle["checking"]), 12)
        for case in self.oracle["checking"]:
            with self.subTest(case=case["id"]):
                name = case["id"]
                if "body" in case:
                    # Invalid surrogate literals cannot be hashed and are rejected before pins.
                    program = ({"schema": "bagaev-l2/1", "entry": "main", "pins": {},
                        "definitions": {"main": {"params": ["x"], "body": case["body"]}}}
                        if name == "SURROGATE-LITERAL" else pinned(case["body"]))
                elif "text" in case:
                    program = case["text"]
                else:
                    program = copy.deepcopy(self.a0)
                    if name == "NO-PIN":
                        del program["pins"]["normalize"]
                    else:
                        program["definitions"]["normalize"]["body"] = ["literal", []]
                        if name == "TRANSITIVE-TAMPER":
                            program["pins"]["normalize"] = digest({"schema":"bagaev-l2-definition/1",
                                "definition":program["definitions"]["normalize"],"dependencies":{}})
                self.code(case["error"], lambda: L2.check_program(program))

    def test_patch_oracle(self):
        self.assertEqual(len(self.oracle["patches"]), 10)
        for case in self.oracle["patches"]:
            with self.subTest(case=case["id"]):
                original = self.snapshots[int(case["original"][1])]
                patch = read("examples/l2/" + case["patch"])
                name = case["id"]
                if name == "INVALID-TARGET": patch["target"] = "sha256:" + "0" * 64
                elif name == "MALFORMED-TARGET": patch["target"] = "sha256" + "0" * 64
                elif name == "INVALID-CHANGE": patch["replace"]["normalize"]["body"] = ["future.op"]
                elif name == "ADD-EXISTING": patch["add"]["normalize"] = patch["replace"].pop("normalize")
                elif name == "REPLACE-MISSING": patch["replace"]["absent"] = patch["replace"].pop("normalize")
                elif name == "DUPLICATE-EDIT": patch["add"]["normalize"] = copy.deepcopy(patch["replace"]["normalize"])
                elif name == "ATOMIC-FAILURE": patch["replace"]["normalize"]["body"] = ["call","main",["var","tags"]]
                before, patch_before = original.canonical, copy.deepcopy(patch)
                if "error" in case:
                    self.code(case["error"], lambda: L2.apply_patch(original, patch))
                else:
                    result = L2.apply_patch(original, patch)
                    self.assertEqual(result.digest, self.snapshots[1].digest)
                self.assertEqual(original.canonical, before)
                self.assertTrue(same(patch, patch_before))
        self.assertEqual(L2.evaluate(self.snapshots[0], self.app["requests"]["EMPTY-1"]),
                         {"kind":"refusal","reason":"invalid-request"})

    def test_boundary_oracle(self):
        self.assertEqual(len(self.oracle["boundaries"]), 23)
        for case in self.oracle["boundaries"]:
            with self.subTest(case=case["id"]):
                program, arg = boundary(case)
                def action():
                    checked = L2.check_program(program)
                    return checked if "check" in case else L2.evaluate(checked, arg)
                if "error" in case:
                    self.code(case["error"], action)
                else:
                    actual = action()
                    if "check" not in case:
                        self.assertTrue(same(actual, case.get("value", arg)))
                        self.assertFalse(containers(actual) & containers(arg))

    def _catalog(self, revisions):
        self.assertEqual(len(self.app["cases"]), 99)
        for revision in revisions:
            for case in self.app["cases"]:
                with self.subTest(program=revision, case=case["id"]):
                    request = self.app["requests"][case["request"]]
                    selected = request.get("behavior_revision") if type(request) is dict else None
                    expected = self.app["responses"][case["expect"]]
                    if type(selected) is int and 0 <= selected <= 3 and selected > revision:
                        expected = {"kind":"refusal","reason":"invalid-request"}
                    result = self.observation(self.snapshots[revision], request, expected)
                    if result["kind"] == "success":
                        replay = {**request, "state": result["state"]}
                        self.observation(self.snapshots[revision], replay, expected)

    def test_catalog_a0_a1(self): self._catalog((0, 1))
    def test_catalog_a2_a3(self): self._catalog((2, 3))

    def test_actual_evolution(self):
        cases = {c["id"]: c for c in self.app["cases"]}
        for revisions in ((0, 1, 2, 3), (3, 3, 3, 3)):
            previous = None
            for revision, name in zip(revisions, self.app["chains"][0]["cases"]):
                case = cases[name]
                request = copy.deepcopy(self.app["requests"][case["request"]])
                if previous is not None:
                    self.assertTrue(same(previous, request["state"]))
                    request["state"] = previous
                previous = self.observation(self.snapshots[revision], request,
                    self.app["responses"][case["expect"]])["state"]
            replay = {**self.app["requests"]["REPLAY-OLDER"], "state": previous}
            self.observation(self.snapshots[3], replay, self.app["responses"]["REPLAY-OLDER"])

    def test_deep_callable_inputs(self):
        calls = 0
        for n in (0, 64, 65, 4096):
            request = {"interface":"catalog-application/2","behavior_revision":3,
                "state":{"entries":[{"id":"a","title":"A","manual_tags":[],
                "indexed_tags":[],"date":nested(n,{})}]},"reindex":None}
            for extra, reason in ((False,"invalid-date"),(True,"invalid-request")):
                if extra: request["extra"] = 0
                ids = containers(request)
                result = L2.evaluate(self.snapshots[3], request)
                self.assertEqual(result, {"kind":"refusal","reason":reason})
                self.assertEqual(ids, containers(request))
                calls += 1
        for n in (64,65,4096):
            self.assertEqual(L2.evaluate(self.snapshots[3],nested(n)),
                             {"kind":"refusal","reason":"invalid-request"})
            calls += 1
        self.assertEqual(calls,11)

    def test_combined_legal_depths(self):
        definitions = {}
        for i in range(64):
            body = ["call", f"d{i+1}", ["var","x"]] if i < 63 else False
            for _ in range(62): body = ["not", body]
            definitions[f"d{i}"] = {"params":["x"],"body":body}
        program = L2.check_program(pinned(..., definitions, "d0"))
        self.assertIs(L2.evaluate(program,None),False)

    def test_immutable_snapshot(self):
        source = pinned(["literal",{"a":[1]}])
        checked = L2.check_program(source)
        source["definitions"]["main"]["body"][1]["a"].append(2)
        view = L2.program_value(checked)
        view["definitions"]["main"]["body"][1]["a"].append(3)
        result = L2.evaluate(checked,None)
        result["a"].append(4)
        self.assertEqual(L2.evaluate(checked,None),{"a":[1]})
        self.assertIs(type(checked.canonical),bytes)
        with self.assertRaises((AttributeError,TypeError)):
            checked.canonical = b"{}"
        self.code("L2_PROGRAM",lambda:L2.evaluate(L2.CheckedProgram(b"{}"),None))

    def test_priorities_and_all_branches(self):
        program = pinned(["var","missing"])
        program["definitions"]["z"] = {"params":[],"body":["unknown"]}
        self.code("L2_PROGRAM",lambda:L2.check_program(program))
        for op in ("sort","unique","increasing"):
            checked = L2.check_program(pinned([op,["var","x"]]))
            self.code("L2_TYPE",lambda:L2.evaluate(checked,["a"*4097,"\ud800"]))
        checked = L2.check_program(pinned(["sort.by",["var","x"],"v",["var","v"]]))
        self.code("L2_TYPE",lambda:L2.evaluate(checked,[["a"*4097,"\ud800"]]))

    def test_value_program_is_not_text_transport(self):
        literal = ["a"*4096]*255 + ["a"*3327]
        source = pinned(0, {"unused":{"params":[],"body":["literal",literal]}})
        checked = L2.check_program(source)
        self.assertGreater(len(checked.canonical),1048576)
        self.assertEqual(L2.evaluate(checked,None),0)
        self.code("L2_BOUNDS",lambda:L2.check_program(checked.canonical))
        with self.assertRaises((AttributeError,TypeError)):
            object.__setattr__(checked,"canonical",b"{}")

    def test_deep_program_text_and_values(self):
        text = json.dumps(pinned(None)).replace('"body": null',
            '"body": ["literal",' + "["*4096 + "null" + "]"*4096 + "]")
        self.code("L2_BOUNDS",lambda:L2.check_program(text))
        self.code("L2_JSON",lambda:L2.check_program(text[:-1]))
        bad = {"schema":"bagaev-l2/1","entry":"main","pins":{},
               "definitions":{"main":{"params":["x"],"body":["literal",nested(4096)]}}}
        self.code("L2_BOUNDS",lambda:L2.check_program(bad))

    def test_large_integer_check_phases(self):
        wrong_schema = unchecked(10**20)
        wrong_schema["schema"] = "wrong"
        for source in (wrong_schema, json.dumps(wrong_schema)):
            self.code("L2_PROGRAM", lambda: L2.check_program(source))
        raw = json.dumps(unchecked(0), separators=(",", ":"))
        digits = "1" + "0" * 9999
        for token in (digits, "-" + digits):
            source = raw.replace('"body":0', '"body":' + token)
            self.code("L2_BOUNDS", lambda: L2.check_program(source))
        huge = raw.replace('"body":0', '"body":' + digits)
        self.code("L2_JSON", lambda: L2.check_program(huge[:-1]))
        duplicate = raw.replace('"body":0', '"body":' + digits + ',"body":0')
        self.code("L2_JSON", lambda: L2.check_program(duplicate))
        bad_pin = unchecked(0)
        bad_pin["pins"]["main"] = 10**20
        self.code("L2_PIN", lambda: L2.check_program(bad_pin))
        pin_text = raw.replace('"pins":{}', '"pins":{"main":' + digits + '}')
        self.code("L2_PIN", lambda: L2.check_program(pin_text))
        for value in (-(1 << 63), (1 << 63) - 1):
            self.assertIsInstance(L2.check_program(json.dumps(pinned(value))), L2.CheckedProgram)

    def test_call_arity_check_phase(self):
        definitions = {"f":{"params":list("abcdefgh"), "body":0}}
        self.assertIsInstance(L2.check_program(pinned(["call", "f"] + [0]*8,
                                                     definitions)), L2.CheckedProgram)
        for first, code in ((0, "L2_REFERENCE"), (["unknown"], "L2_PROGRAM"),
                            (1 << 63, "L2_BOUNDS")):
            source = unchecked(["call", "f", first] + [0]*8)
            source["definitions"].update(copy.deepcopy(definitions))
            self.code(code, lambda: L2.check_program(source))

    def test_text_interval_count_phase(self):
        first = [[i, i] for i in range(16)]
        body = ["text", ["var", "x"], 0, 1, first, [[0, 127]]]
        self.assertIsInstance(L2.check_program(pinned(body)), L2.CheckedProgram)
        cases = ((first + [[16, 16]], [[0, 127]], "L2_BOUNDS"),
                 (first, first + [[16, 16]], "L2_BOUNDS"),
                 ([], [[0, 127]], "L2_BOUNDS"),
                 ({}, [[0, 127]], "L2_PROGRAM"),
                 ([0], [[0, 127]], "L2_PROGRAM"),
                 ([0] + first, [[0, 127]], "L2_BOUNDS"))
        for intervals, rest, code in cases:
            source = unchecked(["text", ["var", "x"], 0, 1, intervals, rest])
            self.code(code, lambda: L2.check_program(source))

    def test_shape_count_before_keys(self):
        keys = ["k" + str(i) for i in range(32)]
        self.assertIsInstance(L2.check_program(pinned(["shape", ["var", "x"],
                                                      keys, []])), L2.CheckedProgram)
        cases = ((keys, ["extra"], "L2_BOUNDS"),
                 (keys, [0], "L2_BOUNDS"),
                 (keys[:-1], [0], "L2_PROGRAM"),
                 ([], 0, "L2_PROGRAM"),
                 (keys, ["k0"], "L2_BOUNDS"))
        for required, optional, code in cases:
            source = unchecked(["shape", ["var", "x"], required, optional])
            self.code(code, lambda: L2.check_program(source))


if __name__ == "__main__":
    unittest.main()
