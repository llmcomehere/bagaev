"""Data-only checks of frozen followthrough packets; no native execution."""
import json
import unittest
import native_wide_followthrough as f


class FollowthroughTests(unittest.TestCase):
    def test_initial_state_and_required_predecessors(self):
        initial = f.continuation_request("normalize", None)
        self.assertTrue(f.q.same(initial["arguments"][0], f.cases()[0]["request"]))
        for case in f.cases()[1:]:
            with self.assertRaises(ValueError):
                f.continuation_request(case["id"], None)
        with self.assertRaises(ValueError):
            f.continuation_request("normalize", b"unexpected")

    def test_refusal_keeps_last_success(self):
        cases = {x["id"]: x for x in f.cases()}
        self.assertEqual(cases["origin-refusal"]["previous_success"], "clear-first")
        self.assertEqual(cases["resume-last-success"]["previous_success"], "clear-first")
        self.assertTrue(f.q.same(cases["clear-first"]["expected"]["state"],
                                cases["resume-last-success"]["request"]["state"]))

    def test_five_failure_packets(self):
        rows = json.loads((f.DATA / "failure-expectations.json").read_bytes())
        self.assertEqual(len(rows), 5)
        for row in rows:
            with self.subTest(case=row["id"]):
                packet = f.failure_packet(row["id"])
                self.assertEqual(len(packet[-1]), 32)
                source = f.failure_harness(row["id"], "/checkout/backend")
                self.assertIn("assert_eq!(bytes.len(),32)", source)
                self.assertNotIn("{{", source)
                self.assertEqual(packet[0]["expected"]["work"], row["native_metadata"]["work"])

    def test_work_limit_literal(self):
        row = f.failure_packet("work-limit")[0]
        self.assertEqual(row["expected"]["work"], 65536)
        self.assertEqual(row["native_metadata"]["location"], 7)
        costs = [18, 290, 4642, 74274]
        self.assertEqual(costs[1:], [2 + 16 * x for x in costs[:-1]])
        self.assertEqual(2 + 14 * 4642 + 2 + 290 + 2 + 14 * 18, 65536)


if __name__ == "__main__":
    unittest.main()
