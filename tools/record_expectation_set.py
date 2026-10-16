#!/usr/bin/env python3
"""Compare the complete caller-pinned obligation set offline; never execute it."""
import os, stat, sys
from pathlib import Path
import record_text as transport
import record_run_verify as bundle
import record_run_expectation as single

LIMIT = 1048576
PAYLOAD_LIMIT = 64 * LIMIT
MEMBERS = {'source.bagaev', 'arguments.json', 'program.json', 'invocation.json',
           'reference.stdout', 'reference.stderr', 'receipt.json'}
BINDINGS = {'source_sha256': 'source.bagaev', 'arguments_sha256': 'arguments.json',
            'program_sha256': 'program.json', 'invocation_sha256': 'invocation.json',
            'result_sha256': 'reference.stdout', 'receipt_sha256': 'receipt.json'}

class SetError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def need(ok, code):
    if not ok:
        raise SetError(code)

def syntax(*pins):
    need(all(bundle.pin(p) for p in pins), 'SET_PIN')

def runs_document(raw, known):
    try:
        value = transport.parse_json(raw)
        need(type(value) is dict and set(value) == {'schema', 'runs'}, 'SET_RUNS_DOCUMENT')
        need(value['schema'] == 'bagaev-record-expectation-runs/1', 'SET_RUNS_DOCUMENT')
        rows = value['runs']
        need(type(rows) is list and len(rows) <= 256, 'SET_RUNS_DOCUMENT')
        result = {}
        for row in rows:
            need(type(row) is dict and set(row) == {'case', 'receipt_sha256'}, 'SET_RUNS_DOCUMENT')
            name = row['case']
            need(type(name) is str and name in known and name not in result, 'SET_RUNS_DOCUMENT')
            need(bundle.pin(row['receipt_sha256']), 'SET_RUNS_DOCUMENT')
            result[name] = row['receipt_sha256']
        return result
    except transport.Refusal:
        raise SetError('SET_RUNS_DOCUMENT') from None

def names(path, maximum, code):
    result = set()
    with os.scandir(path) as entries:
        for count, item in enumerate(entries, 1):
            need(count <= maximum, code)
            result.add(item.name)
    return result

def owned(path, directory, code):
    metadata = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    need(kind(metadata.st_mode) and metadata.st_uid == os.getuid(), code)

def preflight(root, ordered):
    fingerprints = {}
    code = 'SET_ROOT'
    try:
        owned(root, True, code)
        need(names(root, 256, code) == set(ordered), code)
        total = 0
        for case in ordered:
            code = 'SET_ROOT'
            child = root / case
            owned(child, True, code)
            code = 'RUN_VERIFY_PATH'
            need(names(child, 7, code) == MEMBERS, code)
            fingerprints[case] = {}
            for name in sorted(MEMBERS):
                owned(child / name, False, code)
                raw = bundle.read(child / name, 4096 if name == 'reference.stderr' else LIMIT)
                total += len(raw)
                need(total <= PAYLOAD_LIMIT, 'SET_PAYLOAD_BOUNDS')
                fingerprints[case][name] = bundle.sha(raw)
        return fingerprints
    except (OSError, ValueError) as error:
        if isinstance(error, (SetError, bundle.VerifyError)):
            raise
        raise SetError(code) from None

def serialize(report):
    raw = bundle.canonical(report)
    need(len(raw) <= LIMIT, 'SET_BOUNDS')
    return raw

def verify(directory, expectations, expectation_sha256, runs, runs_sha256,
           source_sha256, program_sha256):
    syntax(expectation_sha256, runs_sha256, source_sha256, program_sha256)
    raw = single.read(expectations)
    single.need(bundle.sha(raw) == expectation_sha256, 'EXPECT_DIGEST')
    spec = single.document(raw)
    required = [case['id'] for case in spec['cases']]
    try:
        raw_runs = transport.read_input(str(runs))
    except transport.Refusal as error:
        raise SetError('SET_RUNS_BOUNDS' if error.code == 'RECORD_BOUNDS' else 'SET_RUNS_PATH') from None
    need(bundle.sha(raw_runs) == runs_sha256, 'SET_RUNS_DIGEST')
    supplied = runs_document(raw_runs, set(required))
    ordered = [name for name in required if name in supplied]
    try:
        root = Path(directory).absolute()
    except (OSError, TypeError, ValueError):
        raise SetError('SET_ROOT') from None
    fingerprints = preflight(root, ordered)
    results = []
    mismatched = False
    for name in ordered:
        comparison = single.verify(root / name, supplied[name], expectations, expectation_sha256, name)
        verified = comparison['run']
        pins = fingerprints[name]
        need(all(verified[key] == pins[member] for key, member in BINDINGS.items())
             and pins['reference.stderr'] == bundle.sha(b''), 'SET_CHANGED')
        need(verified['source_sha256'] == source_sha256, 'SET_SOURCE')
        need(verified['program_sha256'] == program_sha256, 'SET_PROGRAM')
        mismatched = mismatched or comparison['status'] == 'mismatched'
        result = {key: verified[key] for key in ('receipt_sha256', 'arguments_sha256',
                  'result_sha256', 'runtime_status', 'reason', 'location', 'work')}
        result.update(case=name, status=comparison['status'],
                      expected_sha256=bundle.sha(bundle.canonical(comparison['expected'])),
                      actual_sha256=bundle.sha(bundle.canonical(comparison['actual'])))
        results.append(result)
    missing = [name for name in required if name not in supplied]
    report = {'schema': 'bagaev-record-expectation-set-verification/1',
              'status': 'mismatched' if mismatched else ('incomplete' if missing else 'matched'),
              'form': spec['form'], 'expectation_sha256': expectation_sha256,
              'runs_sha256': runs_sha256, 'source_sha256': source_sha256,
              'program_sha256': program_sha256, 'required_cases': required,
              'missing_cases': missing, 'results': results, 'compared_cases': len(results),
              'independent_oracle_verified': False, 'result_authentication': False,
              'execution_admission': False, 'fresh_run': False}
    if spec['schema'] == 'bagaev-record-run-expectations/2':
        report.update(schema='bagaev-record-expectation-set-verification/2',
                      argument_comparison='raw-utf8')
    serialize(report)
    return report

def main(argv=None):
    try:
        parser = transport.Parser(add_help=False, allow_abbrev=False)
        parser.add_argument('directory')
        for flag in ('expectations', 'expectation-sha256', 'runs', 'runs-sha256',
                     'source-sha256', 'program-sha256', 'output'):
            parser.add_argument('--' + flag, required=True)
        a = parser.parse_args(argv)
        syntax(a.expectation_sha256, a.runs_sha256, a.source_sha256, a.program_sha256)
        try:
            output = transport.path_value(a.output)
            need(not output.resolve().is_relative_to(transport.path_value(a.directory).resolve()), 'SET_OUTPUT')
            need(not output.exists() and not output.is_symlink(), 'SET_OUTPUT')
        except (OSError, ValueError, RuntimeError, transport.Refusal) as error:
            if isinstance(error, SetError):
                raise
            raise SetError('SET_OUTPUT') from None
        report = verify(a.directory, a.expectations, a.expectation_sha256, a.runs,
                        a.runs_sha256, a.source_sha256, a.program_sha256)
        try:
            transport.write_output(a.output, serialize(report))
        except transport.Refusal:
            raise SetError('SET_OUTPUT') from None
        return 0
    except (transport.Refusal, SetError, single.ExpectError, bundle.VerifyError, single.run.RunError) as error:
        print(error.code, file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
