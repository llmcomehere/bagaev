#!/usr/bin/env python3
"""Run the reviewed L0 checks on an exact Git candidate in isolation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import time
from pathlib import Path

CHECK_CANDIDATE_SHA256 = "ce133b743c1fb253561b404216602c9537c1609c8071478f7787d19a6489b8c5"
VALIDATE_DOCS_SHA256 = "01aa915b4aaa6f9dc9e8d167dc8fec1c177184e3cb03043d372cc8aeba2ce1d3"
SHA1 = re.compile(r"[0-9a-f]{40}")
MAX_PROCESSES = 32
MAX_OUTPUT = 256 * 1024
WALL_SECONDS = 30.0

RUNNER = r"""
import contextlib
import io
import json
import platform
import resource
import unittest

limit = int(__import__('sys').argv[1])
resource.setrlimit(resource.RLIMIT_NPROC, (limit, limit))
captured = io.StringIO()
with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
    suite = unittest.defaultTestLoader.discover('/candidate/tests', pattern='test_l0.py')
    selected = suite.countTestCases()
    if selected == 0:
        raise RuntimeError('no L0 tests selected')
    result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
payload = {
    'python_version': platform.python_version(),
    'tests_selected': selected,
    'tests_run': result.testsRun,
    'failures': len(result.failures),
    'errors': len(result.errors),
    'skipped': len(result.skipped),
    'expected_failures': len(result.expectedFailures),
    'unexpected_successes': len(result.unexpectedSuccesses),
    'successful': (
        result.wasSuccessful()
        and result.testsRun == selected
        and not result.skipped
        and not result.expectedFailures
        and not result.unexpectedSuccesses
    ),
    'detail': captured.getvalue()[:65536],
}
print(json.dumps(payload, ensure_ascii=True, separators=(',', ':')))
raise SystemExit(0 if payload['successful'] else 1)
"""


class HarnessError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path, expected: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise HarnessError("trusted.copy", "installed checking tools must be regular files")
    resolved = path.resolve(strict=True)
    if _sha256(resolved) != expected:
        raise HarnessError("trusted.hash", "installed checking tool hash does not match the pinned version")
    return resolved


def _load_helper(repository: Path):
    installed = Path(__file__)
    if installed.is_symlink() or not installed.is_file():
        raise HarnessError("trusted.copy", "installed L0 harness must be a regular file")
    installed = installed.resolve(strict=True)
    helper = _regular(installed.with_name("check_candidate.py"), CHECK_CANDIDATE_SHA256)
    _regular(installed.with_name("validate_docs.py"), VALIDATE_DOCS_SHA256)
    if installed.is_relative_to(repository) or helper.is_relative_to(repository):
        raise HarnessError("trusted.copy", "run a reviewed installed harness outside the candidate repository")
    spec = importlib.util.spec_from_file_location("pinned_check_candidate", helper)
    if spec is None or spec.loader is None:
        raise HarnessError("trusted.load", "pinned candidate helper could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return installed, module


def _sandbox(helper, candidate: Path, deadline: float) -> dict[str, object]:
    bwrap = helper.BWRAP
    if not bwrap.is_file() or bwrap.is_symlink():
        raise HarnessError("sandbox.unavailable", "/usr/bin/bwrap is required and must be a regular file")
    command = [
        str(bwrap), "--unshare-user", "--unshare-all", "--clearenv", "--die-with-parent",
        "--new-session", "--disable-userns", "--cap-drop", "ALL",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
    ]
    if Path("/lib64").exists():
        command.extend(["--ro-bind", "/lib64", "/lib64"])
    command.extend([
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(candidate), "/candidate", "--chdir", "/candidate",
        "/usr/bin/python3", "-I", "-B", "-S", "-c", RUNNER, str(MAX_PROCESSES),
    ])
    try:
        returncode, stdout, _stderr = helper._run(
            command, cwd=None, env={}, deadline=deadline, output_limit=MAX_OUTPUT,
        )
    except helper.CandidateError as error:
        raise HarnessError(error.code, error.message) from error
    try:
        payload = json.loads(stdout.decode("utf-8"))
        selected = payload["tests_selected"]
        run = payload["tests_run"]
        count_fields = (
            "failures", "errors", "skipped", "expected_failures", "unexpected_successes",
        )
        if (
            type(selected) is not int or type(run) is not int or selected <= 0 or run != selected
            or not isinstance(payload["python_version"], str)
            or type(payload["successful"]) is not bool
            or any(type(payload[field]) is not int or payload[field] < 0 for field in count_fields)
        ):
            raise ValueError
        complete = all(payload[field] == 0 for field in count_fields)
        if payload["successful"] is not complete or (returncode == 0) is not complete:
            raise ValueError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise HarnessError("sandbox.output", "isolated L0 checks returned invalid output") from error
    payload["process_returncode"] = returncode
    return payload


def check_l0(repository: Path, trusted_commit: str, candidate_commit: str) -> dict[str, object]:
    repository = repository.resolve(strict=True)
    if not repository.is_dir():
        raise HarnessError("input.repository", "repository must be a local directory")
    installed, helper = _load_helper(repository)
    try:
        candidate_report = helper.check_candidate(repository, trusted_commit, candidate_commit)
        if not candidate_report.get("ok"):
            raise HarnessError("candidate.rejected", "pinned candidate validation rejected the revision")

        deadline = time.monotonic() + WALL_SECONDS
        tree = helper._tree(repository, candidate_commit, deadline)
        with tempfile.TemporaryDirectory(prefix="bagaev-l0-") as directory:
            export = Path(directory) / "candidate"
            helper._export(repository, tree, export, deadline)
            test_result = _sandbox(helper, export, deadline)
    except helper.CandidateError as error:
        raise HarnessError(error.code, error.message) from error

    return {
        "schema": "bagaev/l0-check/v1",
        "ok": bool(test_result["successful"]),
        "trusted_commit": trusted_commit,
        "candidate_commit": candidate_commit,
        "harness_sha256": _sha256(installed),
        "pinned_helper_sha256": CHECK_CANDIDATE_SHA256,
        "pinned_validator_sha256": VALIDATE_DOCS_SHA256,
        "candidate_validation": candidate_report,
        "tests": test_result,
        "limits": {
            "candidate_files": helper.MAX_FILES,
            "candidate_file_bytes": helper.MAX_FILE_BYTES,
            "candidate_total_bytes": helper.MAX_TOTAL_BYTES,
            "processes": MAX_PROCESSES,
            "cpu_seconds": 8,
            "memory_bytes": 512 * 1024 * 1024,
            "wall_seconds": WALL_SECONDS,
            "output_bytes": MAX_OUTPUT,
        },
        "sandbox": {
            "candidate_read_only": True,
            "temporary_writes_only": True,
            "network_namespace_unshared": True,
            "environment_cleared": True,
            "unsandboxed_fallback": False,
        },
        "evidence_notice": (
            "Candidate tests execute as untrusted code in the stated sandbox; their output is data, "
            "not authority or proof of language advantage."
        ),
        "merge_authorized": False,
    }


def _failure(code: str, message: str, trusted: str, candidate: str) -> dict[str, object]:
    return {
        "schema": "bagaev/l0-check/v1",
        "ok": False,
        "trusted_commit": trusted if SHA1.fullmatch(trusted) else None,
        "candidate_commit": candidate if SHA1.fullmatch(candidate) else None,
        "error": {"code": code, "message": message},
        "merge_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check one exact bagaev L0 candidate.")
    parser.add_argument("repository", type=Path)
    parser.add_argument("trusted_commit")
    parser.add_argument("candidate_commit")
    arguments = parser.parse_args()
    try:
        report = check_l0(arguments.repository, arguments.trusted_commit, arguments.candidate_commit)
    except (HarnessError, OSError) as error:
        if isinstance(error, HarnessError):
            code, message = error.code, error.message
        else:
            code, message = "filesystem.error", "local filesystem operation failed"
        report = _failure(code, message, arguments.trusted_commit, arguments.candidate_commit)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
