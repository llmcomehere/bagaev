"""Независимый оракул вызывается только после решения; его файлы не монтируются кандидату."""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path

from .common import encoded, manifest, save, sha
from .sandbox import Sandbox, child_limits


def classify(envelope, decode_cli_response):
    """Код/ответ запущенного кандидата — предмет проверки, не ошибка стенда."""
    if not isinstance(envelope, dict) or envelope.get("started") is not True:
        return {"status": "error", "code": "CLI_LAUNCH_FAILED"}, True
    return decode_cli_response(envelope["returncode"], envelope["stdout"], envelope.get("stderr", "")), False


def posthoc(repo: Path, arm: str, candidate: Path, receipt: dict, output: Path, *, expected_bylines=None, accepted_sources=None):
    spec = importlib.util.spec_from_file_location("isolated_pilot_oracle", repo / "pilot/authorship/oracle/run.py")
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    candidate_inputs = manifest(candidate)
    if expected_bylines is not None:
        oracle.FIX["expected_observations"]["bylines"] = dict(expected_bylines)
    calls = []

    def isolated_call(instance, command, app=None, **opts):
        selected = Path(app or instance.app)
        instance.state.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pilot-judge-input-") as tmp:
            inputs = Path(tmp)
            argv = [x.replace("{app}", "/workspace").replace("{state}", "/state") for x in instance.spec["cli"]]
            argv = ["/runtime/" + x if x.startswith("pilot/") else x for x in argv]
            argv.append(command)
            for key, value in opts.items():
                if isinstance(value, (dict, list)):
                    path = inputs / f"{key}.json"
                    save(path, value)
                    value = f"/input/{path.name}"
                argv.extend(["--" + key.replace("_", "-"), str(value)])
            prefix = Sandbox(repo, selected).argv()[:-3]
            workspace_mount = prefix.index(str(selected.resolve())) - 1
            prefix[workspace_mount] = "--ro-bind"
            # argv() завершён '-- python bridge'; исключаем эти три элемента.
            prefix += ["--bind", str(instance.state), "/state", "--ro-bind", str(inputs), "/input"]
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                process = subprocess.Popen(prefix + ["--", "/usr/bin/python3", "/runtime/pilot/harness/judge_runner.py"],
                                           stdin=subprocess.PIPE, stdout=out, stderr=err,
                                           start_new_session=True, env={"PATH": "/usr/bin:/bin"}, preexec_fn=child_limits)
                timed_out = False
                try:
                    process.communicate(encoded({"argv": argv}), timeout=30)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    process.stdin.close()
                out.seek(0)
                err.seek(0)
                raw, stderr = out.read(), err.read()
            try:
                envelope = json.loads(raw)
            except ValueError:
                envelope = None
            if timed_out or process.returncode or envelope is None:
                result = {"status": "error", "code": "JUDGE_TIMEOUT" if timed_out else "SANDBOX_OR_WRAPPER_FAILED",
                          "returncode": process.returncode}
                infrastructure_error = True
            else:
                result, infrastructure_error = classify(envelope, oracle.decode_cli_response)
            if result.get("status") not in ("ok", "rejected"):
                instance.failures.append(dict(result, command=command))
            calls.append({"command": command, "arguments": opts, "input_app": str(selected), "response": result,
                          "infrastructure_error": infrastructure_error, "runner_receipt": envelope,
                          "stdout_sha256": sha(raw), "stderr_sha256": sha(stderr), "returncode": process.returncode})
            return result

    oracle.Arm.run = isolated_call
    report = oracle.run(arm, candidate=candidate)
    accepted = receipt.get("status") == "accepted" or (receipt.get("status") == "succeeded"
                                                       and receipt.get("operation") == "accept")
    tool_error = any(c["infrastructure_error"] for c in calls)
    if manifest(candidate) != candidate_inputs or accepted and accepted_sources != candidate_inputs:
        tool_error = True
    result = {"format": "bagaev-pilot-posthoc/1", "acceptance_receipt": receipt,
              "candidate_inputs": candidate_inputs,
              "oracle": report, "calls": calls,
              "assessment": "INCONCLUSIVE" if tool_error else "ASSESSED",
              "false_accept": None if tool_error else accepted and report["outcome"] != "PASS",
              "note": "Проверка после решения. Не передавать исполнителю до конца всего измерительного блока."}
    save(output, result)
    return result
