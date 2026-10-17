"""Inspect exact compiled Python text as data, never execute or authenticate it."""
import sys
import os
if (not __debug__ or not sys.dont_write_bytecode or not sys.flags.no_site or sys.flags.optimize
        or os.environ.get('PYTHONPATH') or os.environ.get('PYTHONHOME')):
    try: os.write(2, b'PREVIEW_PROFILE\n')
    except OSError: pass
    raise SystemExit(1)
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
SELF = Path(__file__).absolute()
LIMIT = 1048576
LIMITS = {'source.bagaev': LIMIT, 'program.json': LIMIT, 'checker.stdout': LIMIT,
          'checker.stderr': 4096, 'artifact.json': 4 * LIMIT, 'receipt.json': 65536}
DIGESTS = {'source_sha256', 'program_sha256', 'checker_sha256', 'artifact_sha256',
           'python_sha256', 'generator_sha256', 'runtime_sha256'}
RECEIPT_FIELDS = DIGESTS | {'schema', 'status', 'form', 'checker_invoked', 'generated_code_executed', 'execution_admission'}
ARTIFACT_FIELDS = {'schema', 'profile', 'program_sha256', 'generator_sha256', 'runtime_sha256', 'python'}
class PreviewError(ValueError):
    def __init__(self, code, uncertain=False):
        self.code = code; self.uncertain = uncertain; super().__init__(code)
def need(ok, code):
    if not ok: raise PreviewError(code)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canon(v): return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
def pin(v): return type(v) is str and re.fullmatch('[0-9a-f]{64}', v) is not None
def path(value):
    try:
        p = Path(value)
        need(p.is_absolute() and '..' not in p.parts and len(p.parents) <= 64, 'PREVIEW_PATH')
        for parent in p.parents: need(stat.S_ISDIR(parent.lstat().st_mode), 'PREVIEW_PATH')
        return p
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, PreviewError): raise
        raise PreviewError('PREVIEW_PATH') from None
def read(p, limit):
    path(p)
    try:
        info = p.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'PREVIEW_PATH')
        need(info.st_size <= limit, 'PREVIEW_BOUNDS')
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as f:
            current = os.fstat(f.fileno())
            need(stat.S_ISREG(current.st_mode) and current.st_nlink == 1
                 and (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino), 'PREVIEW_PATH')
            need(current.st_size <= limit, 'PREVIEW_BOUNDS'); raw = f.read(limit + 1)
        need(len(raw) <= limit, 'PREVIEW_BOUNDS'); return raw
    except OSError: raise PreviewError('PREVIEW_PATH') from None
def inventory(base, names):
    path(base)
    try:
        need(stat.S_ISDIR(base.lstat().st_mode), 'PREVIEW_PATH')
        found = {}
        with os.scandir(base) as entries:
            for item in entries:
                need(len(found) < len(names), 'PREVIEW_INVENTORY')
                found[item.name] = stat.S_IFMT(item.stat(follow_symlinks=False).st_mode)
        need(found == {n: stat.S_IFREG for n in names}, 'PREVIEW_INVENTORY')
    except OSError: raise PreviewError('PREVIEW_PATH') from None
def metadata(raw, canonical=True):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('duplicate')
            result[key] = value
        return result
    def noninteger(_): raise ValueError('noninteger')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_float=noninteger, parse_constant=noninteger)
        need(type(value) is dict, 'PREVIEW_JSON')
        pending = [(value, 0)]; nodes = 0
        while pending:
            current, depth = pending.pop(); nodes += 1
            need(nodes <= 32768 and depth <= 64, 'PREVIEW_BOUNDS')
            if type(current) is str: current.encode('utf-8')
            elif type(current) is dict:
                need(nodes + len(pending) + 2 * len(current) <= 32768, 'PREVIEW_BOUNDS')
                pending.extend((item, depth + 1) for pair in current.items() for item in pair)
            elif type(current) is list:
                need(nodes + len(pending) + len(current) <= 32768, 'PREVIEW_BOUNDS')
                pending.extend((item, depth + 1) for item in current)
            else: need(current is None or type(current) in (bool, int), 'PREVIEW_JSON')
        if canonical: need(canon(value) == raw, 'PREVIEW_JSON')
        return value
    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
        if isinstance(exc, PreviewError): raise
        raise PreviewError('PREVIEW_JSON') from None
def write_all(fd, raw):
    while raw:
        n = os.write(fd, raw)
        if n <= 0: raise OSError('short write')
        raw = raw[n:]
def emit(value, fd=1):
    raw = canon(value) + b'\n'; need(len(raw) <= 16384, 'PREVIEW_BOUNDS'); write_all(fd, raw)
def save(p, raw):
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try: write_all(fd, raw)
    finally: os.close(fd)
class Parser(argparse.ArgumentParser):
    def error(self, message): raise PreviewError('PREVIEW_USAGE')
    def _print_message(self, message, file=None):
        if message:
            raw = message.encode(); need(len(raw) <= 16384, 'PREVIEW_BOUNDS')
            write_all(2 if file is sys.stderr else 1, raw)
HELP = '''Extract exact Python text from a caller-pinned form5 compilation packet.
Usage: record_cpython_preview.py --compiled DIRECTORY --receipt-sha256 SHA256 --source-sha256 SHA256 --program-sha256 SHA256 --output NEW_DIRECTORY
Writes python.txt, report.json and MANIFEST.json as review data only.
No compilation, checker invocation, Python execution or execution authority.
Consistency does not authenticate compiler provenance or semantic equivalence.
'''
def arguments(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv in (['--help'], ['-h']):
        write_all(1, HELP.encode('utf-8')); return None
    parser = Parser(add_help=False, allow_abbrev=False)
    for name in ('compiled', 'receipt-sha256', 'source-sha256', 'program-sha256', 'output'):
        parser.add_argument('--' + name, required=True)
    return parser.parse_args(argv)
def preview(a):
    for value in (a.receipt_sha256, a.source_sha256, a.program_sha256): need(pin(value), 'PREVIEW_PIN')
    path(SELF); own = read(SELF, LIMIT)
    base = path(a.compiled); inventory(base, LIMITS)
    data = {n: read(base / n, limit) for n, limit in LIMITS.items()}
    need(sum(map(len, data.values())) <= 8 * LIMIT, 'PREVIEW_BOUNDS')
    need(sha(data['receipt.json']) == a.receipt_sha256 and sha(data['source.bagaev']) == a.source_sha256
         and sha(data['program.json']) == a.program_sha256, 'PREVIEW_PIN')
    try: data['source.bagaev'].decode('utf-8')
    except UnicodeError: raise PreviewError('PREVIEW_JSON') from None
    program = metadata(data['program.json'])
    need(program.get('schema') == 'bagaev-typed-record/11', 'PREVIEW_JSON')
    receipt = metadata(data['receipt.json'])
    need(set(receipt) == RECEIPT_FIELDS and all(pin(receipt[n]) for n in DIGESTS), 'PREVIEW_RECEIPT')
    need(receipt['schema'] == 'bagaev-record-cpython-compile/1' and receipt['status'] == 'compiled'
         and receipt['form'] == 'record-form/5' and receipt['checker_invoked'] is True
         and receipt['generated_code_executed'] is False and receipt['execution_admission'] is False, 'PREVIEW_RECEIPT')
    need(receipt['source_sha256'] == a.source_sha256 and receipt['program_sha256'] == a.program_sha256
         and receipt['artifact_sha256'] == sha(data['artifact.json']), 'PREVIEW_RECEIPT')
    checker = metadata(data['checker.stdout'], canonical=False)
    need(checker == {'schema': 'bagaev-record-source-check/11', 'status': 'checked',
         'input_sha256': a.program_sha256, 'program_sha256': a.program_sha256,
         'reason': None, 'location': None, 'execution_admission': False}
         and checker['execution_admission'] is False and data['checker.stderr'] == b'', 'PREVIEW_CHECKER')
    artifact = metadata(data['artifact.json'])
    need(set(artifact) == ARTIFACT_FIELDS and artifact['schema'] == 'bagaev-record-cpython/1'
         and artifact['profile'] == 'bagaev-typed-record/11' and type(artifact['python']) is str, 'PREVIEW_ARTIFACT')
    need(all(pin(artifact[n]) and artifact[n] == receipt[n] for n in ('program_sha256', 'generator_sha256', 'runtime_sha256')), 'PREVIEW_ARTIFACT')
    python = artifact['python'].encode('utf-8'); need(len(python) <= LIMIT, 'PREVIEW_BOUNDS')
    need(sha(python) == receipt['python_sha256'], 'PREVIEW_ARTIFACT')
    input_files = {n: {'bytes': len(raw), 'sha256': sha(raw)} for n, raw in sorted(data.items())}
    packet_pin = sha(canon(input_files))
    report = {'schema': 'bagaev-record-cpython-preview/1', 'status': 'consistent',
        'form': 'record-form/5', 'profile': 'bagaev-typed-record/11',
        'packet_sha256': packet_pin, 'compile_receipt_sha256': a.receipt_sha256,
        'source_sha256': a.source_sha256, 'program_sha256': a.program_sha256,
        'artifact_sha256': sha(data['artifact.json']), 'python_sha256': sha(python), 'python_bytes': len(python),
        'claimed_checker_sha256': receipt['checker_sha256'], 'claimed_generator_sha256': receipt['generator_sha256'],
        'claimed_runtime_sha256': receipt['runtime_sha256'], 'input_files': input_files,
        'fresh_compilation': False, 'checker_invoked': False, 'compiler_authentication': False,
        'semantic_check': False, 'source_program_equivalence_checked': False,
        'program_python_equivalence_checked': False, 'python_syntax_checked': False, 'execution_admission': False}
    report_raw = canon(report); need(len(report_raw) <= 16384, 'PREVIEW_BOUNDS')
    payload = {'python.txt': python, 'report.json': report_raw}
    manifest = canon({'schema': 'bagaev-record-cpython-preview-files/1', 'packet_sha256': packet_pin,
        'files': {n: {'bytes': len(raw), 'sha256': sha(raw)} for n, raw in payload.items()}, 'execution_admission': False})
    need(len(manifest) <= 16384, 'PREVIEW_BOUNDS')
    out = path(a.output)
    need(not out.is_relative_to(base) and not base.is_relative_to(out), 'PREVIEW_PATH')
    need(not out.exists() and not out.is_symlink(), 'PREVIEW_EXISTS')
    def preserved():
        need(read(SELF, LIMIT) == own, 'PREVIEW_PIN'); inventory(base, LIMITS)
        for n, raw in data.items(): need(read(base / n, LIMITS[n]) == raw, 'PREVIEW_PIN')
    preserved()
    try:
        out.mkdir(mode=0o700)
        for n, raw in payload.items(): save(out / n, raw)
        preserved()
        inventory(out, payload)
        for n, raw in payload.items(): need(read(out / n, max(len(raw), 1)) == raw, 'PREVIEW_PIN')
        save(out / 'MANIFEST.json', manifest)
        inventory(out, {*payload, 'MANIFEST.json'})
        for n, raw in dict(payload, **{'MANIFEST.json': manifest}).items(): need(read(out / n, max(len(raw), 1)) == raw, 'PREVIEW_PIN')
        preserved()
        emit({'schema': 'bagaev-record-cpython-preview-result/1', 'status': 'preview', 'packet_sha256': packet_pin,
              'python_sha256': sha(python), 'report_sha256': sha(report_raw), 'manifest_sha256': sha(manifest), 'execution_admission': False})
        return 0
    except (OSError, ValueError, KeyboardInterrupt):
        raise PreviewError('PREVIEW_UNCERTAIN', True) from None
def main(argv=None):
    try: a = arguments(argv)
    except PreviewError as exc:
        try: emit({'schema': 'bagaev-record-cpython-preview-error/1', 'code': exc.code, 'uncertain': False}, 2)
        except (OSError, PreviewError): pass
        return 2
    except (OSError, KeyboardInterrupt) as exc:
        code = 'PREVIEW_INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'PREVIEW_DELIVERY'
        try: emit({'schema': 'bagaev-record-cpython-preview-error/1', 'code': code, 'uncertain': False}, 2)
        except (OSError, PreviewError): pass
        return 3
    if a is None: return 0
    try: return preview(a)
    except (PreviewError, OSError, KeyboardInterrupt) as exc:
        uncertain = isinstance(exc, PreviewError) and exc.uncertain
        code = exc.code if isinstance(exc, PreviewError) else ('PREVIEW_INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'PREVIEW_PATH')
        try: emit({'schema': 'bagaev-record-cpython-preview-error/1', 'code': code, 'uncertain': uncertain}, 2)
        except (OSError, PreviewError): pass
        return 4 if uncertain else 3
if __name__ == '__main__': raise SystemExit(main())
