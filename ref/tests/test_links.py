"""LINKS-1: детерминизм графа и отчёта, только чтение (T14-C01), страницы ContextPack без потери обязательств
(T11-C04, T11-C05), монотонность бюджета и продолжение без потерь (T09-C03), декларации — не факты (T08-C02).
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))
sys.setrecursionlimit(100000)

from bagaev_ref.kernel import canonical as C  # noqa: E402
from bagaev_ref.links.context import context_pack  # noqa: E402
from bagaev_ref.links.extract import extract  # noqa: E402
from bagaev_ref.links.graph import Graph  # noqa: E402
from bagaev_ref.links.impact import impact  # noqa: E402
from bagaev_ref.machine.runner import prepare  # noqa: E402

APP = ROOT / "examples" / "authorship"


def files_of(root: Path):
    return [(f.relative_to(root).as_posix(), f.read_bytes()) for f in sorted(root.rglob("*.bag"))]


def graph(root: Path, side: str):
    fs = files_of(root)
    project, prog, pre = prepare(fs)
    assert pre is None, pre
    return Graph(extract(project, prog, fs), side), dict(fs)


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="bag-links-"))
        cls.cand = cls.tmp / "cand"
        shutil.copytree(APP, cls.cand)
        f = cls.cand / "blog" / "authorship.bag"
        f.write_text(f.read_text(encoding="utf-8").replace("    Authors(xs) => xs,", "    Authors(xs) => seq.concat(xs, []),"),
                     encoding="utf-8")
        cls.base, cls.bf = graph(APP, "base")
        cls.cg, cls.cf = graph(cls.cand, "candidate")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class Determinism(Fixture):
    def test_graph_and_report_are_byte_stable(self):
        g1, _ = graph(APP, "base")
        self.assertEqual(C.encode(g1.data), C.encode(self.base.data))
        r1 = impact(self.base, self.cg)
        r2 = impact(*(graph(APP, "base")[0], graph(self.cand, "candidate")[0]))
        self.assertEqual(json.dumps(r1, sort_keys=True), json.dumps(r2, sort_keys=True))

    def test_declarations_are_not_facts(self):
        for e in self.base.data["edges"]:
            if e["kind"] in ("implements", "requires", "checks", "about", "derived_from", "supersedes"):
                self.assertEqual(e["provenance"]["origin"], "declared")
        r = impact(self.base, self.cg)
        self.assertTrue({o["status"] for o in r["obligations"]} <= {"open", "unknown", "excluded_with_basis"})


class Budget(Fixture):
    def test_frontier_monotone_and_resumable(self):
        full = impact(self.base, self.cg)
        full_scope = {x["id"] for x in full["in_scope"]}
        prev = set()
        for k in range(0, 12):
            r = impact(self.base, self.cg, budget=k)
            scope = {x["id"] for x in r["in_scope"]}
            self.assertTrue(prev <= scope <= full_scope, k)       # больше бюджета — не меньше области
            self.assertTrue({x["id"] for x in r["frontier"]} <= full_scope, k)   # frontier — будущая область
            if r["status"] == "INCOMPLETE":
                self.assertEqual(r["excluded_with_basis"], [])     # без полного замыкания исключений нет
                self.assertEqual(r["readiness"], "BLOCKED")
            prev = scope
        self.assertEqual(impact(self.base, self.cg, budget=1000)["in_scope"], full["in_scope"])


class Context(Fixture):
    def test_pages_cover_everything_and_keep_obligations(self):
        r = impact(self.base, self.cg)
        whole = context_pack(r, self.base, self.cg, self.bf, self.cf, 100000)
        self.assertTrue(whole["ready_for_step"])
        env = whole["envelope"]
        seen, cursor, pages = [], 0, 0
        budget = len(C.encode(env)) // 4 + 400
        while True:
            p = context_pack(r, self.base, self.cg, self.bf, self.cf, budget, cursor)
            self.assertEqual(p["envelope"], env)                    # обязательства в каждой странице
            self.assertLessEqual(p["used"], budget)
            seen += [i["id"] for i in p["items"]]
            pages += 1
            if p["next_cursor"] is None:
                break
            self.assertFalse(p["ready_for_step"])
            self.assertIn("CONTEXT_INCOMPLETE", p["blockers"])
            self.assertGreater(p["next_cursor"], cursor)
            cursor = p["next_cursor"]
        self.assertGreater(pages, 1)
        self.assertEqual(seen, [i["id"] for i in whole["items"]])    # тот же порядок, без пропусков и повторов
        self.assertEqual(whole["measure"], "utf8-bytes/4@1")


class ReviewM5(Fixture):
    """Регрессии ревью m5 (registry/reviews/m5.md)."""

    def test_later_pages_never_ready_and_large_item_progresses(self):
        r = impact(self.base, self.cg)
        env_tokens = len(C.encode(context_pack(r, self.base, self.cg, self.bf, self.cf, 100000)["envelope"])) // 4
        p2 = context_pack(r, self.base, self.cg, self.bf, self.cf, 100000, cursor=3)
        self.assertFalse(p2["ready_for_step"])                     # курсор > 0: не вся картина
        small = env_tokens + 120                                    # меньше самого крупного элемента
        cursor, seen = 0, 0
        for _ in range(200):
            p = context_pack(r, self.base, self.cg, self.bf, self.cf, small, cursor)
            if p["outcome"] != "CONTEXT":
                break
            self.assertLessEqual(p["used"], small)
            seen += len(p["coverage"])
            if p["next_cursor"] is None:
                break
            self.assertGreater(p["next_cursor"], cursor)            # прогресс есть всегда (M3)
            cursor = p["next_cursor"]
        else:
            self.fail("страницы не кончаются")

    def test_interface_certificate_revalidation(self):
        from bagaev_ref.links import certs
        case = ROOT / "conformance" / "cases" / "impact" / "certificate-interface-01"
        b, _ = graph(case, "base") if False else (None, None)
        files = [(f.relative_to(case).as_posix(), f.read_bytes()) for f in sorted(case.rglob("*.bag"))]

        def g(prefix, text=None):
            fs = [(n[len(prefix):], x) for n, x in files if (n.startswith(prefix) if prefix else "/" not in n)]
            if text is not None:
                fs = [(n, text(x.decode()).encode()) for n, x in fs]
            project, prog, pre = prepare(fs)
            assert pre is None, pre
            return Graph(extract(project, prog, fs), prefix or "base")
        base, cand = g(""), g("cand/")
        ev = {"app.origin_positive": "PASS"}
        r = impact(base, cand, evidence=ev)
        closed = [o for o in r["obligations"] if o.get("reason") == "D83a-interface-contract"]
        self.assertEqual(len(closed), 1)
        basis = closed[0]["basis"]
        self.assertEqual(certs.revalidate(basis, cand, basis["dependent"])["applicability"], "applicable")
        weak = g("cand/", lambda t: t.replace('test.expect("x", origin(1).x > 0)', 'test.expect("x", true)'))
        self.assertEqual(certs.revalidate(basis, weak, basis["dependent"])["applicability"], "stale")
        other = g("cand/", lambda t: t.replace("store.put(S.totals, name, origin(1).x);",
                                                "store.put(S.totals, name, origin(2).x);"))
        self.assertEqual(certs.revalidate(basis, other, basis["dependent"])["applicability"], "stale")

    def test_example_graph_has_migrates_and_schema(self):
        self.assertIn(("migrates", "blog.migration.authors_list", "blog.db.Blog.articles"),
                      {(e["kind"], self.base.nodes[e["src"]]["name"], self.base.nodes.get(e["dst"], {}).get("name"))
                       for e in self.base.data["edges"]})
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema нет: схему проверяет tools/check.py --exec")
        v = jsonschema.Draft202012Validator(json.loads((ROOT / "spec/links/graph.schema.json").read_text(encoding="utf-8")))
        self.assertEqual([e.message for e in v.iter_errors(self.base.data)], [])


class ReadOnly(Fixture):
    """T14-C01: просмотр не исполняет программу и не пишет файлов — и на некорректном вводе."""

    def snapshot(self, root: Path):
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}

    def run_cli(self, argv):
        from bagaev_ref import cli
        from bagaev_ref.machine import cek
        orig, calls = cek.run, []

        def forbidden(*a, **k):
            calls.append(1)
            raise AssertionError("программа исполнена")
        cek.run = forbidden
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = cli.main(argv)
        finally:
            cek.run = orig
        return rc, out.getvalue(), calls

    def test_views_do_not_execute_or_write(self):
        work = self.tmp / "ro"
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(APP, work / "base")
        shutil.copytree(self.cand, work / "cand")
        broken = work / "broken"
        shutil.copytree(APP, broken)
        (broken / "blog" / "byline.bag").write_text("module", encoding="utf-8")
        before = self.snapshot(work)
        b, c = str(work / "base"), str(work / "cand")
        commands = [
            ["graph", b, "--json"],
            ["relations", b, "blog.byline.byline", "--json"],
            ["relations", b, "nonexistent.entity", "--json"],
            ["impact", b, c, "--json"],
            ["impact", b, c, "--analysis-budget", "1", "--unavailable", "qcp1fw", "--json"],
            ["context", b, c, "--budget", "500", "--json"],
            ["context", b, c, "--budget", "5", "--json"],
            ["why", b, c, "blog.image.resize", "--not-affected", "--recheck", c, "--json"],
            ["why", b, c, "blog.byline.byline", "--affected", "--json"],
            ["graph", str(broken), "--json"],
            ["impact", b, str(broken), "--json"],
            ["graph", str(work / "missing"), "--json"],
        ]
        for argv in commands:
            rc, out, calls = self.run_cli(argv)
            self.assertEqual(calls, [], argv)
            self.assertTrue(out.strip(), argv)
        self.assertEqual(self.snapshot(work), before)
        self.assertFalse(any(p.name == ".bagaev" for p in work.rglob("*")))


if __name__ == "__main__":
    unittest.main()
