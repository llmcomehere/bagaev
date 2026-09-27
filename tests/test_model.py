"""Authored protocol boundaries, not the independent application oracle.

Run only under an independently reviewed execution profile. No provider calls.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from src import bagaev_l2 as L2, bagaev_model as M

ROOT = Path(__file__).resolve().parents[1]


def program(body=0):
    definition = {"params": ["x"], "body": body}
    return {"schema": "bagaev-l2/1", "entry": "main", "definitions": {"main": definition},
            "pins": {"main": M.digest({"schema": "bagaev-l2-definition/1",
                                        "definition": definition, "dependencies": {}})}}


def fields(variant="l2", source=None):
    if source is None:
        source = program() if variant == "l2" else "def evaluate(x):\n    return 0\n"
    return {"schema": M.PACKET, "task": "synthetic", "revision": 1, "run": "repeat-1",
            "step": "change", "attempt": 1, "variant": variant,
            "profile": {"model": "unavailable", "reasoning": "unavailable",
                        "harness": "protocol-tests", "history": "fresh"},
            "base": {"source": M.inspect_source(variant, source)["source"],
                     "checkpoint": 0, "head": None},
            "goal": {"contract": M.digest({"synthetic": True}), "text": "Synthetic change"},
            "source": source, "references": [], "observations": [],
            "continuation": M.continuation_view(next_question="Propose a constant", unresolved=[],
                hypotheses=[], checkpoints=[], effects=[], receipt=None),
            "limits": {"packet_bytes": M.LIMIT, "response_bytes": M.LIMIT,
                       "proposals_left": 2, "wall_ms": 120000}}


def response(packet, add=None, replace=None):
    value = M.read_packet(packet)
    return {"schema": M.RESPONSE, **{k: value[k] for k in
            ("packet_id", "task", "revision", "run", "step", "attempt", "variant", "base")},
            "status": "proposed", "add": {} if add is None else add,
            "replace": {"main": {"params": ["x"], "body": 1}} if replace is None else replace,
            "unresolved": [], "hypotheses": []}


class ModelTests(unittest.TestCase):
    def refuses(self, code, function, *args):
        with self.assertRaises(M.ModelError) as raised:
            function(*args)
        self.assertEqual(raised.exception.code, code)

    def test_transport_refuses_duplicate_keys_bom_float_and_bad_values(self):
        for raw in (b'{"a":1,"a":2}', b'\xef\xbb\xbf{}', b'1.0', b'NaN', b'"\\ud800"'):
            self.refuses("MODEL_FORMAT", M.decode, raw)
        self.refuses("MODEL_BOUND", M.decode, b' ' * (M.LIMIT + 1))
        self.refuses("MODEL_BOUND", M.decode, b'9223372036854775808')
        self.refuses("MODEL_BOUND", M.canonical, [0] * 32768)
        self.refuses("MODEL_BOUND", M.canonical, ["x" * 40000] * 2)
        deep = 0
        for _ in range(129):
            deep = [deep]
        self.refuses("MODEL_BOUND", M.canonical, deep)
        cycle = []
        cycle.append(cycle)
        self.refuses("MODEL_FORMAT", M.canonical, cycle)
        self.refuses("MODEL_FORMAT", M.canonical, {1: "bad key"})
        self.assertEqual(M.decode(M.canonical({"x": [False, None, -1]})), {"x": [False, None, -1]})

    def test_packet_binding_and_detachment(self):
        source = fields()
        before = copy.deepcopy(source)
        packet = M.make_packet(source)
        self.assertEqual(source, before)
        decoded = M.read_packet(packet)
        source["goal"]["text"] = "changed by caller"
        self.assertEqual(decoded["goal"]["text"], before["goal"]["text"])
        decoded["run"] = "another-run"
        self.refuses("MODEL_BINDING", M.read_packet, M.canonical(decoded))
        changed = copy.deepcopy(before)
        changed["base"]["source"] = "sha256:" + "0" * 64
        self.refuses("MODEL_BINDING", M.make_packet, changed)
        changed = copy.deepcopy(before)
        changed["hidden_cases"] = []
        self.refuses("MODEL_FORMAT", M.make_packet, changed)
        changed = copy.deepcopy(before)
        changed["attempt"] = True
        self.refuses("MODEL_FORMAT", M.make_packet, changed)

    def test_responses_bind_every_attempt_and_preserve_scalar_types(self):
        packet = M.make_packet(fields())
        result = response(packet)
        self.assertEqual(M.read_response(packet, M.canonical(result)), result)
        for field, replacement in (("run", "other"), ("attempt", True), ("revision", 2),
                                    ("variant", "python"), ("packet_id", "sha256:" + "0" * 64)):
            changed = copy.deepcopy(result)
            changed[field] = replacement
            self.refuses("MODEL_BINDING", M.read_response, packet, M.canonical(changed))
        changed = copy.deepcopy(result)
        changed["passed"] = True
        self.refuses("MODEL_FORMAT", M.read_response, packet, M.canonical(changed))
        changed = copy.deepcopy(result)
        changed.update(status="cannot_complete", add={}, replace={})
        self.assertEqual(M.read_response(packet, M.canonical(changed))["status"], "cannot_complete")
        self.refuses("MODEL_EDIT", M.propose, packet, M.canonical(changed))

    def test_l2_mechanical_pins_patch_and_old_snapshots(self):
        original = program()
        before = copy.deepcopy(original)
        add = {"helper": {"params": [], "body": 7}}
        replace = {"main": {"params": ["x"], "body": ["call", "helper"]}}
        patch = L2.prepare_patch(original, add, replace)
        candidate = L2.apply_patch(original, patch)
        self.assertEqual(candidate.digest, patch["target"])
        self.assertEqual(L2.evaluate(candidate, None), 7)
        self.assertEqual(L2.evaluate(L2.check_program(original), None), 0)
        self.assertEqual(original, before)
        add["helper"]["body"] = 9
        self.assertEqual(patch["add"]["helper"]["body"], 7)
        invalid = {**patch, "base": "sha256:" + "0" * 64, "add": []}
        with self.assertRaises(L2.L2Error) as raised:
            L2.apply_patch(original, invalid)
        self.assertEqual(raised.exception.code, "L2_PATCH")
        packet = M.make_packet(fields(source=original))
        candidate = M.propose(packet, M.canonical(response(packet)))
        self.assertEqual(candidate["changed"], ["main"])
        self.assertEqual(L2.evaluate(L2.check_program(candidate["source"]), None), 1)

    def test_l2_edit_failures_do_not_mutate_input(self):
        original = program()
        before = copy.deepcopy(original)
        for add, replace, code in (({}, {}, "L2_PATCH"),
                ({"main": {"params": ["x"], "body": 2}}, {}, "L2_PATCH"),
                ({}, {"absent": {"params": ["x"], "body": 2}}, "L2_PATCH"),
                ({}, {"main": {"params": ["x"], "body": ["call", "absent"]}}, "L2_REFERENCE")):
            with self.assertRaises(L2.L2Error) as raised:
                L2.prepare_patch(original, add, replace)
            self.assertEqual(raised.exception.code, code)
            self.assertEqual(original, before)

    def test_python_named_edits_preserve_unrelated_bytes_without_execution(self):
        source = '# leading\nimport os\n\ndef keep():\n    return "é"\n\ndef evaluate(x):\n    return 0\n# trailing\n'
        packet = M.make_packet(fields("python", source))
        replace = {"evaluate": 'def evaluate(x):\n    return helper(x)\n'}
        add = {"helper": 'def helper(x):\n    return [item for item in x]\n'}
        candidate = M.propose(packet, M.canonical(response(packet, add, replace)))
        self.assertTrue(candidate["source"].startswith('# leading\nimport os\n\ndef keep():\n    return "é"\n'))
        self.assertIn('# trailing\n', candidate["source"])
        self.assertEqual(candidate["changed"], ["evaluate", "helper"])
        self.assertEqual(candidate["change"]["base"], M.inspect_source("python", source)["source"])
        self.assertNotEqual(candidate["source_id"], candidate["change"]["base"])
        self.assertEqual(source.count('return 0'), 1)
        # Arbitrary bodies remain data: this is explicitly not an execution sandbox.
        unsafe = 'def evaluate(x):\n    raise RuntimeError("not executed")\n'
        self.assertIn('raise RuntimeError', M.propose(packet,
            M.canonical(response(packet, replace={"evaluate": unsafe})))["source"])

    def test_inspection_bounds_expanded_inventory(self):
        # The source fits transport; unparsing its default adds enough spaces
        # to exceed the aggregate result bound. Nothing is compiled or run.
        source = 'def evaluate(x=[' + ','.join(['0'] * 25000) + ']):\n    return x\n'
        self.assertLess(len(source.encode('utf-8')), M.LIMIT)
        self.refuses("MODEL_BOUND", M.inspect_source, "python", source)
        for variant, value in (("python", "def evaluate(x): return x\n"),
                               ("l2", program())):
            inventory = M.inspect_source(variant, value)
            self.assertLessEqual(len(M.canonical(inventory)), M.LIMIT)
            self.assertEqual(len(inventory["definitions"]), 1)

    def test_inspection_refuses_recursive_signature(self):
        source = 'def evaluate(x=' + '+'.join(['1'] * 400) + '):\n return x\n'
        self.assertEqual(len(source.encode('utf-8')), 827)
        self.refuses("MODEL_SOURCE", M.inspect_source, "python", source)

    def test_python_refuses_ambiguous_and_invalid_edits(self):
        packet = M.make_packet(fields("python"))
        for definition in ('def other(x):\n    return x\n',
                           'def evaluate(x):\n    return x\nvalue = 2\n'):
            self.refuses("MODEL_EDIT", M.propose, packet,
                M.canonical(response(packet, replace={"evaluate": definition})))
        self.refuses("MODEL_SOURCE", M.inspect_source, "python", 'def evaluate(:\n')
        self.refuses("MODEL_SOURCE", M.inspect_source, "python",
                     'def evaluate(x): return x\ndef evaluate(x): return x\n')
        self.refuses("MODEL_SOURCE", M.inspect_source, "python", 'def evaluate(x, y): return x\n')
        both = response(packet, add={"evaluate": 'def evaluate(x): return x\n'},
                        replace={"evaluate": 'def evaluate(x): return x\n'})
        self.refuses("MODEL_EDIT", M.propose, packet, M.canonical(both))

    def test_python_replacement_uses_physical_lines_inside_unicode_docstrings(self):
        for newline in ("\n", "\r\n", "\r"):
            for separator in ("\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
                with self.subTest(newline=repr(newline), separator=repr(separator)):
                    prefix = '"""' + separator.join("abcdef") + '"""' + newline
                    original = 'def evaluate(x):' + newline + '    return 0' + newline
                    suffix = '# untouched tail' + newline + 'KEEP = "unchanged"' + newline
                    source = prefix + original + suffix
                    replacement = ('def evaluate(x):' + newline + '    return 1' + newline
                                   + '# replacement tail  ' + newline + newline)
                    packet = M.make_packet(fields("python", source))
                    candidate = M.propose(packet, M.canonical(response(packet,
                        replace={"evaluate": replacement})))
                    self.assertEqual(candidate["source"], prefix + replacement + suffix)
                    self.assertEqual(candidate["changed"], ["evaluate"])
                    self.assertEqual(candidate["change"]["replace"], {"evaluate": replacement})
                    self.assertEqual(M.read_packet(packet)["source"], source)

    def test_python_replacement_removes_complete_parenthesized_decorators(self):
        decorators = ("@decorator\n", "@(\n    decorator\n)\n",
                      '@(\n    decorator("@")\n)\n@other\n',
                      "@(\n    first @ second\n)\n")
        for newline in ("\n", "\r\n", "\r"):
            for decorator in decorators:
                with self.subTest(newline=repr(newline), decorator=decorator):
                    prefix = '# unchanged prefix' + newline
                    decorated = decorator.replace("\n", newline)
                    source = prefix + decorated + 'def evaluate(x):' + newline + '    return 0' + newline
                    suffix = '# unchanged suffix' + newline
                    source += suffix
                    replacement = '@replacement' + newline + 'def evaluate(x):' + newline + '    return 1' + newline
                    packet = M.make_packet(fields("python", source))
                    candidate = M.propose(packet, M.canonical(response(packet,
                        replace={"evaluate": replacement})))
                    self.assertEqual(candidate["source"], prefix + replacement + suffix)
                    self.assertEqual(M.read_packet(packet)["source"], source)

    def test_continuation_has_no_store_export_or_hidden_case_slot(self):
        value = fields()
        value["continuation"]["cases"] = [{"input": "private", "expected": "private"}]
        self.refuses("MODEL_FORMAT", M.make_packet, value)
        view = M.continuation_view(next_question="Continue", unresolved=["pending"],
            hypotheses=[{"status": "historical", "text": "Older behavior",
                         "sources": [M.digest(0)]}], checkpoints=[],
            effects=[{"id": "outside", "status": "unknown"}], receipt=None)
        self.assertEqual(view["effects"][0]["status"], "unknown")
        value = fields()
        value["continuation"]["receipt"] = {"operation": "op", "status": "absent", "source": M.digest(0)}
        self.refuses("MODEL_FORMAT", M.make_packet, value)

    def test_attempt_exact_replay_conflict_and_oversize_receipt(self):
        packet = M.make_packet(fields())
        raw = b"invalid response"
        receipt = {"digest": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        rows = M.append_attempt([], packet, receipt, "rejected")
        self.assertEqual(M.append_attempt(rows, packet, receipt, "rejected"), rows)
        self.refuses("MODEL_REPLAY", M.append_attempt, rows, packet, receipt, "received")
        changed = {**receipt, "bytes": 1000000}
        self.refuses("MODEL_REPLAY", M.append_attempt, rows, packet, changed, "rejected")
        self.assertEqual(M.append_attempt([], packet, changed, "rejected")[0]["response"], changed)
        self.assertEqual(M.append_attempt([], packet, None, "timeout")[0]["outcome"], "timeout")
        self.refuses("MODEL_FORMAT", M.append_attempt, [], packet, None, "received")
        self.refuses("MODEL_REPLAY", M.append_attempt, rows + rows, packet, receipt, "rejected")

    def test_cost_unknown_missing_and_nonoverlapping_categories(self):
        rows = [{"schema": M.COST, "id": str(i), "category": category,
                 "unit": "usd_micros", "amount": i + 1, "basis": "expense-" + str(i)}
                for i, category in enumerate(("preparation", "attempts", "maintenance", "operation"))]
        result = M.cost_totals(rows)["usd_micros"]
        self.assertEqual((result["C_dev"], result["C_full"]), (3, 10))
        rows[0]["amount"] = None
        self.assertIsNone(M.cost_totals(rows)["usd_micros"]["C_full"])
        self.assertIsNone(M.cost_totals(rows[1:])["usd_micros"]["preparation"])
        self.assertEqual(M.cost_totals([]), {})
        duplicate = {**rows[1], "id": "other", "category": "operation"}
        self.refuses("MODEL_COST", M.cost_totals, rows + [duplicate])
        duplicate = {**rows[1], "basis": "different"}
        self.refuses("MODEL_COST", M.cost_totals, rows + [duplicate])

    def test_standalone_example_and_unsolved_seed_sources(self):
        example = json.loads((ROOT / "examples/model/protocol-example.json").read_text())
        packet = M.make_packet(example["packet_fields"])
        value = {**example["response_fields"], "packet_id": M.read_packet(packet)["packet_id"]}
        candidate = M.propose(packet, M.canonical(value))
        self.assertEqual(candidate["changed"], ["evaluate"])
        seeds = json.loads((ROOT / "examples/model/seeds.json").read_text())
        for task in ("calibration", "control", "queue"):
            for variant in ("python", "l2"):
                self.assertTrue(M.inspect_source(variant, seeds[task][variant])["source"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
