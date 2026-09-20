from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_candidate", ROOT / "tools" / "check_candidate.py")
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    )
    return completed.stdout.strip()


class CandidateCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="bagaev-check-test-")
        self.base = Path(self.temporary.name)
        self.repo = self.base / "repo"
        self.install = self.base / "installed"
        self.repo.mkdir()
        self.install.mkdir()
        shutil.copy2(ROOT / "tools" / "check_candidate.py", self.install)
        shutil.copy2(ROOT / "tools" / "validate_docs.py", self.install)
        run(["/usr/bin/git", "init", "-q", "-b", "main"], self.repo)
        self.git_env = {
            "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
            "GIT_AUTHOR_NAME": "Synthetic Test",
            "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic Test",
            "HOME": str(self.base / "empty-home"),
            "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin",
        }
        self._write_valid_tree()
        self.base_commit = self._commit("base")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_valid_tree(self) -> None:
        required = [
            "README.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md",
            ".github/CODEOWNERS", ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/research_proposal.yml",
        ]
        for relative in required:
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic fixture\n", encoding="utf-8")
        foundation = self.repo / "docs" / "foundation.md"
        foundation.parent.mkdir(parents=True)
        headings = [f"### B{number:02d}. Principle" for number in range(1, 19)]
        rows = [f"| P0-{number:02d} | Event | Outcome |" for number in range(1, 11)]
        foundation.write_text("\n".join(headings + rows) + "\n", encoding="utf-8")

    def _commit(self, message: str) -> str:
        run(["/usr/bin/git", "add", "-A"], self.repo, self.git_env)
        run(["/usr/bin/git", "commit", "-q", "-m", message], self.repo, self.git_env)
        return run(["/usr/bin/git", "rev-parse", "HEAD"], self.repo, self.git_env)

    def _git_bytes(self, arguments: list[str], payload: bytes) -> bytes:
        completed = subprocess.run(
            ["/usr/bin/git", *arguments], cwd=self.repo, env=self.git_env,
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return completed.stdout.strip()

    def _raw_path_commit(self, parts: tuple[bytes, ...]) -> str:
        blob = self._git_bytes(["hash-object", "-w", "--stdin"], b"synthetic\n")
        tree = self._git_bytes(
            ["hash-object", "-t", "tree", "--literally", "-w", "--stdin"],
            b"100644 " + parts[-1] + b"\0" + bytes.fromhex(blob.decode("ascii")),
        )
        for part in reversed(parts[:-1]):
            tree = self._git_bytes(
                ["hash-object", "-t", "tree", "--literally", "-w", "--stdin"],
                b"40000 " + part + b"\0" + bytes.fromhex(tree.decode("ascii")),
            )
        commit = self._git_bytes(["commit-tree", tree.decode("ascii")], b"raw path fixture\n")
        return commit.decode("ascii")

    def _installed_module(self):
        spec = importlib.util.spec_from_file_location(
            "installed_check_candidate", self.install / "check_candidate.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_ordinary_candidate_validates_and_reports_control_changes(self) -> None:
        (self.repo / "README.md").write_text("candidate\n", encoding="utf-8")
        (self.repo / "AGENTS.md").write_text("candidate policy data\n", encoding="utf-8")
        candidate = self._commit("candidate")
        module = self._installed_module()
        with mock.patch.object(module, "run_validator_sandbox", return_value=[]):
            report = module.check_candidate(self.repo, self.base_commit, candidate)
        self.assertTrue(report["ok"])
        self.assertIn("AGENTS.md", report["sensitive_control_paths"]["items"])
        self.assertFalse(report["semantic_prompt_injection_scan"])
        self.assertFalse(report["merge_authorized"])

    def test_missing_sandbox_fails_closed(self) -> None:
        module = self._installed_module()
        candidate_dir = self.base / "candidate-data"
        candidate_dir.mkdir()
        with mock.patch.object(module, "BWRAP", self.base / "missing-bwrap"):
            with self.assertRaises(module.CandidateError) as caught:
                module.run_validator_sandbox(
                    candidate_dir, self.install / "validate_docs.py", module.time.monotonic() + 5,
                )
        self.assertEqual(caught.exception.code, "sandbox.unavailable")

    def test_symlink_and_escape_paths_are_rejected(self) -> None:
        os.symlink("README.md", self.repo / "linked.md")
        candidate = self._commit("symlink")
        module = self._installed_module()
        with self.assertRaises(module.CandidateError) as caught:
            module.check_candidate(self.repo, self.base_commit, candidate)
        self.assertEqual(caught.exception.code, "path.indirect")
        with self.assertRaises(module.CandidateError) as escape:
            module._safe_path(b"../escape")
        self.assertEqual(escape.exception.code, "path.unsafe")

    def test_raw_aliased_paths_are_rejected_before_export(self) -> None:
        module = self._installed_module()
        cases = (
            ((b".", b"README.md"), b"./README.md"),
            ((b"docs", b".", b"foundation.md"), b"docs/./foundation.md"),
        )
        for parts, raw_path in cases:
            with self.subTest(raw_path=raw_path):
                candidate = self._raw_path_commit(parts)
                listing = subprocess.check_output(
                    ["/usr/bin/git", "ls-tree", "-rlz", "--full-tree", candidate],
                    cwd=self.repo, env=self.git_env,
                )
                self.assertIn(b"\t" + raw_path + b"\0", listing)
                with mock.patch.object(module.Path, "write_bytes") as write_bytes:
                    with self.assertRaises(module.CandidateError) as caught:
                        module.check_candidate(self.repo, self.base_commit, candidate)
                self.assertEqual(caught.exception.code, "path.unsafe")
                write_bytes.assert_not_called()

    def test_full_commit_ids_and_resource_limits_are_enforced(self) -> None:
        module = self._installed_module()
        with self.assertRaises(module.CandidateError) as abbreviated:
            module.check_candidate(self.repo, self.base_commit[:12], self.base_commit)
        self.assertEqual(abbreviated.exception.code, "input.commit")
        with mock.patch.object(module, "MAX_FILES", 1):
            with self.assertRaises(module.CandidateError) as limited:
                module.check_candidate(self.repo, self.base_commit, self.base_commit)
        self.assertEqual(limited.exception.code, "limit.files")
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(self.install / "check_candidate.py"),
             str(self.repo), "not-a-full-commit", self.base_commit],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(completed.returncode, 1)
        failure = json.loads(completed.stdout)
        self.assertIsNone(failure["trusted_commit"])
        self.assertFalse(failure["changed_paths"]["complete"])
        self.assertEqual(completed.stderr, "")

    def test_candidate_validator_and_sitecustomize_are_never_executed(self) -> None:
        sentinel = self.base / "candidate-executed"
        malicious = f"raise RuntimeError('candidate validator executed: {sentinel}')\n"
        (self.repo / "tools").mkdir()
        (self.repo / "tools" / "validate_docs.py").write_text(malicious, encoding="utf-8")
        (self.repo / "sitecustomize.py").write_text(malicious, encoding="utf-8")
        candidate = self._commit("candidate scripts are data")
        module = self._installed_module()
        if os.environ.get("BAGAEV_HOST_BWRAP_SMOKE") == "1":
            report = module.check_candidate(self.repo, self.base_commit, candidate)
            self.assertTrue(report["ok"])
        else:
            try:
                module.check_candidate(self.repo, self.base_commit, candidate)
            except module.CandidateError as error:
                self.assertIn(error.code, {"sandbox.failed", "sandbox.unavailable"})
        self.assertFalse(sentinel.exists())

    def test_python_startup_paths_are_reported_sensitive_without_execution(self) -> None:
        sentinel = self.base / "startup-hook-executed"
        malicious = (
            "from pathlib import Path\n"
            f"Path({str(sentinel)!r}).write_text('executed\\n', encoding='utf-8')\n"
        )
        startup_paths = (
            "sitecustomize.py",
            "nested/UserCustomize.PY",
            "vendor/extra.PTH",
        )
        for relative in startup_paths:
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(malicious, encoding="utf-8")
        candidate = self._commit("python startup paths are control data")
        module = self._installed_module()
        if os.environ.get("BAGAEV_HOST_BWRAP_SMOKE") == "1":
            report = module.check_candidate(self.repo, self.base_commit, candidate)
        else:
            with mock.patch.object(module, "run_validator_sandbox", return_value=[]):
                report = module.check_candidate(self.repo, self.base_commit, candidate)
        expected = sorted(startup_paths)
        self.assertTrue(report["ok"])
        self.assertEqual(report["changed_paths"]["items"], expected)
        self.assertEqual(report["sensitive_control_paths"]["items"], expected)
        self.assertTrue(report["sensitive_control_paths"]["complete"])
        self.assertFalse(sentinel.exists())

    def test_host_bwrap_boundary_probe_or_direct_fail_closed(self) -> None:
        module = self._installed_module()
        candidate_dir = self.base / "probe-candidate"
        candidate_dir.mkdir()
        probe = self.base / "probe-validator.py"
        probe.write_text(
            "import json, os, resource, socket\n"
            "from pathlib import Path\n"
            "def check(root):\n"
            "    connected = False\n"
            "    try:\n"
            "        socket.create_connection(('192.0.2.1', 9), timeout=0.1)\n"
            "        connected = True\n"
            "    except OSError:\n"
            "        pass\n"
            "    return [json.dumps({'home': Path('/home').exists(),\n"
            "        'sensitive_env': sorted(k for k in os.environ if any(x in k.upper() for x in ('TOKEN','SECRET','KEY','HOME'))),\n"
            "        'nproc': resource.getrlimit(resource.RLIMIT_NPROC)[0],\n"
            "        'network_connected': connected}, sort_keys=True)]\n",
            encoding="utf-8",
        )
        try:
            result = module.run_validator_sandbox(
                candidate_dir, probe, module.time.monotonic() + 5,
            )
        except module.CandidateError as error:
            self.assertNotEqual(os.environ.get("BAGAEV_HOST_BWRAP_SMOKE"), "1")
            self.assertIn(error.code, {"sandbox.failed", "sandbox.unavailable"})
        else:
            observed = json.loads(result[0])
            self.assertEqual(
                observed,
                {
                    "home": False, "network_connected": False,
                    "nproc": 32, "sensitive_env": [],
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
