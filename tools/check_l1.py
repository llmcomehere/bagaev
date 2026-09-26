#!/usr/bin/env python3
"""Fixed L1 acceptance runner; Linux x86-64, CPython 3.14.x, cgroup v2.

Execution requires independent admission and a separate execution assignment.
Never run this candidate copy directly. Install the reviewed bytes outside the
repository and independently verify its digest BEFORE starting trusted Python.
The host interpreter, its standard library, the kernel, systemd user manager,
and pinned system tools are trusted infrastructure. Self-hashing below is an
additional binding check, not bootstrap authority. No candidate module is ever
imported by this host process. Generator, oracle, supplemental tests and emitted
source execute only through BOOTSTRAP in separate read-only guests.

CLI (only after admission): /usr/bin/python3 -I -B -S INSTALLED_CHECKER
    WORKSPACE_SNAPSHOT --admission EXTERNAL_JSON --admission-sha256 HEX
The snapshot can be a dirty workspace; no Git revision or Git command is used.
The externally reviewed JSON has exactly these keys:
  schema: "bagaev/l1-admission/v1"
  checker_sha256: digest of this installed file
  generator_revision: "bagaev/l1-cpython/v1"
  files: {repository-relative path: sha256} for exactly SNAPSHOT_FILES
  runtime: {absolute guest path: {source: absolute host file, sha256: hex}}
  tools: {absolute host executable path: sha256} for exactly TOOLS
The manifest and installed checker must be outside the snapshot. The caller
pins the manifest's digest independently; candidate-provided hashes/claims are
not admission. Review of the pinned generator INCLUDING its fixed template
must establish absence of clocks, randomness and other forbidden calls. JSON
matches and OS isolation cannot establish that property.

Runtime is a minimal, independently reviewed dependency closure: CPython at
/usr/bin/python3, /usr/lib/python3.14 (needed pure modules and lib-dynload),
the ELF loader and dependent shared libraries, and libseccomp copied to
/trusted/libseccomp.so.2. List actual dependency files separately, including
symlink targets (copies become regular files). A missing dependency BLOCKS;
there is no host filesystem fallback or package installation. Do not include
credentials, configuration, /proc, /dev, /sys or unrelated data. The executable
and stdlib must be from the same independently verified 3.14.x installation.
Host tools and host interpreter dependencies require pre-start admission too.

The runner copies and hashes only these inputs into a private temporary root
outside the repository, with read-only files. Bubblewrap mounts that root and
each job read-only, unshares all namespaces/network, drops capabilities and
disables nested user namespaces. /tmp is an empty read-only directory; no
procfs/devfs/writable mount exists. Only stdout/stderr pipes are writable.
Post-start libseccomp denies fork/vfork/clone/clone3/execve/execveat, rejects
non-native ABIs (including x32), and denies namespace/mount/ptrace/io_uring
escapes. The native x86-64 ABI, libseccomp architecture and no_new_privs are
checked explicitly. Trusted probes use the identical bootstrap before any
candidate operation. This is not a general Python security proof.

Every guest is the sole active owned transient systemd unit: aggregate
memory/swap/pids/CPU quota are read back in that unit before exec of bwrap;
RuntimeMaxSec and host deadlines bound lifetime. Capture is incrementally
bounded. Finally blocks stop and inspect that exact unit; uncertain cleanup
returns BLOCKED and reports the owned unit handle. No unrelated unit is touched.
All candidate output is data, never commands. No path-bearing candidate text is
reported. One JSON report goes to stdout; exit 0 requires all fixed 41 cases,
no failures/skips, and complete checker and generator tests (separate counts).
The checker-test source is externally pinned like the generator tests; it runs
only in the same probed guest and imports the admitted checker copy mounted at
/trusted/check_l1.py. Neither test suite is imported by the host coordinator.

Normative mechanisms: kernel.org/doc/html/latest/userspace-api/seccomp_filter.html;
github.com/containers/bubblewrap/blob/main/bwrap.xml; libseccomp API manuals.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time

REVISION = "bagaev/l1-cpython/v1"
SCHEMA = "bagaev/l0-result/v1"
HEX = re.compile(r"[0-9a-f]{64}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
MEMORY = 512 * 1024 * 1024
TASKS = 16
CPU_PERCENT = 50
UNIT_SECONDS = 5
TOTAL_SECONDS = 300
OUTPUT_LIMIT = 2 * 1024 * 1024
FILE_LIMIT = 16 * 1024 * 1024
RUNTIME_LIMIT = 128 * 1024 * 1024
TOOLS = ("/usr/bin/bwrap", "/usr/bin/systemd-run", "/usr/bin/systemctl")
SNAPSHOT_FILES = (
    "src/bagaev_l0.py", "src/bagaev_l1.py", "tests/test_l1.py", "tests/test_check_l1.py",
    "examples/l0/tag_list.json", "examples/l0/tag_unique_sorted.patch",
    "examples/l0/composed.json", "examples/l0/composed_inputs.json",
)
# Frozen L0 oracle and fixtures at dd526aa3e5ad3c165948561f33313e99de432ce4.
# An admission manifest cannot silently substitute a different oracle/fixture.
FROZEN = {
    'src/bagaev_l0.py': 'e74aa0cef4ba84d5f17865194868901b36dce12299c81189b2172fa08c6eb922',
    'examples/l0/tag_list.json': '88b5b49f720cabf602a890a9d58025198dbd59c9de64c3299d4385cbe40f3d30',
    'examples/l0/tag_unique_sorted.patch': 'd39f6aa7232660904c6436291c6f421010db4a70d33eb41c2ba6c7befee6ed51',
    'examples/l0/composed.json': 'cdf4ac7ebb6ba8f29514570fbbd3abc4abad2eaecad312b824f32ca43b32208c',
    'examples/l0/composed_inputs.json': '376169957fd2d6be8e32bbf057cda42711c2d0d5ea3588f837ed051a8ed7b032',
}
L0_IDS = (
    "patch-atomic", "list-preserves", "empty", "duplicates", "reversed", "distinct",
    "composed", "wrong-type", "duplicate-key", "duplicate-node", "missing-reference",
    "cycle", "unknown-operation", "integer-overflow", "stale-patch",
    "invalid-replacement", "large-integer", "deep-malformed", "deep-malformed-patch",
    "eager-unreachable-overflow",
)
CASE_IDS = L0_IDS + tuple(f"L1-{i:02d}" for i in range(1, 22))

# Runs as trusted code INSIDE the resource-controlled unit, before bwrap.
# stdout is a pipe, so the subsequent guest cannot rewind this preflight record.
UNIT_GUARD = r'''
import json, os, sys
from pathlib import Path
try:
    relative = next(x[3:] for x in Path('/proc/self/cgroup').read_text().splitlines()
                    if x.startswith('0::'))
    root = Path('/sys/fs/cgroup').resolve(strict=True)
    group = (root / relative.lstrip('/')).resolve(strict=True)
    if not group.is_relative_to(root): raise ValueError()
    actual = {k: (group / k).read_text().strip() for k in
              ('memory.max', 'memory.swap.max', 'pids.max', 'cpu.max')}
    quota, period = map(int, actual['cpu.max'].split())
    if (actual['memory.max'] != '536870912' or actual['memory.swap.max'] != '0'
        or actual['pids.max'] != '16' or quota <= 0 or period <= 0
        or quota * 100 != 50 * period): raise ValueError()
    print(json.dumps({'guard': actual}, separators=(',', ':')), flush=True)
    os.execv(sys.argv[1], sys.argv[1:])
except BaseException:
    raise SystemExit(125)
'''

# This string is trusted checker code; it is never supplied by the candidate.
# All imports of candidate modules below occur AFTER restriction installation.
BOOTSTRAP = r'''
import base64, ctypes, errno, hashlib, json, os, platform, runpy, sys
from pathlib import Path

def blocked():
    raise SystemExit(125)

if (platform.python_implementation() != 'CPython' or sys.version_info[:2] != (3, 14)
    or platform.machine() != 'x86_64' or ctypes.sizeof(ctypes.c_void_p) != 8
    or sys.executable != '/usr/bin/python3'
    # Bubblewrap sets namespace-owned PWD after clearenv; CPython may coerce locale.
    or any(not ((k == 'PWD' and v == '/job') or
                (k == 'LC_CTYPE' and v in ('C.UTF-8', 'C.utf8', 'UTF-8')))
           for k, v in os.environ.items())):
    blocked()
try:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                          ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(39, 0, 0, 0, 0) != 1:
        blocked()
    sec = ctypes.CDLL('/trusted/libseccomp.so.2', use_errno=True)
    sec.seccomp_arch_native.restype = ctypes.c_uint32
    if sec.seccomp_arch_native() != 0xc000003e: blocked()
    sec.seccomp_init.argtypes = [ctypes.c_uint32]
    sec.seccomp_init.restype = ctypes.c_void_p
    sec.seccomp_attr_set.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32]
    sec.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
                                   ctypes.c_uint]
    sec.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    sec.seccomp_syscall_resolve_name.restype = ctypes.c_int
    sec.seccomp_load.argtypes = [ctypes.c_void_p]
    sec.seccomp_release.argtypes = [ctypes.c_void_p]
    sec.seccomp_arch_exist.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    ctx = sec.seccomp_init(0x7fff0000)  # ALLOW default; process/escape denial below.
    if not ctx: blocked()
    try:
        # ACT_BADARCH=2, KILL_PROCESS. Native context must not admit x86 or x32.
        if sec.seccomp_attr_set(ctx, 2, 0x80000000) != 0: blocked()
        if sec.seccomp_arch_exist(ctx, 0x40000003) == 0: blocked()
        if sec.seccomp_arch_exist(ctx, 0x4000003e) == 0: blocked()
        denied = ('fork', 'vfork', 'clone', 'clone3', 'execve', 'execveat',
                  'unshare', 'setns', 'mount', 'umount2', 'pivot_root', 'chroot',
                  'ptrace', 'process_vm_writev', 'io_uring_setup', 'userfaultfd')
        numbers = {}
        for name in denied:
            number = sec.seccomp_syscall_resolve_name(name.encode('ascii'))
            if number < 0: blocked()
            numbers[name] = number
            if sec.seccomp_rule_add(ctx, 0x50000 | errno.EPERM, number, 0) != 0:
                blocked()
        if sec.seccomp_load(ctx) != 0: blocked()
    finally:
        sec.seccomp_release(ctx)
    if libc.prctl(21, 0, 0, 0, 0) != 2: blocked()  # PR_GET_SECCOMP
except (OSError, AttributeError):
    blocked()
print(json.dumps({'runtime': {'implementation': platform.python_implementation(),
      'version': platform.python_version(), 'executable': sys.executable,
      'architecture': platform.machine(), 'seccomp': 2, 'no_new_privs': 1}},
      separators=(',', ':')), flush=True)
request = json.loads(Path('/job/request.json').read_bytes())
mode = request['mode']
if mode == 'probe':
    paths = ('/probe', '/tmp/probe', '/job/probe', '/candidate/probe', '/usr/probe')
    for path in paths:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as error:
            if error.errno != errno.EROFS: blocked()
        else:
            os.close(fd)
            blocked()
    try:
        child = os.fork()
    except OSError as error:
        if error.errno != errno.EPERM: blocked()
    else:
        if child == 0: os._exit(126)
        os.waitpid(child, 0)
        blocked()
    try:
        os.execve('/usr/bin/python3', ['/usr/bin/python3', '-I', '-B', '-S',
                  '-c', 'raise SystemExit(126)'], {})
    except OSError as error:
        if error.errno != errno.EPERM: blocked()
    # EPERM, not the EFAULT/ENOSYS expected for these deliberately invalid calls.
    libc.syscall.restype = ctypes.c_long
    for name in ('clone3', 'execveat'):
        ctypes.set_errno(0)
        result = libc.syscall(ctypes.c_long(numbers[name]), ctypes.c_long(-1),
                              ctypes.c_long(0), ctypes.c_long(0), ctypes.c_long(0),
                              ctypes.c_long(0), ctypes.c_long(0))
        if result != -1 or ctypes.get_errno() != errno.EPERM: blocked()
    print('{"probe":"denied","writes":5,"fork":true,"exec":true,"raw":true}')
    raise SystemExit(0)
if mode == 'artifact':
    source = Path('/job/artifact.py').read_bytes()
    if hashlib.sha256(source).hexdigest() != request['sha256']: blocked()
    sys.argv = ['/job/artifact.py', '/job/inputs.json']
    runpy.run_path('/job/artifact.py', run_name='__main__')
    raise SystemExit(124)  # A conforming artifact always exits through main.
if mode == 'oracle':
    sys.argv = ['/candidate/src/bagaev_l0.py', request['command'], '/job/program.json']
    if request['command'] != 'check':
        sys.argv.append('/job/patch.json' if request['command'] == 'patch'
                        else '/job/inputs.json')
    runpy.run_path('/candidate/src/bagaev_l0.py', run_name='__main__')
    raise SystemExit(124)
sys.path.insert(0, '/candidate/src')
if mode == 'generate':
    import bagaev_l0 as l0
    import bagaev_l1 as l1
    raw = Path('/job/program.json').read_bytes()
    program = None
    before = None
    try:
        program = l0.loads_json(raw)
        before = json.dumps(program, sort_keys=True, separators=(',', ':'))
        if request.get('patch'):
            program = l0.apply_patch(program, l0.loads_json(Path('/job/patch.json').read_bytes()))
        checked = l0.compile_program(program)
        artifact = l1.generate_source(checked)
        payload = {'ok': True, 'source': base64.b64encode(artifact.source).decode('ascii'),
                   'program_digest': artifact.program_digest,
                   'generator_revision': artifact.generator_revision,
                   'artifact_sha256': artifact.artifact_sha256,
                   'program': checked.document(), 'result_type': checked.result_type,
                   'original_unchanged': Path('/job/program.json').read_bytes() == raw}
        if request.get('patch'):
            payload['base_digest'] = l0.compile_program(l0.loads_json(raw)).digest
    except (l0.L0Error, l1.L1Error) as error:
        unchanged = Path('/job/program.json').read_bytes() == raw
        if program is not None and before is not None:
            unchanged = unchanged and json.dumps(program, sort_keys=True,
                         separators=(',', ':')) == before
        payload = {'ok': False, 'error': {'code': error.code, 'message': str(error)},
                   'emitted': False, 'original_unchanged': unchanged}
    print(json.dumps(payload, ensure_ascii=True, separators=(',', ':')))
    raise SystemExit(0 if payload['ok'] else 2)
if mode in ('tests', 'checker-tests'):
    import io, contextlib, unittest
    class Capture(io.StringIO):
        def write(self, value):
            if self.tell() + len(value) > 65536: raise RuntimeError('capture limit')
            return super().write(value)
    captured = Capture()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        pattern = 'test_check_l1.py' if mode == 'checker-tests' else 'test_l1.py'
        suite = unittest.defaultTestLoader.discover('/candidate/tests', pattern=pattern)
        selected = suite.countTestCases()
        result = unittest.TextTestRunner(stream=captured).run(suite)
    counts = {'selected': selected, 'run': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skipped': len(result.skipped),
              'expected_failures': len(result.expectedFailures),
              'unexpected_successes': len(result.unexpectedSuccesses)}
    print(json.dumps(counts, separators=(',', ':')))
    raise SystemExit(0 if result.wasSuccessful() else 1)
blocked()
'''


class Failure(Exception):
    """Only fixed checker codes cross into the public report."""
    def __init__(self, code, *, blocked=False):
        self.code = code
        self.blocked = blocked
        super().__init__(code)


def require(condition, code, *, blocked=False):
    if not condition:
        raise Failure(code, blocked=blocked)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'output.duplicate_key')
        result[key] = value
    return result


def decode(data):
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Failure('output.constant')))
    except (UnicodeError, ValueError, RecursionError):
        raise Failure('output.json') from None


def same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def keys(value, wanted, code='output.shape'):
    require(type(value) is dict and set(value) == set(wanted), code)


def safe_error(value):
    keys(value, ('code', 'message'))
    require(type(value['code']) is str and re.fullmatch(r'[a-z][a-z0-9_.]{0,79}', value['code']),
            'output.error_code')
    message = value['message']
    require(type(message) is str and 0 < len(message) <= 200
            and all(32 <= ord(c) <= 126 for c in message)
            and not any(c in message for c in ('/', '\\', ':', '~')),
            'output.error_message')


def envelope(code, value, command='run'):
    require(type(value) is dict and value.get('schema') == SCHEMA
            and value.get('command') == command and type(value.get('ok')) is bool,
            'output.envelope')
    if value['ok']:
        extra = {'run': ('program_digest', 'result_type', 'result'),
                 'check': ('program_digest', 'node_count', 'input_names', 'result_type'),
                 'patch': ('base_digest', 'program_digest', 'program')}[command]
        keys(value, ('schema', 'ok', 'command', *extra))
        require(code == 0, 'output.exit')
        require(type(value['program_digest']) is str and DIGEST.fullmatch(value['program_digest']),
                'output.digest')
        if command == 'run':
            validate_value(value['result_type'], value['result'])
    else:
        keys(value, ('schema', 'ok', 'command', 'error'))
        require(code == 2, 'output.exit')
        safe_error(value['error'])
    return value


def validate_value(kind, value):
    if kind == 'int':
        good = type(value) is int and -(2**63) <= value < 2**63
    elif kind == 'bool':
        good = type(value) is bool
    elif kind == 'string':
        good = type(value) is str and len(value.encode('utf-8')) <= 4096
    elif kind == 'string_list':
        good = (type(value) is list and len(value) <= 256 and all(
            type(v) is str and len(v.encode('utf-8')) <= 4096 for v in value))
    else:
        good = False
    require(good, 'output.value_type')


def compare(reference, actual):
    require(reference['ok'] is actual['ok'], 'equivalence.outcome')
    if reference['ok']:
        require(same(reference, actual), 'equivalence.value')
    else:
        require(reference['error']['code'] == actual['error']['code'], 'equivalence.error')


def digest(program):
    canonical = copy.deepcopy(program)
    canonical['nodes'].sort(key=lambda n: n['id'])
    data = json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')
    return 'sha256:' + sha(data)


def bind(source, identity, selected_digest):
    keys(identity, ('program_digest', 'generator_revision', 'artifact_sha256'))
    require(identity['generator_revision'] == REVISION, 'binding.generator')
    require(identity['program_digest'] == selected_digest, 'binding.revision')
    require(identity['artifact_sha256'] == sha(source), 'binding.hash')
    require(source.startswith(('# Generated by ' + REVISION + '; fixed L0 program.\n').encode()),
            'binding.header')
    # Inert extraction of the admitted template's single encoded data assignment.
    # This does not evaluate Python, import modules or accept arbitrary expressions.
    found = re.findall(rb'^_DATA = json.loads\(bytes.fromhex\("([0-9a-f]+)"\).decode\("ascii"\)\)$',
                       source, re.MULTILINE)
    require(len(found) == 1, 'binding.embedded')
    data = decode(bytes.fromhex(found[0].decode('ascii')))
    require(type(data) is list and len(data) >= 2 and data[0] == selected_digest,
            'binding.embedded')


def read_file(path, maximum=FILE_LIMIT):
    # Reject a leaf symlink. Nonblocking open prevents a FIFO peer wait before
    # fstat; type, size and content are checked through this same descriptor.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= maximum, 'input.file', blocked=True)
        data = bytearray()
        while len(data) <= maximum:
            chunk = os.read(descriptor, min(65536, maximum + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        require(len(data) <= maximum, 'input.size', blocked=True)
        return bytes(data)
    finally:
        os.close(descriptor)


def pinned(path, expected, maximum=FILE_LIMIT):
    require(type(expected) is str and HEX.fullmatch(expected), 'admission.hash', blocked=True)
    data = read_file(path, maximum)
    require(sha(data) == expected, 'admission.mismatch', blocked=True)
    return data


def put(path, data, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('xb') as stream:
        stream.write(data)
    path.chmod(0o500 if executable else 0o400)


def system_env():
    runtime = f'/run/user/{os.getuid()}'
    return {'DBUS_SESSION_BUS_ADDRESS': f'unix:path={runtime}/bus',
            'XDG_RUNTIME_DIR': runtime, 'PATH': '/usr/bin:/bin', 'LANG': 'C',
            'LC_ALL': 'C', 'HOME': '/nonexistent'}


def capture(command, deadline, env, limit=OUTPUT_LIMIT):
    require(time.monotonic() < deadline, 'limit.wall', blocked=True)
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, close_fds=True,
                               start_new_session=True)
    streams = [bytearray(), bytearray()]
    try:
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((process.stdout, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map():
                require(time.monotonic() < deadline, 'limit.wall', blocked=True)
                for key, _ in selector.select(min(0.1, max(0, deadline-time.monotonic()))):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        streams[key.data].extend(chunk)
                        require(sum(map(len, streams)) <= limit, 'limit.output')
            code = process.wait(timeout=max(0.01, deadline-time.monotonic()))
        return code, bytes(streams[0]), bytes(streams[1])
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        process.stdout.close()
        process.stderr.close()


class Guest:
    def __init__(self, root, jobs, tools, deadline):
        self.root, self.jobs, self.tools, self.deadline = root, jobs, tools, deadline
        self.runtime = None
        self.handles = []
        self.counter = 0
        self.probed = False

    def tool(self, name):
        path = '/usr/bin/' + name
        pinned(Path(path), self.tools[path])
        return path

    def cleanup(self, unit):
        deadline = time.monotonic() + 4
        capture([self.tool('systemctl'), '--user', 'stop', unit], deadline, system_env(), 16384)
        _code, raw, _stderr = capture([self.tool('systemctl'), '--user', 'show', unit,
            '--property=LoadState,ActiveState,MainPID'], deadline, system_env(), 16384)
        fields = dict(line.split('=', 1) for line in raw.decode('ascii').splitlines() if '=' in line)
        require(fields.get('LoadState') == 'not-found' or (
            fields.get('ActiveState') in ('inactive', 'failed') and fields.get('MainPID') == '0'),
            'cleanup.unconfirmed', blocked=True)
        self.handles.remove(unit)

    def run(self, request, files=None):
        require(self.probed or request['mode'] == 'probe', 'sandbox.unprobed', blocked=True)
        self.counter += 1
        job = self.jobs / str(self.counter)
        job.mkdir(mode=0o700)
        put(job / 'request.json', encoded(request))
        for name, data in (files or {}).items():
            require(name in ('program.json', 'patch.json', 'inputs.json', 'artifact.py'), 'job.path')
            put(job / name, data)
        if 'artifact.py' in (files or {}):
            require(sha(read_file(job / 'artifact.py')) == request['sha256'], 'binding.hash')
        # Every nested mount is explicitly RO; root-only remount would be insufficient.
        sandbox = [self.tool('bwrap'), '--unshare-all', '--unshare-user', '--clearenv', '--die-with-parent',
                   '--new-session', '--disable-userns', '--cap-drop', 'ALL',
                   '--ro-bind', str(self.root), '/', '--ro-bind', str(job), '/job',
                   '--chdir', '/job', '/usr/bin/python3', '-I', '-B', '-S',
                   '/trusted/bootstrap.py']
        unit = f'bagaev-l1-{os.getpid()}-{time.monotonic_ns()}.service'
        command = [self.tool('systemd-run'), '--user', '--quiet', '--wait', '--pipe', '--collect',
            '--service-type=exec', '--unit', unit, '--property=MemoryMax=536870912',
            '--property=MemorySwapMax=0', '--property=TasksMax=16', '--property=CPUQuota=50%',
            '--property=RuntimeMaxSec=5s', '--property=KillMode=control-group',
            '--property=KillSignal=SIGKILL', '--property=FinalKillSignal=SIGKILL',
            '--property=SendSIGKILL=yes', '--property=TimeoutStopSec=1s',
            '--property=LimitCORE=0', '--property=LimitNOFILE=64', '--property=LimitCPU=3',
            '--', '/usr/bin/python3', '-I', '-B', '-S', '-c', UNIT_GUARD, *sandbox]
        self.handles.append(unit)
        try:
            code, stdout, stderr = capture(command, min(self.deadline, time.monotonic()+8), system_env())
        finally:
            self.cleanup(unit)
        require(code != 125, 'sandbox.preflight', blocked=True)
        lines = stdout.splitlines()
        require(len(lines) >= 2, 'sandbox.start', blocked=True)
        require(not stderr, 'output.stderr')
        require(len(lines) == 3 and stdout.endswith(b'\n'), 'output.framing')
        guard, runtime, payload = map(decode, lines)
        keys(guard, ('guard',))
        keys(guard['guard'], ('memory.max', 'memory.swap.max', 'pids.max', 'cpu.max'))
        actual = guard['guard']
        require(actual['memory.max'] == str(MEMORY) and actual['memory.swap.max'] == '0'
                and actual['pids.max'] == str(TASKS), 'sandbox.limits', blocked=True)
        try:
            quota, period = map(int, actual['cpu.max'].split())
        except (ValueError, AttributeError):
            raise Failure('sandbox.limits', blocked=True) from None
        require(quota > 0 and period > 0 and quota*100 == CPU_PERCENT*period,
                'sandbox.limits', blocked=True)
        keys(runtime, ('runtime',))
        identity = runtime['runtime']
        keys(identity, ('implementation', 'version', 'executable', 'architecture', 'seccomp', 'no_new_privs'))
        require(identity['implementation'] == 'CPython' and type(identity['version']) is str
                and re.fullmatch(r'3\.14\.\d+', identity['version'])
                and identity['executable'] == '/usr/bin/python3'
                and identity['architecture'] == 'x86_64'
                and type(identity['seccomp']) is int and identity['seccomp'] == 2
                and type(identity['no_new_privs']) is int and identity['no_new_privs'] == 1,
                'sandbox.runtime', blocked=True)
        if self.runtime is None:
            self.runtime = identity
        require(same(self.runtime, identity), 'sandbox.runtime_changed', blocked=True)
        return code, payload

    def preflight(self):
        try:
            code, result = self.run({'mode': 'probe'})
            require(code == 0 and same(result, {'probe': 'denied', 'writes': 5,
                    'fork': True, 'exec': True, 'raw': True}), 'sandbox.probe', blocked=True)
        except Failure as error:
            # Bad/missing probe evidence is unavailable isolation, never a case failure.
            error.blocked = True
            raise
        self.probed = True


def stage(snapshot, admission, expected, root):
    require(not admission.resolve().is_relative_to(snapshot), 'admission.location', blocked=True)
    manifest = decode(pinned(admission, expected))
    keys(manifest, ('schema', 'checker_sha256', 'generator_revision', 'files', 'runtime', 'tools'),
         'admission.shape')
    require(manifest['schema'] == 'bagaev/l1-admission/v1' and manifest['generator_revision'] == REVISION,
            'admission.version', blocked=True)
    installed = Path(__file__).resolve(strict=True)
    require(not installed.is_relative_to(snapshot), 'admission.checker_location', blocked=True)
    checker_source = pinned(installed, manifest['checker_sha256'])
    keys(manifest['files'], SNAPSHOT_FILES, 'admission.files')
    require(all(manifest['files'][name] == value for name, value in FROZEN.items()),
            'admission.frozen', blocked=True)
    keys(manifest['tools'], TOOLS, 'admission.tools')
    for name, value in manifest['tools'].items():
        pinned(Path(name), value)
    for name, value in manifest['files'].items():
        source = snapshot / name
        require(source.resolve().is_relative_to(snapshot), 'snapshot.path', blocked=True)
        put(root / 'candidate' / name, pinned(source, value))
    runtime = manifest['runtime']
    require(type(runtime) is dict and 0 < len(runtime) <= 4096
            and '/usr/bin/python3' in runtime and '/trusted/libseccomp.so.2' in runtime,
            'admission.runtime', blocked=True)
    total = 0
    for name, entry in runtime.items():
        path = PurePosixPath(name)
        require(str(path) == name and path.is_absolute() and '..' not in path.parts
                and (name.startswith(('/usr/', '/lib/', '/lib64/'))
                     or name == '/trusted/libseccomp.so.2'), 'admission.runtime_path', blocked=True)
        keys(entry, ('source', 'sha256'), 'admission.runtime_entry')
        require(type(entry['source']) is str and Path(entry['source']).is_absolute(),
                'admission.runtime_source', blocked=True)
        source = Path(entry['source']).resolve(strict=True)
        require(not source.is_relative_to(snapshot), 'admission.runtime_source', blocked=True)
        data = pinned(source, entry['sha256'])
        total += len(data)
        require(total <= RUNTIME_LIMIT, 'admission.runtime_size', blocked=True)
        put(root / name.lstrip('/'), data, executable=True)
    for name in ('tmp', 'job'):
        (root / name).mkdir(mode=0o500)
    put(root / 'trusted/bootstrap.py', BOOTSTRAP.encode('utf-8'))
    put(root / 'trusted/check_l1.py', checker_source)
    return manifest


def program(nodes, result):
    return {'schema': 'bagaev/l0-program/v1', 'nodes': nodes, 'result': {'ref': result}}


def input_program(kind):
    return program([{'id': 'x', 'op': 'input', 'name': 'x', 'type': kind}], 'x')


def literal_zero():
    return program([{'id': 'zero', 'op': 'literal', 'type': 'int', 'value': 0}], 'zero')


def reverse_keys(value):
    if type(value) is dict:
        return {key: reverse_keys(value[key]) for key in reversed(value)}
    if type(value) is list:
        return [reverse_keys(v) for v in value]
    return value


class Acceptance:
    def __init__(self, guest, fixtures):
        self.guest = guest
        self.fixtures = fixtures
        self.records = []
        self.failures = []
        self.cache = {}
        self.current = None
        self.tag = decode(fixtures['tag_list.json'])
        self.patch = decode(fixtures['tag_unique_sorted.patch'])
        self.composed = decode(fixtures['composed.json'])
        self.patched = copy.deepcopy(self.tag)
        # Exact fixed patch recipe, compared with the oracle's complete result.
        replacements = {node['id']: node for node in self.patch['replace']}
        self.patched['nodes'] = [copy.deepcopy(replacements.get(n['id'], n)) for n in self.tag['nodes']]
        self.patched['nodes'].extend(copy.deepcopy(self.patch['add']))
        self.patched['nodes'].sort(key=lambda n: n['id'])

    def record(self, name, action):
        require(name == CASE_IDS[len(self.records)], 'cases.order')
        self.current = {'case': name, 'status': 'FAILED', 'observations': []}
        self.records.append(self.current)
        try:
            action()
            self.current['status'] = 'MATCH'
        except Failure as error:
            if error.blocked:
                raise
            self.failures.append({'case': name, 'code': error.code})
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            self.failures.append({'case': name, 'code': 'case.malformed'})

    def oracle(self, raw, inputs=None, patch=None, command='run'):
        files = {'program.json': raw}
        if inputs is not None:
            files['inputs.json'] = inputs
        if patch is not None:
            files['patch.json'] = patch
        code, result = self.guest.run({'mode': 'oracle', 'command': command}, files)
        return envelope(code, result, command)

    def generate(self, raw, patch=None, expected_error=None, force=False):
        cache_key = (raw, patch)
        if not force and cache_key in self.cache:
            return self.cache[cache_key]
        files = {'program.json': raw}
        if patch is not None:
            files['patch.json'] = patch
        code, result = self.guest.run({'mode': 'generate', 'patch': patch is not None}, files)
        if expected_error:
            keys(result, ('ok', 'error', 'emitted', 'original_unchanged'))
            require(code == 2 and result['ok'] is False and result['emitted'] is False
                    and result['original_unchanged'] is True, 'generation.refusal')
            safe_error(result['error'])
            require(result['error']['code'] == expected_error, 'generation.error')
            return result
        fields = ('ok', 'source', 'program_digest', 'generator_revision', 'artifact_sha256',
                  'program', 'result_type', 'original_unchanged')
        keys(result, (*fields, 'base_digest') if patch is not None else fields)
        require(code == 0 and result['ok'] is True and result['original_unchanged'] is True,
                'generation.outcome')
        try:
            source = base64.b64decode(result['source'], validate=True)
        except (ValueError, TypeError):
            raise Failure('generation.encoding') from None
        require(0 < len(source) <= 1024*1024, 'generation.size')
        selected = self.patched if patch is not None else decode(raw)
        canonical = copy.deepcopy(selected)
        canonical['nodes'].sort(key=lambda n: n['id'])
        require(same(result['program'], canonical), 'generation.program')
        identity = {name: result[name] for name in
                    ('program_digest', 'generator_revision', 'artifact_sha256')}
        bind(source, identity, digest(selected))
        if patch is not None:
            require(result['base_digest'] == digest(decode(raw)), 'patch.base')
        artifact = (source, identity, result['result_type'])
        if expected_error is None:
            self.cache[cache_key] = artifact
        return artifact

    def run(self, selected, inputs, expected=None, error=None):
        raw = encoded(selected)
        # Oracle observation precedes generation and artifact execution.
        reference = self.oracle(raw, inputs)
        if error:
            require(reference['ok'] is False and reference['error']['code'] == error, 'oracle.expected_error')
        else:
            require(reference['ok'] is True and same(reference['result'], expected), 'oracle.expected_value')
            require(reference['program_digest'] == digest(selected), 'oracle.digest')
        source, identity, result_type = self.generate(raw)
        if reference['ok']:
            require(reference['result_type'] == result_type, 'generation.type')
        bind(source, identity, digest(selected))  # Immediately before staging the executed copy.
        code, result = self.guest.run({'mode': 'artifact', 'sha256': identity['artifact_sha256']},
                                     {'artifact.py': source, 'inputs.json': inputs})
        actual = envelope(code, result)
        compare(reference, actual)
        self.current['observations'].append({'phase': 'runtime', 'binding': identity,
            'exit': code, 'reference': reference, 'artifact': actual})

    def gate(self, raw, code, patch=None):
        command = 'patch' if patch is not None else 'check'
        reference = self.oracle(raw, patch=patch, command=command)
        require(reference['ok'] is False and reference['error']['code'] == code, 'oracle.gate')
        refusal = self.generate(raw, patch, expected_error=code, force=True)
        self.current['observations'].append({'phase': 'generation-refusal', 'command': command,
            'code': code, 'exit': 2, 'emitted': refusal['emitted'],
            'original_unchanged': refusal['original_unchanged'],
            'base_digest': digest(self.tag) if patch is not None else None})

    def patch_atomic(self):
        raw, change = self.fixtures['tag_list.json'], self.fixtures['tag_unique_sorted.patch']
        reference = self.oracle(raw, patch=change, command='patch')
        require(reference['ok'] is True and reference['base_digest'] == digest(self.tag)
                and reference['program_digest'] == digest(self.patched)
                and reference['base_digest'] != reference['program_digest']
                and same(reference['program'], self.patched), 'patch.result')
        _source, identity, _kind = self.generate(raw, change, force=True)
        self.current['observations'].append({'phase': 'patch', 'base_digest': digest(self.tag),
            'program_digest': digest(self.patched), 'binding': identity,
            'original_bytes_sha256': sha(raw), 'original_unchanged': True})

    def equality(self, reordered=False):
        raw = self.fixtures['composed.json']
        other = raw
        if reordered:
            alternate = copy.deepcopy(self.composed)
            alternate['nodes'].reverse()
            other = encoded(reverse_keys(alternate))
        first = self.generate(raw, force=True)
        second = self.generate(other, force=True)
        require(first[0] == second[0] and same(first[1], second[1])
                and same(first[2], second[2]), 'generation.determinism')
        self.current['observations'].append({'phase': 'determinism', 'binding': first[1],
                                            'identical_bytes': True, 'reordered': reordered})

    def tamper(self, revision=False):
        selected = self.tag if revision else self.composed
        source, identity, _kind = self.generate(encoded(selected))
        changed = source if revision else source+b'\n'
        expected = digest(self.patched) if revision else digest(selected)
        wanted = 'binding.revision' if revision else 'binding.hash'
        try:
            bind(changed, identity, expected)
        except Failure as error:
            require(error.code == wanted, 'binding.wrong_refusal')
        else:
            raise Failure('binding.accepted_tamper')
        self.current['observations'].append({'phase': 'binding-refusal', 'code': wanted,
            'binding': identity, 'selected_digest': expected, 'artifact_executed': False})

    def all(self):
        self.record('patch-atomic', self.patch_atomic)
        observations = (
            ('list-preserves', ['red', 'blue', 'red'], ['red', 'blue', 'red'], ['blue', 'red']),
            ('empty', [], [], []),
            ('duplicates', ['blue', 'blue'], ['blue', 'blue'], ['blue']),
            ('reversed', ['red', 'blue'], ['red', 'blue'], ['blue', 'red']),
            ('distinct', ['blue', 'green', 'red'], ['blue', 'green', 'red'], ['blue', 'green', 'red']),
        )
        for name, tags, before, after in observations:
            def observation(tags=tags, before=before, after=after):
                require(same(after, sorted(set(tags))), 'fixture.comparison')
                inputs = encoded({'tags': tags})
                self.run(self.tag, inputs, before)
                self.run(self.patched, inputs, after)
            self.record(name, observation)
        self.record('composed', lambda: self.run(self.composed, self.fixtures['composed_inputs.json'], 4))
        duplicate = copy.deepcopy(self.tag)
        duplicate['nodes'].append(copy.deepcopy(duplicate['nodes'][0]))
        missing = copy.deepcopy(self.tag)
        missing['nodes'][1]['value']['ref'] = 'absent'
        cycle = program([{'id': 'a', 'op': 'identity', 'value': {'ref': 'b'}},
                         {'id': 'b', 'op': 'identity', 'value': {'ref': 'a'}}], 'a')
        unknown = copy.deepcopy(self.tag)
        unknown['nodes'][1]['op'] = 'python.eval'
        overflow = program([
            {'id': 'max', 'op': 'literal', 'type': 'int', 'value': 9223372036854775807},
            {'id': 'one', 'op': 'literal', 'type': 'int', 'value': 1},
            {'id': 'sum', 'op': 'int.add', 'left': {'ref': 'max'}, 'right': {'ref': 'one'}},
        ], 'sum')
        stale = copy.deepcopy(self.patch)
        stale['base'] = 'sha256:'+'0'*64
        invalid = copy.deepcopy(self.patch)
        invalid['replace'][0]['value']['ref'] = 'absent'
        nested = '['*600+'0'+']'*600
        deep_program = ('{"schema":"bagaev/l0-program/v1","nodes":['
            '{"id":"value","op":"literal","type":"int","value":'+nested+
            '}],"result":{"ref":"value"}}').encode()
        deep_patch = ('{"schema":"bagaev/l0-patch/v1","base":"sha256:'
            '7c42c5cb58af9c896353c5043e78f05fb884b19df9a59590f7d773decd9d78c0",'
            '"add":[],"replace":[{"id":"result","op":"literal","type":"int","value":'+
            nested+'}]}').encode()
        eager = program([
            {'id': 'result', 'op': 'literal', 'type': 'int', 'value': 0},
            {'id': 'max', 'op': 'literal', 'type': 'int', 'value': 9223372036854775807},
            {'id': 'one', 'op': 'literal', 'type': 'int', 'value': 1},
            {'id': 'unused_overflow', 'op': 'int.add', 'left': {'ref': 'max'}, 'right': {'ref': 'one'}},
        ], 'result')
        self.record('wrong-type', lambda: self.run(self.tag, b'{"tags":3}', error='value.type'))
        self.record('duplicate-key', lambda: self.run(self.tag, b'{"tags":[],"tags":[]}', error='json.duplicate_key'))
        self.record('duplicate-node', lambda: self.gate(encoded(duplicate), 'node.duplicate'))
        self.record('missing-reference', lambda: self.gate(encoded(missing), 'reference.missing'))
        self.record('cycle', lambda: self.gate(encoded(cycle), 'graph.cycle'))
        self.record('unknown-operation', lambda: self.gate(encoded(unknown), 'operation.unknown'))
        self.record('integer-overflow', lambda: self.run(overflow, b'{}', error='integer.overflow'))
        self.record('stale-patch', lambda: self.gate(self.fixtures['tag_list.json'], 'patch.stale', encoded(stale)))
        self.record('invalid-replacement', lambda: self.gate(self.fixtures['tag_list.json'], 'reference.missing', encoded(invalid)))
        self.record('large-integer', lambda: self.run(self.tag, b'{"tags":'+b'9'*5000+b'}', error='integer.overflow'))
        self.record('deep-malformed', lambda: self.gate(deep_program, 'value.type'))
        self.record('deep-malformed-patch', lambda: self.gate(self.fixtures['tag_list.json'], 'value.type', deep_patch))
        self.record('eager-unreachable-overflow', lambda: self.run(eager, b'{}', error='integer.overflow'))
        boolean = program([
            {'id': 'x', 'op': 'input', 'name': 'x', 'type': 'int'},
            {'id': 'one', 'op': 'literal', 'type': 'int', 'value': 1},
            {'id': 'equal', 'op': 'int.equal', 'left': {'ref': 'x'}, 'right': {'ref': 'one'}},
            {'id': 'result', 'op': 'bool.not', 'value': {'ref': 'equal'}},
        ], 'result')
        concat = program([{'id': 'empty', 'op': 'literal', 'type': 'string_list', 'value': []},
                          {'id': 'result', 'op': 'list.concat', 'items': [{'ref': 'empty'}]*32}], 'result')
        chain = [{'id': 'n000', 'op': 'input', 'name': 'x', 'type': 'int'}]
        chain.extend({'id': f'n{i:03d}', 'op': 'identity', 'value': {'ref': f'n{i-1:03d}'}}
                     for i in range(1, 256))
        self.record('L1-01', lambda: self.run(boolean, b'{"x":1}', False))
        self.record('L1-02', lambda: self.run(boolean, b'{"x":2}', True))
        self.record('L1-03', lambda: self.run(input_program('int'), b'{"x":-9223372036854775808}', -(2**63)))
        self.record('L1-04', lambda: self.run(input_program('int'), b'{"x":9223372036854775807}', 2**63-1))
        self.record('L1-05', lambda: self.run(input_program('string'), encoded({'x': 'a'*4096}), 'a'*4096))
        self.record('L1-06', lambda: self.run(input_program('string_list'), encoded({'x': ['a']*256}), ['a']*256))
        self.record('L1-07', lambda: self.run(concat, b'{}', []))
        self.record('L1-08', lambda: self.run(program(chain, 'n255'), b'{"x":0}', 0))
        self.record('L1-09', lambda: self.run(literal_zero(), b'{}'+b' '*1048574, 0))
        self.record('L1-10', lambda: self.run(input_program('string'), encoded({'x': 'a'*4097}), error='limit.string'))
        self.record('L1-11', lambda: self.run(input_program('string_list'), encoded({'x': ['a']*257}), error='limit.list'))
        self.record('L1-12', lambda: self.run(self.tag, b'{}', error='input.missing'))
        self.record('L1-13', lambda: self.run(self.tag, b'{"tags":[],"extra":0}', error='input.unexpected'))
        self.record('L1-14', self.equality)
        self.record('L1-15', self.tamper)
        self.record('L1-16', lambda: self.tamper(revision=True))
        self.record('L1-17', lambda: self.run(input_program('int'), b'{"x":true}', error='value.type'))
        self.record('L1-18', lambda: self.run(input_program('string'), b'{"x":"'+('é'*2049).encode('utf-8')+b'"}', error='limit.string'))
        self.record('L1-19', lambda: self.run(literal_zero(), b'{}'+b' '*1048575, error='limit.json_bytes'))
        self.record('L1-20', lambda: self.equality(reordered=True))
        joined = program([{'id': n, 'op': 'input', 'name': n, 'type': 'string_list'} for n in ('a', 'b')]
            + [{'id': 'joined', 'op': 'list.concat', 'items': [{'ref': 'a'}, {'ref': 'b'}]}], 'joined')
        self.record('L1-21', lambda: self.run(joined, encoded({'a': ['a']*256, 'b': ['a']*256}), error='limit.list'))


def test_counts(code, result):
    fields = ('selected', 'run', 'failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')
    keys(result, fields, 'tests.shape')
    require(all(type(result[n]) is int and result[n] >= 0 for n in fields), 'tests.counts')
    return {'authoritative': False, 'terminal_exit': code, **result}


def supplemental(code, result):
    counts = test_counts(code, result)
    unwanted = ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')
    require(code == 0 and result['selected'] > 0 and result['run'] == result['selected']
            and all(result[n] == 0 for n in unwanted), 'tests.incomplete')
    return counts


def complete(report):
    """Final gate is also checked independently of record construction."""
    require(type(report.get('cases_selected')) is int and report['cases_selected'] == 41,
            'cases.selected')
    require(type(report.get('cases_run')) is int and report['cases_run'] == 41, 'cases.run')
    require(report.get('failures') == [] and report.get('skips') == [], 'cases.failures')
    records = report.get('cases')
    require(type(records) is list and len(records) == 41, 'cases.records')
    for expected, record in zip(CASE_IDS, records):
        keys(record, ('case', 'status', 'observations'), 'cases.record')
        require(record['case'] == expected and record['status'] == 'MATCH'
                and type(record['observations']) is list and len(record['observations']) > 0,
                'cases.match')


def check(snapshot, admission, expected):
    started = time.monotonic()
    report = {'schema': 'bagaev/l1-check/v1', 'ok': False, 'status': 'BLOCKED',
        'admission_sha256': expected if type(expected) is str and HEX.fullmatch(expected) else None,
        'cases_selected': 41, 'cases_run': 0, 'cases': [], 'failures': [], 'skips': [],
        'terminal_exit': 1, 'runtime': None, 'bindings': None, 'owned_handles': [],
        'checker_tests': {'status': 'NOT_RUN', 'authoritative': False},
        'supplemental_generator_tests': {'status': 'NOT_RUN', 'authoritative': False},
        'static_template_admission_required': True, 'merge_authorized': False,
        'limits': {'memory_bytes': MEMORY, 'swap_bytes': 0, 'tasks': TASKS,
            'cpu_quota_percent': CPU_PERCENT, 'unit_wall_seconds': UNIT_SECONDS,
            'total_wall_seconds': TOTAL_SECONDS, 'output_bytes_per_guest': OUTPUT_LIMIT,
            'concurrent_guests': 1, 'guest_filesystem': 'read-only', 'network': 'unshared',
            'post_start_process_creation': 'seccomp-denied'}}
    guest = None
    acceptance = None
    try:
        snapshot = snapshot.resolve(strict=True)
        require(snapshot.is_dir(), 'input.snapshot', blocked=True)
        with tempfile.TemporaryDirectory(prefix='bagaev-l1-') as temporary:
            scratch = Path(temporary).resolve()
            require(not scratch.is_relative_to(snapshot), 'scratch.location', blocked=True)
            root, jobs = scratch / 'root', scratch / 'jobs'
            root.mkdir(mode=0o700)
            jobs.mkdir(mode=0o700)
            manifest = stage(snapshot, admission, expected, root)
            report['bindings'] = {'checker_sha256': manifest['checker_sha256'],
                'generator_revision': manifest['generator_revision'], 'snapshot': manifest['files'],
                'runtime_manifest_sha256': sha(encoded(manifest['runtime'])), 'tools': manifest['tools']}
            guest = Guest(root, jobs, manifest['tools'], started+TOTAL_SECONDS)
            guest.preflight()
            report['checker_tests'] = {'status': 'NO_VALID_RESULT', 'authoritative': False}
            code, checker_tests = guest.run({'mode': 'checker-tests'})
            report['checker_tests'] = test_counts(code, checker_tests)
            supplemental(code, checker_tests)
            fixtures = {Path(name).name: read_file(root / 'candidate' / name)
                        for name in SNAPSHOT_FILES if name.startswith('examples/')}
            acceptance = Acceptance(guest, fixtures)
            report['cases'] = acceptance.records
            report['failures'] = acceptance.failures
            acceptance.all()
            report['cases_run'] = len(acceptance.records)
            report['supplemental_generator_tests'] = {'status': 'NO_VALID_RESULT', 'authoritative': False}
            code, tests = guest.run({'mode': 'tests'})
            report['supplemental_generator_tests'] = test_counts(code, tests)
            supplemental(code, tests)
            # Confirm snapshot bytes after all runs, including frozen example inputs.
            for name, value in manifest['files'].items():
                pinned(root / 'candidate' / name, value)
            complete(report)
        # Scratch cleanup is mandatory and may fail on context exit.
        report.update(ok=True, status='PASS', terminal_exit=0)
    except Failure as error:
        report['status'] = 'BLOCKED' if error.blocked else 'FAIL'
        report['error'] = {'code': error.code}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, subprocess.SubprocessError):
        report['status'] = 'BLOCKED'
        report['error'] = {'code': 'environment.operation'}
    finally:
        if acceptance is not None:
            report['cases_run'] = len(acceptance.records)
        if guest is not None:
            report['runtime'] = guest.runtime
            report['owned_handles'] = list(guest.handles)
    return report


def main():
    parser = argparse.ArgumentParser(description='Check an independently admitted exact L1 workspace snapshot.')
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--admission-sha256', required=True)
    args = parser.parse_args()
    report = check(args.snapshot, args.admission, args.admission_sha256)
    print(json.dumps(report, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':')))
    return report['terminal_exit']


if __name__ == '__main__':
    raise SystemExit(main())
