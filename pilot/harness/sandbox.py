"""Linux bwrap: нет сети, домашнего каталога, oracle, reference и закрытых задач.

Доверенный runtime доступен процессам инструмента; агент получает только ответы посредника.
При отсутствии sandbox нет небезопасного fallback.
"""
from __future__ import annotations

import json
import os
import resource
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from .common import encoded, save, sha


class SandboxError(RuntimeError):
    pass


def base_command():
    return ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--clearenv",
            "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
            "--setenv", "LANG", "C.UTF-8", "--setenv", "PYTHONDONTWRITEBYTECODE", "1"]


def child_limits():
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


class Sandbox:
    def __init__(self, repo: Path, app: Path, tool_seconds=30):
        self.repo, self.app, self.tool_seconds = repo.resolve(), app.resolve(), tool_seconds

    def argv(self, rpc=None):
        paths = [(self.repo / "ref", "/runtime/ref"),
                 (self.repo / "pilot/harness/bridge.py", "/runtime/pilot/harness/bridge.py"),
                 (self.repo / "pilot/harness/judge_runner.py", "/runtime/pilot/harness/judge_runner.py"),
                 (self.repo / "pilot/authorship/links-ts", "/runtime/pilot/authorship/links-ts"),
                 (self.repo / "pilot/authorship/arms", "/runtime/pilot/authorship/arms")]
        tsc = self.repo / "pilot/writability/node_modules/typescript"
        if tsc.is_dir():
            paths.append((tsc.resolve(), "/runtime/pilot/writability/node_modules/typescript"))
        argv = base_command() + ["--bind", str(self.app), "/workspace", "--chdir", "/workspace",
                                  "--setenv", "PYTHONPATH", "/runtime/ref"]
        for source, dest in paths:
            argv.extend(["--ro-bind", str(source), dest])
        if rpc is not None:
            argv.extend(["--bind", str(rpc), "/rpc"])
        return argv + ["--", "/usr/bin/python3", "/runtime/pilot/harness/bridge.py"]

    @staticmethod
    def test_job(request, deadline):
        """Untrusted TS исполняется отдельно от ref, store и RPC; никакой произвольной команды."""
        job = json.loads(request.read_bytes())
        from pathlib import PurePosixPath
        def safe(name):
            p = PurePosixPath(name)
            return not p.is_absolute() and p.as_posix() == name and all(x not in (".", "..") and not x.startswith(".") for x in p.parts)
        if not safe(job["test"]) or job["test"] not in job["files"] or not job["test"].endswith(".test.ts") \
                or not all(safe(x) for x in job["files"]):
            raise ValueError("UNSAFE_TEST_JOB")
        with tempfile.TemporaryDirectory(prefix="pilot-untrusted-test-") as tmp:
            root = Path(tmp)
            for rel, content in job["files"].items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            argv = base_command() + ["--ro-bind", str(root), "/candidate", "--chdir", "/candidate", "--",
                                      "/usr/bin/node", "--no-warnings", "--test", "--test-reporter=tap", "/candidate/" + job["test"]]
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                p = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True,
                                     env={"PATH": "/usr/bin:/bin"}, preexec_fn=child_limits)
                try:
                    p.wait(timeout=max(0.001, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
                out.seek(0)
                err.seek(0)
                result = {"returncode": p.returncode, "stdout": out.read().decode(errors="replace"),
                          "stderr": err.read().decode(errors="replace")}
        save(request.with_name(request.name.replace(".request.json", ".response.json")), result)

    def call(self, arm: str, action: str, **arguments):
        started = time.monotonic()
        request = dict(arm=arm, action=action, **arguments)
        with tempfile.TemporaryDirectory(prefix="pilot-test-rpc-") as rpc_dir, \
                tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            rpc = Path(rpc_dir)
            proc = subprocess.Popen(self.argv(rpc), stdin=subprocess.PIPE, stdout=out, stderr=err,
                                    start_new_session=True, env={"PATH": "/usr/bin:/bin"}, preexec_fn=child_limits)
            deadline = started + self.tool_seconds
            try:
                proc.stdin.write(encoded(request))
                proc.stdin.close()
                handled = set()
                while proc.poll() is None:
                    if time.monotonic() >= deadline:
                        raise subprocess.TimeoutExpired(proc.args, self.tool_seconds)
                    for path in rpc.glob("*.request.json"):
                        if path.name not in handled:
                            self.test_job(path, deadline)
                            handled.add(path.name)
                    time.sleep(0.005)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                return {"status": "BUDGET_STOP", "code": "TOOL_TIME_LIMIT"}, time.monotonic() - started
            finally:
                proc.stdin.close()
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            out.seek(0)
            err.seek(0)
            stdout, stderr = out.read(), err.read()
        if proc.returncode or len(stdout) > 1024 * 1024:
            return {"status": "ERROR", "code": "SANDBOX_OR_TOOL_FAILED", "returncode": proc.returncode,
                    "stdout_sha256": sha(stdout), "stderr": stderr.decode(errors="replace")[:1500]}, time.monotonic() - started
        try:
            result = json.loads(stdout)
        except ValueError:
            result = {"status": "ERROR", "code": "TOOL_PROTOCOL_ERROR", "stdout_sha256": sha(stdout)}
        return result, time.monotonic() - started
