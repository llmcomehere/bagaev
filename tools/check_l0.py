#!/usr/bin/env python3
"""Run the reviewed L0 checks on an exact Git candidate in isolation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
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
MEMORY_MAX_BYTES = 512 * 1024 * 1024
MEMORY_SWAP_MAX_BYTES = 0
CPU_QUOTA_PERCENT = 50
CANDIDATE_VALIDATION_WALL_SECONDS = 30.0
EXECUTION_UNIT_SECONDS = 8.0
EXECUTION_COMMAND_SECONDS = 10.0
CLEANUP_SECONDS = 3.0
TOTAL_WALL_SECONDS = 50.0
EXPECTED_ACCEPTANCE_CASES = 20
SYSTEMD_RUN = Path("/usr/bin/systemd-run")
SYSTEMCTL = Path("/usr/bin/systemctl")

UNIT_RUNNER = r"""
import os
import sys
import time
from pathlib import Path

expected_memory = int(sys.argv[1])
expected_swap = int(sys.argv[2])
expected_tasks = int(sys.argv[3])
expected_cpu_percent = int(sys.argv[4])
latest_candidate_start = float(sys.argv[5])
command = sys.argv[6:]

try:
    relative = next(
        line.split('::', 1)[1]
        for line in Path('/proc/self/cgroup').read_text(encoding='ascii').splitlines()
        if line.startswith('0::')
    )
    root = Path('/sys/fs/cgroup').resolve(strict=True)
    group = (root / relative.lstrip('/')).resolve(strict=True)
    if not group.is_relative_to(root):
        raise ValueError
    memory = (group / 'memory.max').read_text(encoding='ascii').strip()
    swap = (group / 'memory.swap.max').read_text(encoding='ascii').strip()
    tasks = (group / 'pids.max').read_text(encoding='ascii').strip()
    cpu_quota, cpu_period = (group / 'cpu.max').read_text(encoding='ascii').split()
    if (
        memory == 'max' or int(memory) > expected_memory
        or swap == 'max' or int(swap) > expected_swap
        or tasks == 'max' or int(tasks) > expected_tasks
        or cpu_quota == 'max'
        or int(cpu_quota) * 100 > expected_cpu_percent * int(cpu_period)
        or time.monotonic() > latest_candidate_start
        or not command
    ):
        raise ValueError
except (OSError, StopIteration, ValueError):
    raise SystemExit('aggregate resource preflight failed')

os.execv(command[0], command)
"""

RUNNER = r"""
import json
import os
import platform
import signal
import subprocess
import tempfile
from pathlib import Path

PYTHON = '/usr/bin/python3'
CLI = '/candidate/src/bagaev_l0.py'
EXAMPLES = Path('/candidate/examples/l0')
RESULT_SCHEMA = 'bagaev/l0-result/v1'
CASE_SECONDS = 2.0
CAPTURE_BYTES = 65536
work = Path(tempfile.mkdtemp(prefix='acceptance-', dir='/tmp'))
failures = []
cases_run = 0


class CheckFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise CheckFailure(message)


def write(name, content):
    path = work / name
    if isinstance(content, str):
        path.write_text(content, encoding='utf-8')
    else:
        path.write_text(json.dumps(content, ensure_ascii=False, separators=(',', ':')),
                        encoding='utf-8')
    return path


def run_child(arguments):
    process = subprocess.Popen(
        arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=CASE_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        raise CheckFailure('candidate child exceeded its case time limit')
    require(len(stdout) <= CAPTURE_BYTES and len(stderr) <= CAPTURE_BYTES,
            'candidate child output exceeded its case limit')
    return process.returncode, stdout, stderr


def cli(*arguments):
    returncode, stdout, _stderr = run_child(
        [PYTHON, '-I', '-B', '-S', CLI, *(str(item) for item in arguments)]
    )
    try:
        payload = json.loads(stdout.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckFailure('candidate CLI returned invalid JSON') from error
    require(isinstance(payload, dict) and payload.get('schema') == RESULT_SCHEMA,
            'candidate CLI returned the wrong result schema')
    return returncode, payload


def expect_success(arguments, *, command, result=None):
    returncode, payload = cli(command, *arguments)
    require(returncode == 0 and payload.get('ok') is True,
            'candidate CLI did not return success')
    require(payload.get('command') == command, 'candidate CLI returned the wrong command')
    if result is not None:
        require(payload.get('result') == result, 'candidate CLI returned the wrong result')
    return payload


def expect_error(arguments, code):
    returncode, payload = cli(*arguments)
    require(returncode == 2 and payload.get('ok') is False,
            'candidate CLI did not return a structured refusal')
    require(payload.get('command') == arguments[0],
            'candidate CLI returned the wrong refusal command')
    error = payload.get('error')
    require(isinstance(error, dict) and error.get('code') == code,
            'candidate CLI returned the wrong refusal code')


def case(name, action):
    global cases_run
    try:
        action()
    except Exception as error:
        failures.append({'case': name, 'reason': str(error)[:200]})
    cases_run += 1


tag_program = EXAMPLES / 'tag_list.json'
tag_patch = EXAMPLES / 'tag_unique_sorted.patch'
patched_program = work / 'patched.json'


def patch_atomic():
    before = tag_program.read_bytes()
    payload = expect_success((tag_program, tag_patch), command='patch')
    require(tag_program.read_bytes() == before, 'patch changed the original program')
    program = payload.get('program')
    require(isinstance(program, dict), 'patch did not return a complete program')
    patched_program.write_text(
        json.dumps(program, ensure_ascii=False, separators=(',', ':')), encoding='utf-8'
    )


case('patch-atomic', patch_atomic)

observations = (
    ('list-preserves', ['red', 'blue', 'red'], ['red', 'blue', 'red'], ['blue', 'red']),
    ('empty', [], [], []),
    ('duplicates', ['blue', 'blue'], ['blue', 'blue'], ['blue']),
    ('reversed', ['red', 'blue'], ['red', 'blue'], ['blue', 'red']),
    ('distinct', ['blue', 'green', 'red'], ['blue', 'green', 'red'],
     ['blue', 'green', 'red']),
)
for name, tags, before, after in observations:
    def observation(tags=tags, before=before, after=after, name=name):
        inputs = write('input-' + name + '.json', {'tags': tags})
        require(after == sorted(set(tags)), 'ordinary Python comparison disagrees')
        expect_success((tag_program, inputs), command='run', result=before)
        expect_success((patched_program, inputs), command='run', result=after)
    case(name, observation)


def composed():
    expect_success(
        (EXAMPLES / 'composed.json', EXAMPLES / 'composed_inputs.json'),
        command='run', result=4,
    )


case('composed', composed)

base_program = json.loads(tag_program.read_text(encoding='utf-8'))
base_patch = json.loads(tag_patch.read_text(encoding='utf-8'))

wrong_type = write('wrong-type.json', {'tags': 3})
duplicate_keys = write('duplicate-keys.json', '{"tags":[],"tags":[]}')
duplicate_node = json.loads(json.dumps(base_program))
duplicate_node['nodes'].append(json.loads(json.dumps(duplicate_node['nodes'][0])))
missing_reference = json.loads(json.dumps(base_program))
missing_reference['nodes'][1]['value']['ref'] = 'absent'
cycle = {
    'schema': 'bagaev/l0-program/v1',
    'nodes': [
        {'id': 'a', 'op': 'identity', 'value': {'ref': 'b'}},
        {'id': 'b', 'op': 'identity', 'value': {'ref': 'a'}},
    ],
    'result': {'ref': 'a'},
}
unknown = json.loads(json.dumps(base_program))
unknown['nodes'][1]['op'] = 'python.eval'
overflow = {
    'schema': 'bagaev/l0-program/v1',
    'nodes': [
        {'id': 'max', 'op': 'literal', 'type': 'int', 'value': 9223372036854775807},
        {'id': 'one', 'op': 'literal', 'type': 'int', 'value': 1},
        {'id': 'sum', 'op': 'int.add', 'left': {'ref': 'max'}, 'right': {'ref': 'one'}},
    ],
    'result': {'ref': 'sum'},
}
stale_patch = json.loads(json.dumps(base_patch))
stale_patch['base'] = 'sha256:' + '0' * 64
invalid_patch = json.loads(json.dumps(base_patch))
invalid_patch['replace'][0]['value']['ref'] = 'absent'
huge_integer = write('huge-integer.json', '{"tags":' + '9' * 5000 + '}')
nested = '[' * 600 + '0' + ']' * 600
deep_program = write(
    'deep-program.json',
    '{"schema":"bagaev/l0-program/v1","nodes":['
    '{"id":"value","op":"literal","type":"int","value":' + nested
    + '}],"result":{"ref":"value"}}',
)
deep_patch = write(
    'deep-patch.json',
    '{"schema":"bagaev/l0-patch/v1","base":"sha256:'
    '7c42c5cb58af9c896353c5043e78f05fb884b19df9a59590f7d773decd9d78c0",'
    '"add":[],"replace":[{"id":"result","op":"literal","type":"int","value":'
    + nested + '}]}',
)
eager_overflow = {
    'schema': 'bagaev/l0-program/v1',
    'nodes': [
        {'id': 'result', 'op': 'literal', 'type': 'int', 'value': 0},
        {'id': 'max', 'op': 'literal', 'type': 'int', 'value': 9223372036854775807},
        {'id': 'one', 'op': 'literal', 'type': 'int', 'value': 1},
        {'id': 'unused_overflow', 'op': 'int.add', 'left': {'ref': 'max'},
         'right': {'ref': 'one'}},
    ],
    'result': {'ref': 'result'},
}

refusals = (
    ('wrong-type', ('run', tag_program, wrong_type), 'value.type'),
    ('duplicate-key', ('run', tag_program, duplicate_keys), 'json.duplicate_key'),
    ('duplicate-node', ('check', write('duplicate-node.json', duplicate_node)), 'node.duplicate'),
    ('missing-reference', ('check', write('missing-reference.json', missing_reference)),
     'reference.missing'),
    ('cycle', ('check', write('cycle.json', cycle)), 'graph.cycle'),
    ('unknown-operation', ('check', write('unknown.json', unknown)), 'operation.unknown'),
    ('integer-overflow', ('run', write('overflow.json', overflow), write('empty.json', {})),
     'integer.overflow'),
    ('stale-patch', ('patch', tag_program, write('stale.patch', stale_patch)), 'patch.stale'),
    ('invalid-replacement', ('patch', tag_program, write('invalid.patch', invalid_patch)),
     'reference.missing'),
    ('large-integer', ('run', tag_program, huge_integer), 'integer.overflow'),
    ('deep-malformed', ('check', deep_program), 'value.type'),
    ('deep-malformed-patch', ('patch', tag_program, deep_patch), 'value.type'),
    ('eager-unreachable-overflow',
     ('run', write('eager-overflow.json', eager_overflow), write('eager-inputs.json', {})),
     'integer.overflow'),
)
for name, arguments, code in refusals:
    case(name, lambda arguments=arguments, code=code: expect_error(arguments, code))

candidate_test_code = (
    "import contextlib,io,json,unittest\n"
    "captured=io.StringIO()\n"
    "with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):\n"
    " suite=unittest.defaultTestLoader.discover('/candidate/tests',pattern='test_l0.py')\n"
    " selected=suite.countTestCases()\n"
    " result=unittest.TextTestRunner(stream=captured,verbosity=2).run(suite)\n"
    "payload={'selected':selected,'run':result.testsRun,'failures':len(result.failures),"
    "'errors':len(result.errors),'skipped':len(result.skipped),"
    "'expected_failures':len(result.expectedFailures),"
    "'unexpected_successes':len(result.unexpectedSuccesses),'detail':captured.getvalue()[:32768]}\n"
    "payload['successful']=(result.wasSuccessful() and selected>0 and result.testsRun==selected "
    "and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses)\n"
    "print(json.dumps(payload,ensure_ascii=True,separators=(',',':')))\n"
)
candidate_tests = {
    'authoritative': False,
    'provenance': 'candidate-controlled supplemental evidence; success cannot establish acceptance',
    'successful': False,
}
try:
    test_returncode, test_stdout, _test_stderr = run_child(
        [PYTHON, '-I', '-B', '-S', '-c', candidate_test_code]
    )
    test_payload = json.loads(test_stdout.decode('utf-8'))
    require(isinstance(test_payload, dict), 'candidate tests returned invalid data')
    for field in (
        'selected', 'run', 'failures', 'errors', 'skipped', 'expected_failures',
        'unexpected_successes',
    ):
        candidate_tests[field] = test_payload.get(field)
    detail = test_payload.get('detail')
    candidate_tests['detail'] = detail[:32768] if isinstance(detail, str) else ''
    candidate_tests['process_returncode'] = test_returncode
    candidate_tests['successful'] = bool(test_payload.get('successful')) and test_returncode == 0
except Exception as error:
    candidate_tests['error'] = str(error)[:200]

selected = 1 + len(observations) + 1 + len(refusals)
fixed_successful = not failures and cases_run == selected
successful = fixed_successful and candidate_tests['successful']
payload = {
    'python_version': platform.python_version(),
    'acceptance_version': 'language-l0-acceptance/1',
    'cases_selected': selected,
    'cases_run': cases_run,
    'case_failures': failures,
    'fixed_acceptance_successful': fixed_successful,
    'candidate_tests': candidate_tests,
    'successful': successful,
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
    if (
        module.WALL_SECONDS != CANDIDATE_VALIDATION_WALL_SECONDS
        or module.COMMAND_SECONDS != EXECUTION_COMMAND_SECONDS
    ):
        raise HarnessError("trusted.contract", "pinned helper time limits do not match the harness")
    return installed, module


def _systemd_environment() -> dict[str, str]:
    runtime = f"/run/user/{os.getuid()}"
    return {
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime}/bus",
        "HOME": "/nonexistent",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
        "XDG_RUNTIME_DIR": runtime,
    }


def _require_regular_tool(path: Path, description: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise HarnessError("sandbox.unavailable", f"{description} is required as a regular file")
    return path.resolve(strict=True)


def _request_unit_stop(helper, systemctl: Path, unit: str) -> None:
    try:
        helper._run(
            [str(systemctl), "--user", "stop", unit],
            cwd=None,
            env=_systemd_environment(),
            deadline=time.monotonic() + CLEANUP_SECONDS,
            output_limit=4096,
        )
    except helper.CandidateError:
        # RuntimeMaxSec remains the fail-closed lifetime bound if explicit cleanup fails.
        pass


def _sandbox(helper, candidate: Path, deadline: float) -> dict[str, object]:
    if deadline - time.monotonic() < EXECUTION_COMMAND_SECONDS:
        raise HarnessError("limit.time", "insufficient overall time remains for isolated L0 checks")
    bwrap = helper.BWRAP
    if not bwrap.is_file() or bwrap.is_symlink():
        raise HarnessError("sandbox.unavailable", "/usr/bin/bwrap is required and must be a regular file")
    systemd_run = _require_regular_tool(SYSTEMD_RUN, "/usr/bin/systemd-run")
    systemctl = _require_regular_tool(SYSTEMCTL, "/usr/bin/systemctl")
    sandbox = [
        str(bwrap), "--unshare-user", "--unshare-all", "--clearenv", "--die-with-parent",
        "--new-session", "--disable-userns", "--cap-drop", "ALL",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
    ]
    if Path("/lib64").exists():
        sandbox.extend(["--ro-bind", "/lib64", "/lib64"])
    sandbox.extend([
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(candidate), "/candidate", "--chdir", "/candidate",
        "/usr/bin/python3", "-I", "-B", "-S", "-c", RUNNER,
    ])
    unit = f"bagaev-l0-{os.getpid()}-{time.monotonic_ns()}.service"
    command = [
        str(systemd_run), "--user", "--quiet", "--wait", "--pipe", "--collect",
        "--service-type=exec", "--unit", unit,
        f"--property=MemoryMax={MEMORY_MAX_BYTES}",
        f"--property=MemorySwapMax={MEMORY_SWAP_MAX_BYTES}",
        f"--property=TasksMax={MAX_PROCESSES}",
        f"--property=CPUQuota={CPU_QUOTA_PERCENT}%",
        f"--property=RuntimeMaxSec={EXECUTION_UNIT_SECONDS}s",
        "--property=KillMode=control-group",
        "--property=KillSignal=SIGKILL",
        "--property=FinalKillSignal=SIGKILL",
        "--property=SendSIGKILL=yes",
        "--property=TimeoutStopSec=1s",
        f"--property=LimitAS={MEMORY_MAX_BYTES}",
        f"--property=LimitFSIZE={MAX_OUTPUT}",
        "--property=LimitNOFILE=64",
        "--", "/usr/bin/python3", "-I", "-B", "-S", "-c", UNIT_RUNNER,
        str(MEMORY_MAX_BYTES), str(MEMORY_SWAP_MAX_BYTES), str(MAX_PROCESSES),
        str(CPU_QUOTA_PERCENT), str(deadline - EXECUTION_UNIT_SECONDS), *sandbox,
    ]
    try:
        returncode, stdout, _stderr = helper._run(
            command,
            cwd=None,
            env=_systemd_environment(),
            deadline=deadline,
            output_limit=MAX_OUTPUT,
        )
    except helper.CandidateError as error:
        _request_unit_stop(helper, systemctl, unit)
        raise HarnessError(error.code, error.message) from error
    try:
        payload = json.loads(stdout.decode("utf-8"))
        selected = payload["cases_selected"]
        run = payload["cases_run"]
        case_failures = payload["case_failures"]
        candidate_tests = payload["candidate_tests"]
        candidate_count_fields = (
            "failures", "errors", "skipped", "expected_failures", "unexpected_successes",
        )
        if (
            type(selected) is not int or selected != EXPECTED_ACCEPTANCE_CASES
            or type(run) is not int or run != selected
            or not isinstance(payload["python_version"], str)
            or payload["acceptance_version"] != "language-l0-acceptance/1"
            or not isinstance(case_failures, list)
            or not all(
                isinstance(item, dict)
                and isinstance(item.get("case"), str)
                and isinstance(item.get("reason"), str)
                for item in case_failures
            )
            or type(payload["fixed_acceptance_successful"]) is not bool
            or type(payload["successful"]) is not bool
            or not isinstance(candidate_tests, dict)
            or candidate_tests.get("authoritative") is not False
            or not isinstance(candidate_tests.get("provenance"), str)
            or type(candidate_tests.get("successful")) is not bool
            or type(candidate_tests.get("selected")) is not int
            or type(candidate_tests.get("run")) is not int
            or any(
                type(candidate_tests.get(field)) is not int or candidate_tests[field] < 0
                for field in candidate_count_fields
            )
        ):
            raise ValueError
        fixed_complete = not case_failures
        candidate_complete = (
            candidate_tests["selected"] > 0
            and candidate_tests["run"] == candidate_tests["selected"]
            and all(candidate_tests[field] == 0 for field in candidate_count_fields)
            and candidate_tests.get("process_returncode") == 0
        )
        complete = fixed_complete and candidate_complete
        if payload["fixed_acceptance_successful"] is not fixed_complete:
            raise ValueError
        if candidate_tests["successful"] is not candidate_complete:
            raise ValueError
        if payload["successful"] is not complete or (returncode == 0) is not complete:
            raise ValueError
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise HarnessError("sandbox.output", "isolated L0 checks returned invalid output") from error
    payload["process_returncode"] = returncode
    return payload


def check_l0(repository: Path, trusted_commit: str, candidate_commit: str) -> dict[str, object]:
    started = time.monotonic()
    overall_deadline = started + TOTAL_WALL_SECONDS
    work_deadline = overall_deadline - CLEANUP_SECONDS
    repository = repository.resolve(strict=True)
    if not repository.is_dir():
        raise HarnessError("input.repository", "repository must be a local directory")
    installed, helper = _load_helper(repository)
    try:
        candidate_report = helper.check_candidate(repository, trusted_commit, candidate_commit)
        if not candidate_report.get("ok"):
            raise HarnessError("candidate.rejected", "pinned candidate validation rejected the revision")

        tree = helper._tree(repository, candidate_commit, work_deadline)
        with tempfile.TemporaryDirectory(prefix="bagaev-l0-") as directory:
            export = Path(directory) / "candidate"
            helper._export(repository, tree, export, work_deadline)
            test_result = _sandbox(helper, export, work_deadline)
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
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "limits": {
            "candidate_files": helper.MAX_FILES,
            "candidate_file_bytes": helper.MAX_FILE_BYTES,
            "candidate_total_bytes": helper.MAX_TOTAL_BYTES,
            "candidate_validation_wall_seconds": CANDIDATE_VALIDATION_WALL_SECONDS,
            "execution_command_wall_seconds": EXECUTION_COMMAND_SECONDS,
            "execution_unit_runtime_seconds": EXECUTION_UNIT_SECONDS,
            "cleanup_reserved_seconds": CLEANUP_SECONDS,
            "overall_wall_seconds": TOTAL_WALL_SECONDS,
            "aggregate_tasks_max": MAX_PROCESSES,
            "aggregate_cpu_quota_percent": CPU_QUOTA_PERCENT,
            "aggregate_memory_max_bytes": MEMORY_MAX_BYTES,
            "aggregate_memory_swap_max_bytes": MEMORY_SWAP_MAX_BYTES,
            "per_process_address_space_bytes": MEMORY_MAX_BYTES,
            "per_file_bytes": MAX_OUTPUT,
            "per_process_open_files": 64,
            "harness_output_bytes": MAX_OUTPUT,
        },
        "sandbox": {
            "candidate_read_only": True,
            "temporary_writes_only": True,
            "temporary_files_inside_aggregate_resource_unit": True,
            "network_namespace_unshared": True,
            "environment_cleared": True,
            "transient_user_service": True,
            "transient_unit_collect_requested": True,
            "aggregate_limits_preflight_before_candidate": True,
            "candidate_start_deadline_preflight": True,
            "whole_unit_sigkill_on_stop": True,
            "fixed_acceptance_runner_separate_from_candidate_process": True,
            "unsandboxed_fallback": False,
        },
        "evidence_notice": (
            "The fixed runner checks the named synthetic acceptance cases outside the candidate "
            "interpreter. Candidate unit-test output remains supplemental untrusted data. Neither "
            "result authorizes a merge or proves language, model, or cost advantage."
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
