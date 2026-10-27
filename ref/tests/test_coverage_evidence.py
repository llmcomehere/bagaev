"""LNK-08-16/EFF-13 и CHG-12: отсутствие пути при PARTIAL не доказывает независимость.

Графы заданы вручную: producer меняется, неизвестное reads-ребро reader→table может отсутствовать.
По норме reader нельзя исключить; неизменное известное замыкание не переносит прежний PASS.
"""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.change import verify as V
from bagaev_ref.links import certs
from bagaev_ref.links.graph import DEPENDS, Graph
from bagaev_ref.links.impact import impact, why_not


def graph(side="base", changed=False, partial=()):
    nodes = [{"id": name, "name": name, "kind": kind, "file": "app.ts", "span": ["0", "1"],
              "rev": ("2" if changed and name == "producer" else "1") * 64, "pub": False}
             for name, kind in (("producer", "fn"), ("table", "table"), ("reader", "fn"),
                                ("check", "test"), ("rule", "rule"))]
    edges = [{"id": str(i), "kind": kind, "src": src, "dst": dst,
              "site": {"file": "app.ts", "span": ["0", "1"]}, "provenance": {"origin": "structural", "rule": "fixture"}}
             for i, (kind, src, dst) in enumerate((
                 ("writes", "producer", "table"), ("calls", "check", "reader"), ("requires", "reader", "rule")))]
    return Graph({"format": "bagaev-graph/1", "source": "0" * 64, "extractor_rev": "fixture@1",
                  "nodes": nodes, "edges": edges, "gaps": [], "unused_atoms": [],
                  "coverage": {"kinds": {kind: {"status": "PARTIAL" if kind in partial else "COMPLETE",
                                                "basis": "independent fixture"} for kind in DEPENDS},
                               "scope": "fixture", "external_boundaries": []}}, side)


class PartialCoverage(unittest.TestCase):
    def test_partial_on_either_side_keeps_unknown_and_obligations(self):
        for base_partial, cand_partial in ((True, True), (True, False), (False, True)):
            with self.subTest(base=base_partial, candidate=cand_partial):
                base = graph(partial=("reads", "writes") if base_partial else ())
                cand = graph("candidate", changed=True, partial=("reads", "writes") if cand_partial else ())
                result = impact(base, cand)
                self.assertEqual(result["status"], "INCOMPLETE")
                self.assertEqual(result["readiness"], "BLOCKED")
                self.assertEqual(result["excluded_with_basis"], [])
                self.assertEqual(why_not(result, "reader")["outcome"], "UNKNOWN")
                self.assertEqual(why_not(result, "reader")["cause"], "COVERAGE_PARTIAL")
                self.assertEqual({n["id"] for n in result["in_scope"]}, {"producer", "table"})
                self.assertEqual(result["obligations"][0]["status"], "unknown")
                self.assertTrue(result["coverage_gaps"])

    def test_complete_control_still_excludes_with_basis(self):
        result = impact(graph(), graph("candidate", changed=True))
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["unknown"], [])
        self.assertEqual(why_not(result, "reader")["outcome"], "EXCLUDED")

    def test_budget_and_partial_never_restore_exclusion(self):
        for budget in (0, 1, 2, 20):
            result = impact(graph(partial=("reads",)), graph("candidate", changed=True), budget=budget)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(result["excluded_with_basis"], [])

    def test_d83b_cannot_be_created_or_revalidated_with_partial(self):
        complete, partial = graph(), graph(partial=("reads",))
        basis = certs.no_dependency_path(complete, "reader")
        self.assertIsNotNone(basis)
        self.assertIsNone(certs.no_dependency_path(partial, "reader"))
        self.assertEqual(certs.revalidate(basis, complete, "reader")["applicability"], "applicable")
        stale = certs.revalidate(basis, partial, "reader")
        self.assertEqual(stale["applicability"], "stale")
        self.assertIn("coverage", stale["changed"])

    def test_edge_without_coverage_is_unknown(self):
        g = graph()
        del g.coverage["kinds"]["writes"]
        self.assertEqual(certs.incomplete_coverage(g), ["writes"])
        self.assertIsNone(certs.no_dependency_path(g, "reader"))

    def test_missing_calls_without_an_edge_is_still_incomplete(self):
        g = graph()
        g.data["edges"] = [e for e in g.data["edges"] if e["kind"] != "calls"]
        del g.coverage["kinds"]["calls"]
        g = Graph(g.data)
        self.assertEqual(certs.incomplete_coverage(g), ["calls"])
        self.assertIsNone(certs.no_dependency_path(g, "reader"))
        self.assertEqual(impact(g, g)["status"], "INCOMPLETE")
        self.assertEqual(why_not(impact(g, g), "reader")["outcome"], "UNKNOWN")
        g.coverage["kinds"] = {}
        self.assertEqual(certs.incomplete_coverage(g), sorted(DEPENDS))
        self.assertEqual(impact(g, g)["excluded_with_basis"], [])

    def test_ts_profile_allows_only_the_explicit_migrates_omission(self):
        g = graph()
        g.data["extractor_rev"] = "links-ts@1+fixture"
        del g.coverage["kinds"]["migrates"]
        self.assertEqual(certs.incomplete_coverage(g), [])
        self.assertIsNotNone(certs.no_dependency_path(g, "reader"))
        del g.coverage["kinds"]["calls"]
        g.data["edges"] = [e for e in g.data["edges"] if e["kind"] != "calls"]
        self.assertEqual(certs.incomplete_coverage(g), ["calls"])

    def test_no_transfer_from_or_to_partial_closure(self):
        runner = SimpleNamespace(run_tests=lambda _: {"tests": [{"test": "check", "status": "PASS"}]})
        for before, after in ((graph(partial=("reads",)), graph(partial=("reads",))),
                              (graph(), graph(partial=("reads",))),
                              (graph(partial=("reads",)), graph())):
            ev = V.run_evidence({}, before, "before", runner)[0]
            self.assertEqual(V.assess(ev, before, "before")["transfer_basis"], "same-subject")
            self.assertEqual(V.assess(ev, after, "after")["applicability"], "stale")
        ev = V.run_evidence({}, graph(), "before", runner)[0]
        self.assertEqual(V.assess(ev, graph(), "after")["transfer_basis"], "same-closure")
        legacy = copy.deepcopy(ev)
        del legacy["closure_complete"]
        self.assertEqual(V.assess(legacy, graph(), "after")["applicability"], "stale")


if __name__ == "__main__":
    unittest.main()
