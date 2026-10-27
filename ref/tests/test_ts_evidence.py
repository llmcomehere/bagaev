"""Регрессии Ф7: CHG-11/12 — callable-зависимости и только исполненный PASS как основание.

Ожидания заданы до прогона: изменение value 1→2 затрагивает проверяющий output тест;
SKIP/TODO не исполняют требуемую проверку; ненулевой exit runner запрещает приёмку.
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ref"))

from bagaev_ref.change import verify as V, workstate as W
from bagaev_ref.change.lang import TypeScript
from bagaev_ref.links import certs
from bagaev_ref.links.graph import Graph
from bagaev_ref.links.impact import impact
from bagaev_ref.protocol.ops import PROTOCOL, Ops, init_project

HAVE_NODE = shutil.which("node") is not None and TypeScript.TSC.is_file()
TEST_NAME = "test.value.value_is_one"


def request(op, ch=None, rev=None, key=None, **args):
    out = {"protocol": PROTOCOL, "operation": op, "arguments": args}
    if ch is not None:
        out["change_id"] = ch
    if rev is not None:
        out["expected_work_revision"] = rev
    if key is not None:
        out["idempotency_key"] = (key + "-" + "x" * 20)[:24]
    return out


def files(source="export const value = () => 1;\n", test=None):
    app = ROOT / "pilot/authorship/app-ts"
    out = {name: (app / name).read_bytes() for name in ("package.json", "tsconfig.json", "node-env.d.ts")}
    out["node-env.d.ts"] += (
        b'\ndeclare module "node:test" { export function test(name: string, '
        b'options: {skip?: boolean; todo?: boolean}, fn: () => void): void; }\n')
    out["src/value.ts"] = (source + "export function output(): number { return value(); }\n").encode()
    out["test/value.test.ts"] = (test if test is not None else
        'import { test } from "node:test";\n'
        'import { equal } from "node:assert/strict";\n'
        'import { output } from "../src/value.ts";\n'
        'test("value_is_one", () => { equal(output(), 1); });\n').encode()
    return out


class TapResults(unittest.TestCase):
    """Парсер TAP не смешивает имя, директиву и успешность всего процесса."""

    def test_directives_and_runner_exit_are_preserved(self):
        tap = ("TAP version 13\nok 1 - skipped # SKIP reason\nnot ok 2 - pending # TODO reason\n"
               "ok 3 - future # TODO\nok 4 - passed\nnot ok 5 - failed\n1..5\n")
        with patch("bagaev_ref.change.lang.subprocess.run", return_value=subprocess.CompletedProcess([], 7, tap, "")):
            result = TypeScript().run_tests({"test/value.test.ts": b""})
        self.assertEqual(result["tests"], [
            {"test": "test.value.skipped", "status": "SKIP"},
            {"test": "test.value.pending", "status": "TODO"},
            {"test": "test.value.future", "status": "TODO"},
            {"test": "test.value.passed", "status": "PASS"},
            {"test": "test.value.failed", "status": "FAIL"}])
        self.assertEqual(result["outcome"], "ERROR")
        self.assertEqual(result["runners"], [{"file": "test/value.test.ts", "status": "ERROR",
                                              "reason": "runner-exit", "returncode": "7"}])

    def test_legacy_runner_failure_needs_a_valid_complete_retry(self):
        def sealed(body):
            return dict(body, id=V.C.digest("evidence", "1", body))

        lang, before = TypeScript(), {"test/value.test.ts": b"failed runner"}
        failure = sealed({"kind": "test-runner", "test": "runner:test/value.test.ts", "verdict": "ERROR"})
        success = sealed({"kind": "test-suite", "test": lang.runner_suite, "verdict": "PASS", "inventory": {},
                          "subject": "empty"})
        self.assertEqual(V.pending_runner_verification(before, {}, [failure], lang, "empty"), lang.runner_suite)
        self.assertIsNone(V.pending_runner_verification(before, {}, [failure, success], lang, "empty"))
        self.assertEqual(V.pending_runner_verification(before, before, [failure, success], lang, "restored"), lang.runner_suite)
        corrupted = dict(success, inventory={"forged": "0" * 64})
        self.assertEqual(V.pending_runner_verification(before, {}, [failure, corrupted], lang, "empty"), lang.runner_suite)

    def test_incomplete_runner_observation_cannot_be_a_successful_suite(self):
        fs = {"test/a.test.ts": b"", "test/b.test.ts": b""}
        observation = {"phase": "test", "outcome": "TESTED", "tests": [],
                       "runners": [{"file": "test/a.test.ts", "status": "PASS"}]}
        with patch.object(TypeScript, "run_tests", return_value=observation):
            ev = V.run_evidence(fs, SimpleNamespace(nodes={}), "candidate", TypeScript())
        self.assertEqual([(e["kind"], e["verdict"]) for e in ev], [("test-suite", "ERROR")])
        self.assertEqual(set(ev[0]["inventory"]), set(fs))


@unittest.skipUnless(HAVE_NODE, "нет node или уже установленного TypeScript")
class TypeScriptEvidence(unittest.TestCase):
    def setUp(self):
        self.lang = TypeScript()

    def graph(self, fs, side="candidate"):
        return Graph(self.lang.extract(fs, None), side)

    def project(self, fs):
        root = Path(tempfile.mkdtemp(prefix="bag-ts-evidence-"))
        self.addCleanup(shutil.rmtree, root, True)
        for rel, data in fs.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
        self.assertEqual(init_project(root, "agent")["language"], "typescript")
        o = Ops(root, "agent")
        self.addCleanup(o.close)
        ch = o.call(request("change_begin", key="begin", intent="evidence regression"))["change_id"]
        return o, ch

    def clause(self, o, ch):
        r = o.call(request("contract_update", ch, 1, "clause", ops=[{
            "op": "add_clause", "id": "must-run", "claim": "output equals one", "method": {"test": TEST_NAME}}]))
        self.assertEqual(r["status"], "succeeded", r)

    def edit_files(self, o, ch, revision, changes):
        current = o.store.files(W.work_row(o.store, ch)["candidate"])
        edits = []
        for rel, text in changes.items():
            if rel in current:
                edits.append({"path": rel, "base_sha256": hashlib.sha256(current[rel]).hexdigest(),
                              **({"delete": True} if text is None else {"whole_file": text})})
            else:
                edits.append({"path": rel, "create": text})
        result = o.call(request("apply", ch, revision, "edit-files-" + str(revision), source_edit={"files": edits}))
        self.assertEqual(result["status"], "succeeded", result)

    def assert_runner_pending(self, o, ch, revision):
        view = o.call(request("work_resume", ch))["result"]
        self.assertFalse(view["ready_for_acceptance"])
        self.assertIn("runner:typescript", view["impact"]["tests_to_run"])
        self.assertIn({"kind": "TESTS_NOT_RUN", "tests": ["runner:typescript"]}, view["blockers"])
        self.assertEqual(o.call(request("accept", ch, revision, "pending-" + str(revision)))["error"]["code"],
                         "OPEN_OBLIGATIONS")

    def test_callable_declarations_and_aliases_invalidate_the_closure(self):
        cases = [
            ("arrow", "export const value = () => 1;\n", "() => 1", "() => 2", "value.value"),
            ("function-expression", "export const value = function named(): number { return 1; };\n",
             "return 1", "return 2", "value.value"),
            ("alias", "const original = () => 1;\nexport const value = original;\n", "() => 1", "() => 2", "value.original"),
            ("bound-alias", "const original = () => 1;\nexport const value = original.bind(null);\n",
             "() => 1", "() => 2", "value.original"),
            ("same-statement", "export const original = () => 1, value = () => original();\n",
             "() => 1", "() => 2", "value.original"),
        ]
        for label, source, old, new, target in cases:
            with self.subTest(label=label):
                base_files = files(source)
                cand_files = dict(base_files, **{"src/value.ts": base_files["src/value.ts"].replace(old.encode(), new.encode())})
                base, cand = self.graph(base_files, "base"), self.graph(cand_files)
                self.assertEqual(base.nodes["value.value"]["kind"], "fn")
                self.assertIn(("calls", "value.output", "value.value"),
                              {(e["kind"], e["src"], e["dst"]) for e in base.data["edges"]})
                self.assertIn(target, certs.closure(base, TEST_NAME))
                ev = next(e for e in V.run_evidence(base_files, base, "before", self.lang) if e["test"] == TEST_NAME)
                self.assertEqual(ev["verdict"], "PASS")
                self.assertEqual(V.assess(ev, cand, "after")["applicability"], "stale")
                self.assertIn(TEST_NAME, impact(base, cand)["tests_to_run"])
                self.assertEqual(next(t["status"] for t in self.lang.run_tests(cand_files)["tests"] if t["test"] == TEST_NAME), "FAIL")

    def test_imported_callable_alias_has_call_edge(self):
        fs = files('import { original as imported } from "./original.ts";\nexport const value = imported;\n')
        fs["src/original.ts"] = b"export const original = function () { return 1; };\n"
        g = self.graph(fs)
        self.assertIn("original.original", certs.closure(g, TEST_NAME))
        fs["src/original.ts"] = fs["src/original.ts"].replace(b"return 1", b"return 2")
        changed = self.graph(fs)
        self.assertNotEqual(certs.closure_premises(g, TEST_NAME)["closure"],
                            certs.closure_premises(changed, TEST_NAME)["closure"])

    def test_arrow_change_cannot_accept_old_pass(self):
        o, ch = self.project(files())
        self.assertEqual(o.call(request("verify", ch, 1, "verify"))["status"], "succeeded")
        data = o.store.files(W.work_row(o.store, ch)["candidate"])["src/value.ts"]
        applied = o.call(request("apply", ch, 2, "apply", source_edit={"files": [{"path": "src/value.ts",
            "base_sha256": hashlib.sha256(data).hexdigest(), "edits": [{"old_text": "() => 1", "text": "() => 2"}]}]}))
        self.assertEqual(applied["status"], "succeeded", applied)
        view = o.call(request("work_resume", ch))["result"]
        self.assertFalse(view["ready_for_acceptance"])
        self.assertIn("TESTS_NOT_RUN", {b["kind"] for b in view["blockers"]})
        self.assertEqual(o.call(request("accept", ch, 3, "accept"))["error"]["code"], "OPEN_OBLIGATIONS")

    def test_real_skip_and_todo_do_not_support_a_clause(self):
        for directive in ("skip", "todo"):
            with self.subTest(directive=directive):
                fs = files(test='import { test } from "node:test";\n'
                    f'test("value_is_one", {{{directive}: true}}, () => {{ throw new Error("must fail"); }});\n')
                o, ch = self.project(fs)
                self.clause(o, ch)
                self.assertEqual(o.call(request("verify", ch, 2, "verify"))["status"], "succeeded")
                view = o.call(request("work_resume", ch))["result"]
                self.assertEqual(view["clauses"][0]["status"], "open")
                self.assertEqual(view["clauses"][0]["basis"], "test-not-run")
                self.assertFalse(view["ready_for_acceptance"])
                self.assertEqual(next(a["verdict"] for a in view["assessments"] if a["test"] == TEST_NAME), directive.upper())
                self.assertNotIn("EVIDENCE_CONTRADICTED", {b["kind"] for b in view["blockers"]})
                self.assertEqual(o.call(request("accept", ch, 3, "accept"))["error"]["code"], "OPEN_OBLIGATIONS")

    def test_new_nonexecution_replaces_pass_on_the_same_snapshot(self):
        o, ch = self.project(files())
        self.clause(o, ch)
        self.assertEqual(o.call(request("verify", ch, 2, "pass"))["status"], "succeeded")
        self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])
        for rev, status in enumerate(("SKIP", "TODO", "NOT_RUN"), start=3):
            result = {"phase": "test", "outcome": "TESTED", "tests": [] if status == "NOT_RUN" else [
                {"test": TEST_NAME, "status": status}], "runners": [{"file": "test/value.test.ts", "status": "PASS"}]}
            with patch.object(TypeScript, "run_tests", return_value=result):
                self.assertEqual(o.call(request("verify", ch, rev, status))["status"], "succeeded")
            view = o.call(request("work_resume", ch))["result"]
            self.assertEqual(view["clauses"][0]["status"], "open")
            self.assertEqual(next(a["verdict"] for a in view["assessments"] if a["test"] == TEST_NAME), status)
            self.assertEqual(o.call(request("accept", ch, rev + 1, "accept-" + status))["error"]["code"], "OPEN_OBLIGATIONS")
        self.assertEqual(o.call(request("verify", ch, 6, "pass-again"))["status"], "succeeded")
        self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])

    def test_nonzero_runner_blocks_even_when_named_test_passed(self):
        fs = files("export const value = () => 1;\nexport const unrelated = 1;\n")
        fs["test/value.test.ts"] += b"declare const process: { exitCode: number };\nprocess.exitCode = 1;\n"
        o, ch = self.project(fs)
        self.clause(o, ch)
        self.assertEqual(o.call(request("verify", ch, 2, "verify"))["status"], "succeeded")
        view = o.call(request("work_resume", ch))["result"]
        self.assertEqual(view["clauses"][0]["status"], "supported")
        self.assertFalse(view["ready_for_acceptance"])
        self.assertIn({"kind": "EVIDENCE_CONTRADICTED", "test": "runner:test/value.test.ts", "verdict": "ERROR"}, view["blockers"])
        self.assertEqual(o.call(request("accept", ch, 3, "accept"))["error"]["code"], "OPEN_OBLIGATIONS")
        # Ни чужая константа, ни комментарий в тестовом файле не заменяют успешный retry runner.
        for rev, rel, old, new in ((3, "src/value.ts", "unrelated = 1", "unrelated = 2"),
                                  (4, "test/value.test.ts", "process.exitCode = 1;", "process.exitCode = 1; // changed")):
            data = o.store.files(W.work_row(o.store, ch)["candidate"])[rel]
            edited = o.call(request("apply", ch, rev, "edit-" + str(rev), source_edit={"files": [{
                "path": rel, "base_sha256": hashlib.sha256(data).hexdigest(), "edits": [{"old_text": old, "text": new}]}]}))
            self.assertEqual(edited["status"], "succeeded", edited)
            view = o.call(request("work_resume", ch))["result"]
            self.assertFalse(view["ready_for_acceptance"])
            self.assertIn({"kind": "EVIDENCE_CONTRADICTED", "test": "runner:typescript", "verdict": "ERROR"}, view["blockers"])
            self.assertEqual(o.call(request("accept", ch, rev + 1, "accept-" + str(rev)))["error"]["code"], "OPEN_OBLIGATIONS")
        # Повторный успешный runner вытесняет прежнюю ошибку того же снимка.
        result = {"phase": "test", "outcome": "TESTED", "tests": [{"test": TEST_NAME, "status": "PASS"}],
                  "runners": [{"file": "test/value.test.ts", "status": "PASS"}]}
        with patch.object(TypeScript, "run_tests", return_value=result):
            self.assertEqual(o.call(request("verify", ch, 5, "retry"))["status"], "succeeded")
        self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])

    def test_raw_sql_partial_prevents_acceptance_despite_fresh_pass(self):
        fs = files()
        fs["src/db.ts"] = (b'export type Db = { prepare(sql: string): { all(): unknown[] } };\n'
                            b'export const articles = { all(db: Db) { return db.prepare("SELECT 1").all(); } };\n')
        fs["src/reader.ts"] = (b'import type { Db } from "./db.ts";\n'
                                b'export function raw(db: Db): unknown[] { return db.prepare("SELECT * FROM articles").all(); }\n')
        o, ch = self.project(fs)
        self.assertEqual(o.call(request("verify", ch, 1, "verify"))["status"], "succeeded")
        view = o.call(request("work_resume", ch))["result"]
        self.assertFalse(view["ready_for_acceptance"])
        self.assertEqual(view["impact"]["status"], "INCOMPLETE")
        self.assertIn("reader.raw", {u["id"] for u in view["impact"]["unknown"]})
        self.assertEqual(next(a["verdict"] for a in view["assessments"] if a["test"] == TEST_NAME), "PASS")
        self.assertEqual(o.call(request("accept", ch, 2, "accept"))["error"]["code"], "OPEN_OBLIGATIONS")

    def test_runner_failure_without_a_named_test_still_blocks(self):
        fs = files(test="declare const process: { exitCode: number };\nprocess.exitCode = 1;\n")
        o, ch = self.project(fs)
        self.assertEqual(o.call(request("verify", ch, 1, "verify"))["status"], "succeeded")
        view = o.call(request("work_resume", ch))["result"]
        self.assertEqual(view["clauses"], [])
        self.assertFalse(view["ready_for_acceptance"])
        self.assertIn({"kind": "EVIDENCE_CONTRADICTED", "test": "runner:test/value.test.ts", "verdict": "ERROR"}, view["blockers"])
        self.assertEqual(o.call(request("accept", ch, 2, "accept"))["error"]["code"], "OPEN_OBLIGATIONS")

    def test_runner_rename_keeps_error_until_a_real_successful_retry(self):
        failure = "declare const process: { exitCode: number };\nprocess.exitCode = 1;\n"
        o, ch = self.project(files(test=failure))
        self.assertEqual(o.call(request("verify", ch, 1, "first-error"))["status"], "succeeded")
        self.edit_files(o, ch, 2, {"test/value.test.ts": None, "test/renamed.test.ts": failure})
        self.assert_runner_pending(o, ch, 3)
        self.assertEqual(o.call(request("run_tests", ch))["result"]["outcome"], "ERROR")
        self.assertEqual(o.call(request("verify", ch, 3, "renamed-error"))["status"], "succeeded")
        self.assert_runner_pending(o, ch, 4)
        self.edit_files(o, ch, 4, {"test/renamed.test.ts": failure.replace("= 1", "= 0")})
        self.assert_runner_pending(o, ch, 5)
        self.assertEqual(o.call(request("verify", ch, 5, "fixed"))["status"], "succeeded")
        self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])
        self.assertEqual(o.call(request("accept", ch, 6, "accept-fixed"))["status"], "succeeded")

    def test_deleted_runner_can_clear_but_restoring_it_requires_a_new_run(self):
        failure = "declare const process: { exitCode: number };\nprocess.exitCode = 1;\n"
        o, ch = self.project(files(test=failure))
        self.assertEqual(o.call(request("verify", ch, 1, "first-error"))["status"], "succeeded")
        self.edit_files(o, ch, 2, {"test/value.test.ts": None})
        self.assert_runner_pending(o, ch, 3)
        self.assertEqual(o.call(request("verify", ch, 3, "empty"))["status"], "succeeded")
        self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])
        self.edit_files(o, ch, 4, {"test/value.test.ts": failure})
        self.assert_runner_pending(o, ch, 5)
        self.assertEqual(o.call(request("verify", ch, 5, "restored-error"))["status"], "succeeded")
        # Удаление из runner-набора без исчезновения module ID: value.test.ts → value.ts.
        self.edit_files(o, ch, 6, {"test/value.test.ts": None, "test/value.ts": failure})
        self.assert_runner_pending(o, ch, 7)
        self.assertEqual(o.call(request("verify", ch, 7, "empty-again"))["status"], "succeeded")
        self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])
        self.assertEqual(o.call(request("accept", ch, 8, "accept-removed"))["status"], "succeeded")

    def test_new_renamed_or_changed_successful_runner_requires_verification(self):
        for changes in ({"test/new.test.ts": ""},
                        {"test/value.test.ts": None, "test/renamed.test.ts": ""},
                        {"test/value.test.ts": "// changed runner\n"}):
            with self.subTest(paths=list(changes)):
                o, ch = self.project(files(test=""))
                self.assertEqual(o.call(request("verify", ch, 1, "baseline"))["status"], "succeeded")
                self.edit_files(o, ch, 2, changes)
                self.assert_runner_pending(o, ch, 3)
                self.assertEqual(o.call(request("verify", ch, 3, "fresh"))["status"], "succeeded")
                self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])
                self.assertEqual(o.call(request("accept", ch, 4, "accept-fresh"))["status"], "succeeded")

    def test_runner_success_does_not_transfer_across_imported_source_change(self):
        fs = files(test='import { output } from "../src/value.ts";\n'
                        'if (output() !== 1) throw new Error("top-level runner failed");\n')
        o, ch = self.project(fs)
        self.assertEqual(o.call(request("verify", ch, 1, "baseline"))["status"], "succeeded")
        source = fs["src/value.ts"].decode()
        self.edit_files(o, ch, 2, {"src/value.ts": source.replace("() => 1", "() => 2")})
        self.assert_runner_pending(o, ch, 3)
        self.assertEqual(o.call(request("run_tests", ch))["result"]["outcome"], "ERROR")
        self.edit_files(o, ch, 3, {"src/value.ts": source})
        self.assertEqual(o.call(request("verify", ch, 4, "restored"))["status"], "succeeded")
        self.assertTrue(o.call(request("work_resume", ch))["result"]["ready_for_acceptance"])
        self.assertEqual(o.call(request("accept", ch, 5, "accept-restored"))["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
