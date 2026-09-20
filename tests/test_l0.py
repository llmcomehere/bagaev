from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bagaev_l0", ROOT / "src" / "bagaev_l0.py")
assert SPEC and SPEC.loader
L0 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = L0
SPEC.loader.exec_module(L0)


def fixture(name: str):
    return L0.loads_json((ROOT / "examples" / "l0" / name).read_bytes())


class L0Tests(unittest.TestCase):
    def assert_code(self, code: str, action) -> None:
        with self.assertRaises(L0.L0Error) as caught:
            action()
        self.assertEqual(caught.exception.code, code)

    def test_original_preserves_order_and_duplicates(self) -> None:
        program = fixture("tag_list.json")
        self.assertEqual(L0.run_program(program, {"tags": ["red", "blue", "red"]}),
                         ["red", "blue", "red"])
        self.assertEqual(L0.run_program(program, {"tags": []}), [])

    def test_patch_is_atomic_and_matches_sorted_set_reference(self) -> None:
        original = fixture("tag_list.json")
        snapshot = copy.deepcopy(original)
        patch = fixture("tag_unique_sorted.patch")
        patched = L0.apply_patch(original, patch)
        self.assertEqual(original, snapshot)
        cases = [[], ["red", "red"], ["red", "blue"], ["blue", "red"],
                 ["red", "blue", "red"], ["blue", "blue"]]
        for tags in cases:
            with self.subTest(tags=tags):
                self.assertEqual(L0.run_program(patched, {"tags": tags}), sorted(set(tags)))

    def test_composed_integer_and_list_operations(self) -> None:
        self.assertEqual(
            L0.run_program(fixture("composed.json"), fixture("composed_inputs.json")),
            4,
        )

    def test_duplicate_key_and_node_id_are_rejected(self) -> None:
        self.assert_code("json.duplicate_key", lambda: L0.loads_json('{"x":1,"x":2}'))
        program = fixture("tag_list.json")
        program["nodes"].append(copy.deepcopy(program["nodes"][0]))
        self.assert_code("node.duplicate", lambda: L0.compile_program(program))

    def test_bad_type_missing_reference_cycle_and_unknown_op_are_rejected(self) -> None:
        program = fixture("tag_list.json")
        self.assert_code("value.type", lambda: L0.run_program(program, {"tags": 3}))

        missing = fixture("tag_list.json")
        missing["nodes"][1]["value"]["ref"] = "absent"
        self.assert_code("reference.missing", lambda: L0.compile_program(missing))

        cyclic = {
            "schema": L0.PROGRAM_SCHEMA,
            "nodes": [
                {"id": "a", "op": "identity", "value": {"ref": "b"}},
                {"id": "b", "op": "identity", "value": {"ref": "a"}},
            ],
            "result": {"ref": "a"},
        }
        self.assert_code("graph.cycle", lambda: L0.compile_program(cyclic))

        unknown = fixture("tag_list.json")
        unknown["nodes"][1]["op"] = "python.eval"
        self.assert_code("operation.unknown", lambda: L0.compile_program(unknown))

    def test_stale_and_invalid_patches_leave_original_unchanged(self) -> None:
        original = fixture("tag_list.json")
        snapshot = copy.deepcopy(original)
        stale = fixture("tag_unique_sorted.patch")
        stale["base"] = "sha256:" + "0" * 64
        self.assert_code("patch.stale", lambda: L0.apply_patch(original, stale))
        self.assertEqual(original, snapshot)

        invalid = fixture("tag_unique_sorted.patch")
        invalid["replace"][0]["value"]["ref"] = "absent"
        self.assert_code("reference.missing", lambda: L0.apply_patch(original, invalid))
        self.assertEqual(original, snapshot)

    def test_integer_overflow_is_rejected(self) -> None:
        program = {
            "schema": L0.PROGRAM_SCHEMA,
            "nodes": [
                {"id": "max", "op": "literal", "type": "int", "value": L0.INT_MAX},
                {"id": "one", "op": "literal", "type": "int", "value": 1},
                {"id": "sum", "op": "int.add", "left": {"ref": "max"},
                 "right": {"ref": "one"}},
            ],
            "result": {"ref": "sum"},
        }
        self.assert_code("integer.overflow", lambda: L0.run_program(program, {}))

    def test_cli_check_run_and_patch_return_documented_schema(self) -> None:
        examples = ROOT / "examples" / "l0"
        commands = (
            ["check", str(examples / "tag_list.json")],
            ["run", str(examples / "tag_list.json"), str(examples / "tag_inputs.json")],
            ["patch", str(examples / "tag_list.json"), str(examples / "tag_unique_sorted.patch")],
        )
        for argv in commands:
            with self.subTest(command=argv[0]):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    returncode = L0.main(argv)
                payload = json.loads(output.getvalue())
                self.assertEqual(returncode, 0)
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["schema"], L0.RESULT_SCHEMA)
                self.assertEqual(payload["command"], argv[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
