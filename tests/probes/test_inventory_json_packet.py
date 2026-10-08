"""Source/data checks only. No reference or native process launch."""
import json
import sys
import unittest
import inventory_json_packet as p

sys.path.insert(0, str(p.q.ROOT / "src"))
import bagaev_record_wide_form as form


class InventoryPacketTests(unittest.TestCase):
    def test_source_roundtrip_and_unchanged_business(self):
        source = (p.D / "Reserve.bagaev").read_bytes()
        new = form.decode(source)
        self.assertEqual(new, form.decode(form.encode(new)))
        old = form.decode((p.q.ROOT / "examples/probes/inventory-reserve/Reserve.bagaev").read_bytes())
        for key in ("records", "lists", "variants"):
            self.assertEqual(old[key], new[key])
        for name, function in old["functions"].items():
            self.assertEqual(function, new["functions"][name])
        self.assertEqual(new, json.loads((p.D / "program.json").read_bytes()))

    def test_all_packets(self):
        cases = json.loads((p.D / "cases.json").read_bytes())
        self.assertEqual(len(cases), 32)
        for case in cases:
            with self.subTest(case=case["id"]):
                packet = p.packet(case["id"])
                self.assertTrue(p.q.same(packet[1]["arguments"], [case["request"]]))

    def test_explicit_cap_mapping(self):
        case = p.packet("seventeen")[0]
        self.assertEqual(len(case["request"]["stock"]), 17)
        self.assertEqual(case["value"], {"case": "Rejected", "value": "request-shape"})

    def test_harness_and_type_comparison(self):
        _, _, binding, source, pin, _ = p.packet("partial")
        text = p.q.harness(binding, source, pin, "/checkout/backend")
        self.assertNotIn("{{", text)
        self.assertIn("const ARG_COUNT:usize=1;", text)
        self.assertFalse(p.q.same(True, 1))


if __name__ == "__main__":
    unittest.main()
