"""Read-only packet checks. No compiler, native code or reference process runs."""
import json
import unittest
import native_wide_qualification as q


class PacketTests(unittest.TestCase):
    def test_all_captures_match_frozen_values(self):
        rows = json.loads((q.DATA / "observations.json").read_bytes())["observations"]
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({(x["program"], x["case"]) for x in rows}), 16)
        for row in rows:
            with self.subTest(program=row["program"], case=row["case"]):
                q.packet(row["program"], row["case"])

    def test_harness_is_unadmitted_source(self):
        for program, case in [("sum", "sum"), ("catalog", "sixteen-set")]:
            binding, source, pin, *_ = q.packet(program, case)
            text = q.harness(binding, source, pin, "/checkout/examples/probes/backend/rust")
            self.assertNotIn("{{", text)
            self.assertIn("bagaev_json_view11_kernel", text)
            self.assertIn("checked_json_invocation_v11", text)
            for path in ["relative", "/bad path", "/x/../y", '/x"']:
                with self.assertRaises(ValueError):
                    q.harness(binding, source, pin, path)

    def test_old_magic_binding_and_trailing_data_refuse(self):
        _, _, pin, invocation, _, _, wire = q.packet("sum", "sum")
        for bad in [b"BCMPRES3" + wire[8:],
                    wire[:24] + bytes(32) + wire[56:], wire + b"!"]:
            with self.assertRaises(AssertionError):
                q.decode(invocation["program"], bad, pin)

    def test_comparison_preserves_types(self):
        self.assertFalse(q.same(True, 1))
        self.assertFalse(q.same(120, 120.0))
        self.assertFalse(q.same({"x": [1]}, {"x": [True]}))
        self.assertTrue(q.same({"x": [1]}, {"x": [1]}))


if __name__ == "__main__":
    unittest.main()
