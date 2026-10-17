"""Finite data-only checks of the authored-record dispatch contract."""
import contextlib
import importlib.util
import io
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('record_frontdoor_test_subject', ROOT / 'tools/record.py')
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)
ORACLE = json.loads((ROOT / 'tests/probes/record-frontdoor-oracle.json').read_bytes())
EXPECTED = {
    'run-cpython': ('record_cpython_run', []),
    'verify-cpython-run': ('record_cpython_run_verify', []),
    'verify-cpython-run-expectation': ('record_cpython_run_expectation', []),
    'check': ('record_source_check', []),
    'run': ('record_source_run', []),
    'inspect': ('record_text', ['inspect', '--form', '5']),
    'diagnose': ('record_diagnose', []),
    'format': ('record_format', []),
    'source-map': ('record_source_map', []),
    'function': ('record_function', []),
    'draft': ('record_draft', []),
    'export': ('record_export', []),
    'compile-cpython': ('record_cpython_compile', []),
    'history': ('record_revisions', []),
    'history-store': ('record_history_store', []),
    'verify-run': ('record_run_verify', []),
    'verify-run-expectation': ('record_run_expectation', []),
    'verify-expectation-set': ('record_expectation_set', []),
    'check-location': ('record_check_location', []),
    'failure-location': ('record_failure_location', []),
}

class Frontdoor(unittest.TestCase):
    def test_actual_inspect_default_and_form6_override(self):
        self.assertFalse(Path.cwd().resolve().is_relative_to(ROOT.resolve()))
        target = Path.cwd() / 'frontdoor-inspection'
        target.mkdir()
        canon = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        sha = lambda raw: hashlib.sha256(raw).hexdigest()
        for form, profile, extra in (('5', '11', []), ('6', '12', ['--form', '6'])):
            source = ('bagaev record-form/' + form + '; program { entry main; fn main() -> Int64 = 7; }').encode()
            program = {'schema': 'bagaev-typed-record/' + profile, 'records': {}, 'lists': {}, 'variants': {},
                       'entry': 'main', 'functions': {'main': {'params': [], 'result': 'Int64', 'body': ['int', 7]}}}
            src, output = target / ('source-' + form), target / ('inspection-' + form)
            with src.open('xb') as stream:
                stream.write(source)
            out, err = io.StringIO(), io.StringIO()
            with patch.object(sys, 'path', [str(ROOT / 'tools'), str(ROOT / 'src'), *sys.path]):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    self.assertEqual(cli.main(['inspect', str(src), *extra, '--output', str(output)]), 0)
            expected = {'schema': 'bagaev-record-inspection/1', 'source_sha256': sha(source),
                        'program_sha256': sha(canon(program)), 'entry': 'main',
                        'functions': [{'name': 'main', 'params': [], 'result': 'Int64'}],
                        'types': {'records': 0, 'lists': 0, 'variants': 0},
                        'semantic_check': False, 'execution_admission': False}
            self.assertEqual(output.read_bytes(), canon(expected))
            self.assertEqual(src.read_bytes(), source)
            self.assertEqual(err.getvalue(), '')
            self.assertEqual(json.loads(out.getvalue()), {'schema': 'bagaev-record-text/1', 'ok': True,
                'result': {'operation': 'inspect', 'source_schema': 'bagaev-typed-record/' + profile,
                'output_bytes': len(canon(expected)), 'output_sha256': sha(canon(expected)),
                'semantic_check': False, 'execution_admission': False}})

    def test_help_no_project_import(self):
        for option in ('-h', '--help'):
            with self.subTest(option=option), patch.object(cli.importlib, 'import_module') as load:
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    self.assertEqual(cli.main([option]), 0)
                load.assert_not_called()
                self.assertEqual(out.getvalue(), ORACLE['help'])
                self.assertTrue(out.getvalue().startswith('Bagaev authored-record commands\n'))
                self.assertIn('grant no execution authority.', out.getvalue())
                self.assertEqual(err.getvalue(), '')
                for route in EXPECTED:
                    self.assertEqual(sum(line.split()[0] == route for line in out.getvalue().splitlines() if line.split()), 1)

    def test_unknown_no_project_import(self):
        for argv in ([], ['missing'], ['--help', 'extra'], ['diff'], ['patch'], ['compile']):
            with self.subTest(argv=argv), patch.object(cli.importlib, 'import_module') as load:
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    self.assertEqual(cli.main(argv), 2)
                load.assert_not_called()
                self.assertEqual(out.getvalue(), '')
                self.assertEqual(err.getvalue(), 'RECORD_COMMAND\n')

    def test_all_routes_preserve_arguments_streams_and_result(self):
        self.assertEqual(set(cli.ROUTES), set(EXPECTED))
        for route, (module, prefix) in EXPECTED.items():
            with self.subTest(route=route):
                received = []
                def delegate(arguments):
                    received.append(arguments)
                    print('literal output')
                    print('literal error', file=sys.stderr)
                    return 23
                argv = [route, 'path with spaces', '--form', '6', '--unknown', '', '--']
                before = list(argv)
                out, err = io.StringIO(), io.StringIO()
                with patch.object(cli.importlib, 'import_module', return_value=types.SimpleNamespace(main=delegate)) as load:
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        self.assertEqual(cli.main(argv), 23)
                    load.assert_called_once_with(module)
                self.assertEqual(received, [prefix + before[1:]])
                self.assertEqual(argv, before)
                self.assertEqual(out.getvalue(), 'literal output\n')
                self.assertEqual(err.getvalue(), 'literal error\n')

    def test_delegate_failure_is_not_hidden(self):
        failure = RuntimeError('delegate refusal')
        def delegate(arguments):
            raise failure
        with patch.object(cli.importlib, 'import_module', return_value=types.SimpleNamespace(main=delegate)):
            with self.assertRaises(RuntimeError) as caught:
                cli.main(['check'])
        self.assertIs(caught.exception, failure)

    def test_sys_argv_and_prefix_not_mutated(self):
        received = []
        def delegate(arguments):
            received.append(list(arguments))
            arguments.clear()
            return 0
        with patch.object(cli.importlib, 'import_module', return_value=types.SimpleNamespace(main=delegate)):
            for _ in range(2):
                with patch.object(sys, 'argv', ['record.py', 'inspect', 'source']):
                    self.assertEqual(cli.main(), 0)
        self.assertEqual(received, [['inspect', '--form', '5', 'source']] * 2)

if __name__ == '__main__':
    unittest.main()
