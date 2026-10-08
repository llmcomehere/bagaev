"""Data-only checks for the pinned one-function policy change."""
import json
import sys
import unittest
import inventory_json_change_packet as p
sys.path.insert(0, str(p.q.ROOT / "src"))
import bagaev_record_wide_form as form
import bagaev_record_wide_function as function
from bagaev_record_draft import digest


class ChangeTests(unittest.TestCase):
    def test_one_function_draft(self):
        raw = (p.q.ROOT / "examples/probes/inventory-json/Reserve.bagaev").read_bytes()
        base = form.decode(raw)
        pins = json.loads((p.D / "pins.json").read_bytes())
        self.assertEqual(digest(base), pins["base"])
        self.assertEqual(digest(base["functions"]["reserve"]), pins["function"])
        draft = function.replace(raw, (p.D / "ReserveLimited.fragment.bagaev").read_bytes(),
                                 base_sha256=pins["base"], function_sha256=pins["function"])
        expected = form.decode((p.D / "ReserveLimited.bagaev").read_bytes())
        self.assertEqual(draft["target"], pins["target"])
        self.assertEqual(draft["program"], expected)
        self.assertEqual(expected, json.loads((p.D / "program.json").read_bytes()))
        self.assertEqual(draft["delta"], {"add": [], "replace": ["reserve"]})
        self.assertFalse(draft["execution_admission"])
        self.assertEqual([n for n in base["functions"] if base["functions"][n] != expected["functions"][n]], ["reserve"])
        for key in ("schema", "entry", "records", "lists", "variants"):
            self.assertEqual(base[key], expected[key])

    def test_context(self):
        raw = (p.q.ROOT / "examples/probes/inventory-json/Reserve.bagaev").read_bytes()
        context = function.context(raw, "reserve")
        self.assertEqual([x["name"] for x in context["callers"]], ["main"])
        self.assertEqual([x["name"] for x in context["callees"]],
                         ["decrement", "find", "sku_ok", "stock_ok"])

    def test_all_case_bindings(self):
        cases = json.loads((p.D / "cases.json").read_bytes())
        self.assertEqual(len(cases), 37)
        for case in cases:
            with self.subTest(case=case["id"]):
                p.packet(case["id"])


if __name__ == "__main__":
    unittest.main()
