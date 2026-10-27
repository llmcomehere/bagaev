"""CHANGE-1: одновременная приёмка (T10-C04), точки сбоя с kill -9, неизменность SnapshotId (T02-C04),
приёмка без исполнения (T10-C06), SourceEdit против независимого применения (T03-C04), resume в разных
процессах (T12-C04), паритет MCP и CLI (T14-C05), схема операций.
"""
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))
sys.setrecursionlimit(100000)

from bagaev_ref.change.sourceedit import EditError, apply_source_edit  # noqa: E402
from bagaev_ref.protocol.ops import PROTOCOL, Ops, init_project  # noqa: E402

APP = ROOT / "conformance" / "cases" / "accept" / "flow-01"
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "ref"))
ENV.pop("BAG_CRASH_AT", None)


def req(op, ch=None, rev=None, key=None, **args):
    r = {"protocol": PROTOCOL, "operation": op, "arguments": args}
    if ch:
        r["change_id"] = ch
    if rev is not None:
        r["expected_work_revision"] = rev
    if key:
        r["idempotency_key"] = (key + "-" + "x" * 20)[:24]
    return r


def bag(*args, env=None):
    p = subprocess.run([sys.executable, "-m", "bagaev_ref", *args, "--json"], capture_output=True, text=True,
                       env=dict(ENV, **(env or {})))
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip() else None)


class Project(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bag-change-"))
        self.root = self.tmp / "p"
        self.root.mkdir()
        shutil.copy(APP / "app.bag", self.root / "app.bag")
        init_project(self.root, "agent")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ops(self, principal="agent"):
        o = Ops(self.root, principal)
        self.addCleanup(o.close)
        return o

    def sha(self, o, ch, path="app.bag"):
        from bagaev_ref.change import workstate as W
        return hashlib.sha256(o.store.files(W.work_row(o.store, ch)["candidate"])[path]).hexdigest()

    def change(self, o, tag, old, new):
        ch = o.call(req("change_begin", key="b" + tag, intent=tag))["change_id"]
        r = o.call(req("apply", ch, 1, "a" + tag, source_edit={"files": [
            {"path": "app.bag", "base_sha256": self.sha(o, ch), "edits": [{"old_text": old, "text": new}]}]}))
        self.assertEqual(r["status"], "succeeded", r)
        return ch


class Acceptance(Project):
    def test_concurrent_accept_one_wins(self):
        o = self.ops()
        c1 = self.change(o, "1", "  n + 1\n", "  n + 2\n")
        c2 = self.change(o, "2", "  n + 1\n", "  n + 3\n")
        procs = [subprocess.Popen([sys.executable, "-m", "bagaev_ref", "op", str(self.root),
                                   json.dumps(req("accept", c, 2, "c" + c[-4:])), "--principal", "agent", "--json"],
                                  stdout=subprocess.PIPE, text=True, env=ENV) for c in (c1, c2)]
        outs = [json.loads(p.communicate(timeout=120)[0]) for p in procs]
        codes = sorted(r.get("error", {}).get("code", r["status"]) for r in outs)
        self.assertEqual(codes, ["STALE_BASE", "succeeded"])
        o2 = self.ops()
        n = o2.store.db.execute("SELECT count(*) FROM acceptance").fetchone()[0]
        self.assertEqual((n, o2.store.meta("head_revision")), (2, "2"))      # bootstrap + одна приёмка
        winner = next(r for r in outs if r["status"] == "succeeded")
        self.assertEqual(o2.store.meta("head"), winner["result"]["head"])

    def test_crash_points(self):
        o = self.ops()
        ch = self.change(o, "1", "  n + 1\n", "  n + 2\n")
        head0 = o.store.meta("head")
        o.close()
        r = req("accept", ch, 2, "c1")
        rc, _ = bag("op", str(self.root), json.dumps(r), "--principal", "agent", env={"BAG_CRASH_AT": "accept_before_commit"})
        self.assertEqual(rc, 137)
        o = self.ops()
        self.assertEqual(o.store.meta("head"), head0)                         # до фиксации ничего не видно
        o.close()
        rc, _ = bag("op", str(self.root), json.dumps(r), "--principal", "agent", env={"BAG_CRASH_AT": "accept_after_commit"})
        self.assertEqual(rc, 137)
        o = self.ops()
        self.assertNotEqual(o.store.meta("head"), head0)                      # зафиксировано, ответ потерян
        again = o.call(r)
        self.assertEqual((again["status"], again["replayed"]), ("succeeded", True))
        self.assertEqual(o.store.db.execute("SELECT count(*) FROM acceptance").fetchone()[0], 2)

    def test_snapshot_id_unchanged_by_evidence_and_acceptance(self):
        from bagaev_ref.change import workstate as W
        o = self.ops()
        ch = self.change(o, "1", '"Привет, " ++ name', '"Здравствуй, " ++ name')
        sid = W.work_row(o.store, ch)["candidate"]
        manifest = o.store.manifest(sid)
        self.assertEqual(o.call(req("verify", ch, 2, "v1"))["status"], "succeeded")
        self.assertEqual(o.call(req("accept", ch, 3, "c1"))["status"], "succeeded")
        self.assertEqual(o.store.meta("head"), sid)
        self.assertEqual(o.store.manifest(sid), manifest)
        from bagaev_ref.kernel import canonical as C
        self.assertEqual(C.digest("snapshot", "1", manifest), sid)
        self.assertEqual(o.store.snapshot(o.store.files(sid), manifest["parents"]), sid)

    def test_accept_executes_nothing(self):
        from bagaev_ref.machine import cek
        o = self.ops()
        ch = self.change(o, "1", '"Привет, " ++ name', '"Здравствуй, " ++ name')
        self.assertEqual(o.call(req("verify", ch, 2, "v1"))["status"], "succeeded")
        orig = cek.run
        cek.run = lambda *a, **k: (_ for _ in ()).throw(AssertionError("исполнение при приёмке"))
        try:
            r = o.call(req("accept", ch, 3, "c1"))
            again = o.call(req("accept", ch, 3, "c1"))
        finally:
            cek.run = orig
        self.assertEqual((r["status"], again["replayed"]), ("succeeded", True))

    def test_resume_identical_across_processes(self):
        o = self.ops()
        ch = self.change(o, "1", '"Привет, " ++ name', '"Здравствуй, " ++ name')
        o.close()
        outs = [bag("work", "resume", str(self.root), ch, "--principal", p)[1] for p in ("session_a", "session_b")]
        self.assertEqual(outs[0], outs[1])
        self.assertGreater(len([x for x in outs[0]["result"]["obligations"] if x["status"] == "open"]), 0)

    def test_corrupt_object_detected(self):
        o = self.ops()
        sid = o.store.meta("head")
        h = o.store.manifest(sid)["sources"]["app.bag"]["sha256"]
        (o.store.objects / h).write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            o.store.files(sid)


class ReviewM6(Project):
    """Регрессии ревью m6, которые корпус не выражает (registry/reviews/m6.md)."""

    def test_truncated_graph_cache_recomputed(self):
        o = self.ops()
        ch = self.change(o, "1", "  n + 1\n", "  n + 2\n")
        o.call(req("work_resume", ch))
        for f in (self.root / ".bagaev" / "graph").rglob("*.json"):
            f.write_bytes(f.read_bytes()[:10])                  # оборванная запись кэша
        r = o.call(req("work_resume", ch))
        self.assertEqual((r["status"], r["result"]["blockers"]), ("succeeded", []))
        self.assertEqual(o.call(req("accept", ch, 2, "c1"))["status"], "succeeded")

    def test_digest_escaping_no_collision(self):
        from bagaev_ref.protocol.ops import strip_numbers, unstrip
        self.assertNotEqual(strip_numbers({"x": 5}), strip_numbers({"x": {"$int": "5"}}))
        for v in ({"x": 5}, {"x": {"$int": "5"}}, {"$$y": [1, {"$int": 2}]}):
            self.assertEqual(unstrip(strip_numbers(v)), v)

    def test_internal_error_is_a_response(self):
        from bagaev_ref.change import workstate as W
        o = self.ops()
        ch = self.change(o, "1", "  n + 1\n", "  n + 2\n")
        orig = W.view
        W.view = lambda *a, **k: 1 / 0
        try:
            r = o.call(req("work_resume", ch))
        finally:
            W.view = orig
        self.assertEqual((r["status"], r["error"]["code"]), ("failed", "INTERNAL"))
        self.assertEqual(o.call(req("work_resume", ch))["status"], "succeeded")

    def test_declared_rule_deletion_discharges_obligations(self):
        o = self.ops()
        ch = o.call(req("change_begin", key="b1", intent="снять правило"))["change_id"]
        text = o.store.files(o.store.meta("head"))["app.bag"].decode()
        new = (text.replace('  @id("cq0004") rule nonempty "приветствие не пустое"\n', "")
                   .replace("pub fn greet(name: String) -> String\n  implements Polite.nonempty\n{",
                            "pub fn greet(name: String) -> String {")
                   .replace('\n@id("cq0008")\ntest greet_nonempty\n  checks Polite.nonempty\n{\n'
                            '  test.expect("не пусто", greet("x") != "")\n}\n', ""))
        r = o.call(req("apply", ch, 1, "a1", source_edit={
            "files": [{"path": "app.bag", "base_sha256": self.sha(o, ch), "whole_file": new}],
            "identity_ops": [{"op": "delete", "id": "cq0004", "reason": "правило снято"},
                             {"op": "delete", "id": "cq0008", "reason": "тест снятого правила"}]}))
        self.assertEqual(r["status"], "succeeded", r)
        v = o.call(req("work_resume", ch))["result"]
        basis = sorted({x["basis"] for x in v["obligations"] if x["obligation"][1] == "cq0004"})
        self.assertEqual(basis, ["declared-delete"])
        self.assertEqual([b["kind"] for b in v["blockers"]], ["OBLIGATION_OPEN"])     # about: контракт Polite изменён
        o.call(req("contract_update", ch, 2, "k1", ops=[{"op": "assume", "obligation": ["about", "cq0002", "cq0003"],
                                                         "reason": "контракт сужен осознанно"}]))
        self.assertEqual(o.call(req("accept", ch, 3, "c1"))["status"], "succeeded")

    def test_tampered_evidence_is_invalid(self):
        """Свидетельство неизменно: запись, не совпадающая со своим ID, — integrity invalid и не закрывает (T08-C04)."""
        from bagaev_ref.kernel import canonical as C
        o = self.ops()
        ch = self.change(o, "1", '"Привет, " ++ name', '"Здравствуй, " ++ name')
        o.call(req("verify", ch, 2, "v1"))
        self.assertEqual(o.call(req("work_resume", ch))["result"]["blockers"], [])
        eid, rec = o.store.db.execute("SELECT id, record FROM evidence").fetchone()
        forged = dict(C.decode(bytes(rec)), verdict="PASS", test_rev="0" * 64)
        o.store.db.execute("UPDATE evidence SET record = ? WHERE id = ?", (C.encode(forged), eid))
        v = o.call(req("work_resume", ch))["result"]
        self.assertEqual({a["integrity"] for a in v["assessments"]}, {"invalid"})
        self.assertIn("OBLIGATION_OPEN", [b["kind"] for b in v["blockers"]])

    def test_init_skips_hidden_dirs_and_refuses_twice(self):
        root = self.tmp / "q"
        (root / ".git").mkdir(parents=True)
        (root / ".git" / "x.bag").write_text("garbage")
        shutil.copy(APP / "app.bag", root / "app.bag")
        self.assertEqual(init_project(root, "agent")["files"], 1)
        self.assertEqual(init_project(root, "agent")["code"], "PROJECT_EXISTS")


class Mcp(unittest.TestCase):
    """JSON-RPC 2.0: пакет, уведомление без ответа, неверные params и исключения не роняют сервер (ревью m6 M4)."""

    def test_jsonrpc_shapes(self):
        from bagaev_ref.protocol.mcp_server import handle_line
        tmp = Path(tempfile.mkdtemp(prefix="bag-mcp-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copy(APP / "app.bag", tmp / "app.bag")
        init_project(tmp, "agent")
        o = Ops(tmp, "agent")
        self.addCleanup(o.close)
        batch = handle_line(o, json.dumps([{"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                                           {"jsonrpc": "2.0", "method": "tools/call",
                                            "params": {"name": "bag_search", "arguments": {"query": "x"}}}]))
        self.assertEqual([r["id"] for r in batch], [2])                 # уведомление ответа не получает
        self.assertEqual(handle_line(o, "[]")["error"]["code"], -32600)
        self.assertEqual(handle_line(o, '"x"')["error"]["code"], -32600)
        self.assertEqual(handle_line(o, '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":[1]}')["error"]["code"],
                         -32602)
        self.assertEqual(handle_line(o, "{")["error"]["code"], -32700)
        r = handle_line(o, json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                       "params": {"name": "bag_work_resume", "arguments": {"change_id": "ch-x",
                                                                                           "arguments": {"budget": "x"}}}}))
        self.assertEqual(r["result"]["structuredContent"]["error"]["code"], "REQUEST_INVALID")


TS_APP = ROOT / "pilot" / "authorship" / "app-ts"
HAVE_NODE = shutil.which("node") is not None and (ROOT / "pilot/writability/node_modules/typescript/bin/tsc").is_file()


@unittest.skipUnless(HAVE_NODE, "нет node или компилятора TypeScript")
class TypeScriptArm(unittest.TestCase):
    """Вариант B пилота: язык typescript того же протокола (lang.py) и извлекатель links-ts."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bag-ts-"))
        self.root = self.tmp / "p"
        shutil.copytree(TS_APP, self.root)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def graph(self, root=None):
        p = subprocess.run(["node", "--no-warnings", str(ROOT / "pilot/authorship/links-ts/extract.ts"), str(root or self.root)],
                           capture_output=True, text=True, check=True)
        return json.loads(p.stdout)

    def test_extractor_edges(self):
        g = self.graph()
        e = {(x["kind"], x["src"], x["dst"]) for x in g["edges"]}
        for want in [("reads", "rss.feed", "db.articles"), ("consumes", "notify.notifyEdit", "events.AuthorshipChanged"),
                     ("consumes", "indexer.indexAuthorship", "events.AuthorshipChanged"),
                     ("emits", "editor.apply", "events.AuthorshipChanged"), ("writes", "editor.apply", "db.articles"),
                     ("derived_from", "db.authorIndex", "authorship.Authorship"),
                     ("implements", "authorship.checkAuthor", "authorship.AuthorshipShape.single"),
                     ("checks", "test.app.export_keeps_author", "authorship.AttributionComplete.complete"),
                     ("uses_type", "rss.feed", "articles.Article"), ("calls", "editor.apply", "authorship.checkAuthor")]:
            self.assertIn(want, e)
        self.assertTrue(all(v["status"] == "COMPLETE" for v in g["coverage"]["kinds"].values()))

    def test_raw_sql_is_partial(self):
        f = self.root / "src" / "rss.ts"
        f.write_text(f.read_text(encoding="utf-8").replace("const all = people.all(db);",
                     "const all = people.all(db);\n  db.prepare(\"SELECT * FROM articles\").all();"), encoding="utf-8")
        cov = self.graph()["coverage"]["kinds"]
        self.assertEqual((cov["reads"]["status"], cov["reads"]["basis"]), ("PARTIAL", "сырой SQL в rss.feed"))

    def test_protocol_cycle(self):
        self.assertEqual(init_project(self.root, "agent")["language"], "typescript")
        o = Ops(self.root, "agent")
        self.addCleanup(o.close)
        ch = o.call(req("change_begin", key="b1", intent="подпись"))["change_id"]
        from bagaev_ref.change import workstate as W
        f = o.store.files(W.work_row(o.store, ch)["candidate"])["src/byline.ts"]
        r = o.call(req("apply", ch, 1, "a1", source_edit={"files": [{"path": "src/byline.ts",
            "base_sha256": hashlib.sha256(f).hexdigest(),
            "edits": [{"old_text": "return displayName(all, a.author);", "text": "return displayName(all, a.author) + \"\";"}]}]}))
        self.assertEqual((r["status"], r["result"]["diagnostics"]), ("succeeded", []))
        v = o.call(req("work_resume", ch))["result"]
        self.assertEqual(sorted({b["kind"] for b in v["blockers"]}), ["OBLIGATION_OPEN", "TESTS_NOT_RUN"])
        self.assertEqual(o.call(req("accept", ch, 2, "c0"))["error"]["code"], "OPEN_OBLIGATIONS")
        self.assertEqual(o.call(req("verify", ch, 2, "v1"))["status"], "succeeded")
        self.assertEqual(o.call(req("work_resume", ch))["result"]["blockers"], [])
        self.assertEqual(o.call(req("accept", ch, 3, "c1"))["status"], "succeeded")

    def test_type_error_is_draft(self):
        init_project(self.root, "agent")
        o = Ops(self.root, "agent")
        self.addCleanup(o.close)
        ch = o.call(req("change_begin", key="b1", intent="ошибка типов"))["change_id"]
        from bagaev_ref.change import workstate as W
        f = o.store.files(W.work_row(o.store, ch)["candidate"])["src/byline.ts"]
        r = o.call(req("apply", ch, 1, "a1", source_edit={"files": [{"path": "src/byline.ts",
            "base_sha256": hashlib.sha256(f).hexdigest(), "edits": [{"old_text": "a.author", "text": "a.authors"}]}]}))
        self.assertTrue(r["result"]["draft"])
        self.assertEqual({d["code"] for d in r["result"]["diagnostics"]}, {"TS2551"})
        self.assertEqual([b["kind"] for b in o.call(req("work_resume", ch))["result"]["blockers"]], ["CANDIDATE_INVALID"])


class SourceEditProperty(unittest.TestCase):
    """Случайные правки против наивного применения слева направо со сдвигом (T03-C04)."""

    def test_random_edits(self):
        rng = random.Random(7)
        alphabet = "abc ёж\n{}"
        for _ in range(400):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
            data = text.encode("utf-8")
            cuts = sorted({rng.randint(0, len(text)) for _ in range(rng.randint(0, 6))})
            spans, i = [], 0
            while i + 1 < len(cuts):
                if rng.random() < 0.6:
                    spans.append((cuts[i], cuts[i + 1]))
                i += 2
            edits, expected, prev = [], "", 0
            for s, t in spans:                           # символьные позиции → байтовые
                rep = "".join(rng.choice("XYZ") for _ in range(rng.randint(0, 3)))
                bs, bt = len(text[:s].encode()), len(text[:t].encode())
                edits.append({"start": bs, "end": bt, "text": rep})
                expected += text[prev:s] + rep
                prev = t
            expected += text[prev:]
            if not edits:
                continue
            f = {"path": "a.bag", "base_sha256": hashlib.sha256(data).hexdigest(), "edits": list(reversed(edits))}
            try:
                new, touched = apply_source_edit({"a.bag": data}, {"files": [f]})
            except EditError as e:
                self.assertEqual(e.code, "OVERLAPPING_EDITS")   # смежные пустые правки — неоднозначный порядок
                continue
            self.assertEqual(new["a.bag"].decode("utf-8"), expected)


class Transports(unittest.TestCase):
    def test_mcp_cli_parity(self):
        rc, out = bag("mcp", str(APP), "--selftest")
        self.assertEqual((rc, out["outcome"]), (0, "PARITY"), out)
        self.assertEqual(out["tools"], 16)

    def test_operations_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema нет: схему проверяет tools/check.py --exec")
        schema = json.loads((ROOT / "spec/protocol/operations.schema.json").read_text(encoding="utf-8"))
        v = jsonschema.Draft202012Validator(schema)
        from bagaev_ref.protocol.ops import READ, WRITE
        ops = set(schema["$defs"]["read_op"]["enum"]) | set(schema["$defs"]["write_op"]["enum"])
        self.assertEqual(ops, READ | WRITE)
        self.assertEqual(list(v.iter_errors(req("accept", "ch-x", 2, "c1"))), [])
        self.assertTrue(list(v.iter_errors({"protocol": PROTOCOL, "operation": "accept", "arguments": {}})))


if __name__ == "__main__":
    unittest.main()
