"""Границы харнесса; никакого провайдера LLM и никаких сетевых вызовов."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot.authorship.oracle.run import decode_cli_response
from pilot.harness.closed import materialize, reveal, validate
from pilot.harness.commit_reveal import commitment
from pilot.harness.common import Journal, encoded, load, save, sha
from pilot.harness.judge import classify, posthoc
from pilot.harness.mediator import AccessDenied, Session, live_provider
from pilot.harness.run import dry_run, head_hook, provider_call, resume_hook, schedule, unavailable_hook
from pilot.harness.sandbox import Sandbox

ROOT = Path(__file__).resolve().parents[3]
SANDBOX = Path("/usr/bin/bwrap").is_file()
TSC = (ROOT / "pilot/writability/node_modules/typescript/bin/tsc").is_file()


class Formats(unittest.TestCase):
    def test_balanced_reproducible_schedule(self):
        first = schedule()
        self.assertEqual(first, schedule())
        self.assertEqual(len(first["rows"]), 120)
        for case in first["cases"]:
            for arm in "ABC":
                self.assertEqual(sum(r["case"] == case and r["arm"] == arm for r in first["rows"]), 5)
        self.assertNotEqual(first["rows"], schedule(seed=1)["rows"])
        with self.assertRaises(ValueError):
            schedule(repetitions=2)

    def test_commitment_exact_bytes_nonce_and_domain(self):
        payload = 'кириллица\n'.encode()
        nonce = bytes(range(32))
        self.assertEqual(commitment(payload, nonce), commitment(payload, nonce))
        self.assertNotEqual(commitment(payload, nonce), commitment(payload + b"\n", nonce))
        self.assertNotEqual(commitment(payload, nonce), commitment(payload, nonce[::-1]))
        with self.assertRaises(ValueError):
            commitment(payload, b"short")
        # Независимая формула привязывает framing, порядок и domain; хеш публичного теста, не closed payload.
        import hashlib
        self.assertEqual(commitment(payload, nonce), hashlib.sha256(
            b"bagaev-pilot-hidden-task/1\0" + (32).to_bytes(8, "big") + nonce
            + len(payload).to_bytes(8, "big") + payload).hexdigest())

    def test_live_never_spawns(self):
        with patch("subprocess.Popen", side_effect=AssertionError("must not spawn")):
            with self.assertRaisesRegex(RuntimeError, "LIVE_DISABLED"):
                live_provider(model="anything", budget=1)

    def test_cli_observation_failure_is_not_infrastructure_failure(self):
        for output in ("not JSON", '"not an object"', '{"status":"error","value":42}',
                       '{"value":42}', '{\n"status":"ok"\n}'):
            result, infrastructure = classify({"started": True, "returncode": 0, "stdout": output}, decode_cli_response)
            self.assertEqual(result["code"], "CLI_RESPONSE")
            self.assertFalse(infrastructure)
        result, infrastructure = classify({"started": True, "returncode": 0, "stdout": '{"status":"rejected"}'}, decode_cli_response)
        self.assertFalse(infrastructure)
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(classify({"started": False}, decode_cli_response)[1])

    def test_journal_truncation_and_edit_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.jsonl"
            log = Journal(path)
            log.append("one", value=1)
            log.append("two", value=2)
            self.assertEqual(len(Journal.verify(path)), 2)
            raw = path.read_bytes().replace(b'"value":1', b'"value":9')
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "JOURNAL_INTEGRITY"):
                Journal.verify(path)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def make(self, arm="C", **kwargs):
        path = self.directory / str(len(list(self.directory.iterdir())))
        return Session(ROOT, path, arm, **kwargs)

    def test_paths_cannot_leave_workspace_or_access_control(self):
        s = self.make()
        for path in ("../control/checkpoint.json", str(ROOT / "pilot/authorship/reference"),
                     ".bagaev/project.db", "blog/../../oracle/run.py", "blog//export.bag", "./guide-llm.md"):
            self.assertEqual(s.call("read", {"path": path})["status"], "DENIED")
        (s.app / "escape.bag").symlink_to(ROOT / "spec/language/guide-llm.md")
        with self.assertRaisesRegex(AccessDenied, "SYMLINK_DENIED"):
            s.path("escape.bag")

    def test_a_has_no_graph_tool(self):
        s = self.make("A")
        self.assertEqual(s.call("bag", {"operation": "search"})["code"], "TOOL_NOT_ALLOWED")
        self.assertFalse((s.app / ".bagaev").exists())
        self.assertFalse((s.app / "guide-llm.md").exists())

    def test_write_compare_and_swap_and_guide_read_only(self):
        s = self.make("A")
        path = "src/byline.ts"
        original = (s.app / path).read_bytes()
        denied = s.call("write", {"path": path, "expected_sha256": "wrong", "text": "bad"})
        self.assertEqual(denied["code"], "STALE_SOURCE")
        self.assertEqual((s.app / path).read_bytes(), original)
        okay = s.call("write", {"path": path, "expected_sha256": sha(original), "text": original.decode() + "\n"})
        self.assertEqual(okay["status"], "WRITTEN")
        c = self.make("C")
        self.assertEqual(c.call("write", {"path": "guide-llm.md", "text": "changed"})["code"], "WRITE_DENIED")

    def test_turn_context_total_and_time_budgets_stop_before_write(self):
        for limits, code in (({"turns": 0}, "TURN_LIMIT"), ({"context_token_upper_bound": 1}, "CONTEXT_LIMIT"),
                             ({"total_token_upper_bound": 1}, "TOTAL_TOKEN_UPPER_BOUND"),
                             ({"wall_seconds": 0}, "WALL_TIME_LIMIT")):
            s = self.make("A", limits=limits)
            original = (s.app / "src/byline.ts").read_bytes()
            response = s.call("write", {"path": "src/byline.ts", "text": "wrong", "expected_sha256": sha(original)})
            self.assertEqual((response["status"], response["code"]), ("BUDGET_STOP", code))
            self.assertEqual((s.app / "src/byline.ts").read_bytes(), original)
            restored = Session(ROOT, s.directory, resume=True)
            self.assertEqual(restored.call("list")["status"], "BUDGET_STOP")

    def test_each_context_saved_and_metrics_null(self):
        s = self.make()
        s.call("list")
        s.call("read", {"path": "guide-llm.md"})
        for row in Journal.verify(s.journal.path):
            if row["kind"] == "tool":
                context = load(s.control / row["context_file"])
                self.assertEqual(sha(encoded(context)), row["context_sha256"])
        self.assertGreater(s.data["context_bytes_total"], len((s.app / "guide-llm.md").read_bytes()) * 2)
        self.assertTrue(all(x is None for x in s.data["llm_measurements"].values()))

    def test_context_limit_precedes_provider_request(self):
        s = self.make(limits={"context_token_upper_bound": 1})
        class ForbiddenProvider:
            def action(self, *args):
                raise AssertionError("Контекст сверх лимита передан провайдеру")
        self.assertEqual(provider_call(ForbiddenProvider(), s, "list")["code"], "CONTEXT_LIMIT")

    def test_accepted_sources_cannot_be_changed_by_agent(self):
        s = self.make("A")
        s.initialize()
        response = s.call("accept")
        self.assertEqual(response["status"], "accepted")
        before = (s.app / "src/byline.ts").read_bytes()
        response = s.call("write", {"path": "src/byline.ts", "text": "bad", "expected_sha256": sha(before)})
        self.assertEqual(response["code"], "DECISION_FINAL")
        self.assertEqual(s.data["accepted_files"], s.data["files"])

    def test_resume_refuses_changed_workspace_and_partial_checkpoint(self):
        s = self.make()
        s.call("list")
        (s.app / "blog/byline.bag").write_text("changed")
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_WORKSPACE_MISMATCH"):
            Session(ROOT, s.directory, resume=True)
        s2 = self.make()
        s2.journal.append("unexpected_write")
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_JOURNAL_MISMATCH"):
            Session(ROOT, s2.directory, resume=True)

    def test_setup_failure_is_saved_as_error(self):
        with patch("pilot.harness.run.versions", side_effect=FileNotFoundError("sandbox missing")):
            result = dry_run(ROOT, self.directory / "failed")
        self.assertEqual(result["outcome"], "ERROR")
        self.assertEqual(load(self.directory / "failed/result.json")["pilot_status"], "NOT_RUN")

    @unittest.skipUnless(SANDBOX, "Linux bwrap required")
    def test_tool_timeout_is_budget_stop(self):
        s = self.make()
        response, _ = Sandbox(ROOT, s.app, tool_seconds=0.0001).call("C", "check")
        self.assertEqual(response["status"], "BUDGET_STOP")

    @unittest.skipUnless(SANDBOX and TSC, "local bwrap and TypeScript required")
    def test_ts_test_cannot_read_runtime_repo_or_projectstore(self):
        s = self.make("B")
        (s.app / ".bagaev").mkdir()
        (s.app / ".bagaev" / "private-marker").write_text("secret")
        (s.app / "test" / "isolation.test.ts").write_text('''
import {test} from "node:test";
import {readFileSync} from "node:fs";
import {throws} from "node:assert/strict";
test("private_paths_inaccessible", () => {
  for (const path of ["/workspace/.bagaev/private-marker", "/runtime/ref/bagaev_ref/change/store.py", HOST_ORACLE_PATH])
    throws(() => readFileSync(path));
});
'''.replace('HOST_ORACLE_PATH', json.dumps(str(ROOT / 'pilot/authorship/oracle/run.py'))))
        result, _ = Sandbox(ROOT, s.app).call("B", "test")
        found = [t for t in result.get("tests", []) if t["test"].endswith("private_paths_inaccessible")]
        self.assertEqual(len(found), 1, result)
        self.assertEqual(found[0]["status"], "PASS", result)

    @unittest.skipUnless(SANDBOX, "Linux bwrap required")
    def test_c06_real_provider_reset_preserves_open_clauses(self):
        result = resume_hook(ROOT, self.directory / "resume", "C")
        self.assertTrue(result["provider_killed"] and result["state_equal"])

    @unittest.skipUnless(SANDBOX, "Linux bwrap required")
    def test_c07_actual_cas_rejects_stale_candidate(self):
        self.assertEqual(head_hook(ROOT, self.directory / "head", "C")["code"], "STALE_BASE")

    @unittest.skipUnless(SANDBOX, "Linux bwrap required")
    def test_c12_export_unavailable_in_all_tool_paths(self):
        self.assertEqual(unavailable_hook(ROOT, self.directory / "hidden", "C")["outcome"], "PASS")

    @unittest.skipUnless(SANDBOX and Path("/usr/bin/node").exists(), "local bwrap and Node required")
    def test_accepted_candidate_nonzero_exit_is_false_accept(self):
        s = self.make("A", initial_source=ROOT / "pilot/authorship/reference/ts")
        cli = s.app / "src/cli.ts"
        old = cli.read_bytes()
        self.assertEqual(old.decode().count("exit(main(argv.slice(2)));"), 1)
        cli.write_text(old.decode().replace("exit(main(argv.slice(2)));", "main(argv.slice(2)); exit(1);"))
        s.initialize()
        receipt = s.call("accept")
        self.assertEqual(receipt["status"], "accepted")
        result = posthoc(ROOT, "A", s.app, receipt, s.control / "posthoc.json", accepted_sources=s.data["accepted_files"])
        self.assertEqual(result["assessment"], "ASSESSED")
        self.assertTrue(result["false_accept"])
        self.assertTrue(any(c["response"].get("code") == "CLI_EXIT" for c in result["calls"]))
        self.assertIn("cli-contract", result["oracle"]["failed"])
        self.assertFalse(any(c["infrastructure_error"] for c in result["calls"]))

    @unittest.skipUnless(SANDBOX and Path("/usr/bin/node").exists(), "local bwrap and Node required")
    def test_accepted_status_error_with_correct_value_is_false_accept(self):
        s = self.make("A", initial_source=ROOT / "pilot/authorship/reference/ts")
        cli = s.app / "src/cli.ts"
        source = cli.read_text()
        before = 'status: "ok", byline:'
        self.assertEqual(source.count(before), 1)
        cli.write_text(source.replace(before, 'status: "error", byline:'))
        s.initialize()
        receipt = s.call("accept")
        self.assertEqual(receipt["status"], "accepted")
        result = posthoc(ROOT, "A", s.app, receipt, s.control / "posthoc.json", accepted_sources=s.data["accepted_files"])
        self.assertEqual(result["assessment"], "ASSESSED")
        self.assertTrue(result["false_accept"])
        self.assertIn("cli-contract", result["oracle"]["failed"])
        self.assertIn("byline-a_101", result["oracle"]["failed"])
        self.assertFalse(any(c["infrastructure_error"] for c in result["calls"]))

    @unittest.skipUnless(SANDBOX, "Linux bwrap required")
    def test_closed_selector_never_exposes_neighbors_or_expectations(self):
        def task(tid, separator, marker):
            return {"id": tid, "case": "C10", "initial": "multi-author",
                    "public": {"instruction": "Локально поменяй разделитель", "separator": separator},
                    "expected": {"bylines": {"a_101": marker, "a_102": "OTHER_PRIVATE_EXPECTATION"}}}
        package = {"format": "bagaev-pilot-closed/1", "tasks": [task("first", " + ", "EXPECTED_SECRET"),
                                                                 task("neighbor", "NEIGHBOR_SEPARATOR", "NEIGHBOR_SECRET")]}
        payload, nonce = self.directory / "payload.json", self.directory / "nonce.bin"
        save(payload, package)
        nonce.write_bytes(bytes(range(32)))
        digest = commitment(payload.read_bytes(), nonce.read_bytes())
        self.assertEqual(reveal(payload, nonce, digest), validate(package))
        with self.assertRaisesRegex(ValueError, "COMMITMENT_MISMATCH"):
            reveal(payload, nonce, "0" * 64)
        s = materialize(ROOT, payload, nonce, digest, "first", "C", self.directory / "closed")
        visible = encoded(s.context()).decode() + "\n".join(p.read_text() for p in s.app.rglob("*")
                                                                if p.is_file() and ".bagaev" not in p.parts)
        for forbidden in ("EXPECTED_SECRET", "OTHER_PRIVATE_EXPECTATION", "NEIGHBOR_SEPARATOR", "NEIGHBOR_SECRET"):
            self.assertNotIn(forbidden, visible)
        self.assertIn(" + ", encoded(s.context()).decode())
        # Подготовка не подменяет приложение готовым target-решением.
        self.assertIn('" · "', (s.app / "blog/byline.bag").read_text())


if __name__ == "__main__":
    unittest.main()
