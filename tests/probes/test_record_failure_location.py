"""Synthetic retained-data joins; no program evaluation or authenticated captures."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import record_failure_location as cli
from bagaev_record_draft import digest, DraftError
from bagaev_record_wide_form import decode

SOURCE = 'bagaev record-form/5;\nprogram {\nentry main;\nfn main() -> Int64 =\n  7 + 7;\n}\n'
POINTER = '/program/functions/main/body/2'


def fixture(source=SOURCE, status='integer-overflow', reason='RR_OVERFLOW', pointer=POINTER):
    pins = dict(program_sha256=digest(decode(source)), arguments_sha256='a' * 64,
                source_sha256=hashlib.sha256(source.encode('utf8')).hexdigest())
    capture = dict(program_sha256=pins['program_sha256'],
                   arguments_sha256=pins['arguments_sha256'],
                   result=dict(schema='bagaev-typed-record-result/11', status=status,
                               reason=reason, location=pointer, work=9,
                               value_type=None, value=None))
    return capture, pins


class FailureLocation(unittest.TestCase):
    def test_prior_overflow_cli_example(self):
        examples = ROOT / 'examples/probes'
        source = examples / 'record-branch-edit/Before.bagaev'
        capture = examples / 'record-failure-location/overflow-capture.json'
        rows = json.loads((examples / 'record-capture-comparison/cases.json').read_bytes())
        prior = next(row for row in rows if row['name'] == 'overflow')
        self.assertEqual(capture.read_text(encoding='utf8'), prior['before_file'])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         '44aa09a9c7f6d15e6f50aee101a77f666f0bb38f1fa65eda5818bb9d7f103608')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'location.json'
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = cli.main([str(source), str(capture), '--form', '5',
                    '--program-sha256', '790c5e3bc358c16e9f831ce79dfa82d0f8013b469a059413fd6079c0e9e8f314',
                    '--arguments-sha256', 'c3f7c8546d7d1d31d48314475042deacca64377481791bd7d983514abebf5b07',
                    '--source-sha256', '44aa09a9c7f6d15e6f50aee101a77f666f0bb38f1fa65eda5818bb9d7f103608',
                    '--output', str(output)])
            self.assertEqual(code, 0)
            result = json.loads(output.read_bytes())
            self.assertEqual(result['excerpt'], 'x + 1')
            self.assertEqual(result['result']['reason'], 'RR_OVERFLOW')
            self.assertEqual(result['result']['work'], 5)
            location = result['location']
            self.assertEqual((location['start_byte'], location['end_byte']), (104, 109))
            self.assertEqual((location['start_line'], location['start_column'],
                              location['end_line'], location['end_column']), (1, 105, 1, 110))
            self.assertEqual(location['precision'], 'exact-expression')

    def test_four_retained_failure_families(self):
        for status, reason in [('integer-overflow', 'RR_OVERFLOW'),
                               ('list-index', 'RR_INDEX'), ('work-limit', 'RR_WORK'),
                               ('record-list-bound', 'RR_RECORD_LIST_ITEMS')]:
            capture, pins = fixture(status=status, reason=reason)
            original = copy.deepcopy(capture)
            result = cli.locate_failure(SOURCE, capture, **pins)
            self.assertEqual(result['result'], capture['result'])
            self.assertEqual(capture, original)
            self.assertEqual(result['excerpt'], '7')
            self.assertFalse(result['excerpt_truncated'])
            location = result['location']
            self.assertEqual((location['start_line'], location['start_column'],
                              location['end_line'], location['end_column']), (5, 7, 5, 8))
            prefix = SOURCE.splitlines(keepends=True)[:4]
            self.assertEqual(location['start_byte'], len(''.join(prefix).encode()) + 6)
            self.assertEqual(location['end_byte'], location['start_byte'] + 1)
            self.assertEqual(location['precision'], 'exact-expression')
            self.assertEqual(result['capture_sha256'], digest(capture))
            self.assertEqual(result['result_sha256'], digest(capture['result']))
            for flag in ('semantic_check', 'capture_authentication', 'execution_admission'):
                self.assertIs(result[flag], False)

    def test_layout_unicode_and_coarse_range(self):
        capture, pins = fixture()
        changed = SOURCE.replace('program {\n', 'program {\n// é\n')
        current = dict(pins, source_sha256=hashlib.sha256(changed.encode()).hexdigest())
        result = cli.locate_failure(changed, capture, **current)
        self.assertEqual(result['excerpt'], '7')
        self.assertEqual(result['location']['start_line'], 6)
        old = cli.locate_failure(SOURCE, capture, **pins)
        self.assertEqual(result['location']['start_byte'] - old['location']['start_byte'], 6)
        with self.assertRaisesRegex(DraftError, 'DIAGNOSTIC_LAYOUT'):
            cli.locate_failure(changed, capture, **pins)
        chain = SOURCE.replace('7 + 7', '1 + 2 + 3')
        capture, pins = fixture(chain, pointer='/program/functions/main/body/1')
        result = cli.locate_failure(chain, capture, **pins)
        self.assertEqual(result['excerpt'], '1 + 2 + 3')
        self.assertEqual(result['location']['precision'], 'enclosing-expression')

    def test_excerpt_bound(self):
        source = SOURCE.replace('Int64', 'Text').replace('7 + 7', '"' + 'é' * 300 + '"')
        capture, pins = fixture(source, pointer='/program/functions/main/body')
        result = cli.locate_failure(source, capture, **pins)
        self.assertEqual(result['excerpt'], '"' + 'é' * 255)
        self.assertTrue(result['excerpt_truncated'])
        self.assertEqual(result['location']['end_byte'] - result['location']['start_byte'], 602)

    def test_refusals(self):
        capture, pins = fixture()
        for key, code in [('program_sha256', 'CAPTURE_PROGRAM'),
                          ('arguments_sha256', 'CAPTURE_ARGUMENTS'),
                          ('source_sha256', 'DIAGNOSTIC_LAYOUT')]:
            with self.assertRaisesRegex(DraftError, code):
                cli.locate_failure(SOURCE, capture, **dict(pins, **{key: '0' * 64}))
        for value in (None, 'bad'):
            with self.assertRaisesRegex(DraftError, 'DIAGNOSTIC_LAYOUT'):
                cli.locate_failure(SOURCE, capture, **dict(pins, source_sha256=value))
        changed = SOURCE.replace('7 + 7', '7 + 8')
        with self.assertRaisesRegex(DraftError, 'DIAGNOSTIC_PROGRAM'):
            cli.locate_failure(changed, capture, **dict(pins, source_sha256=hashlib.sha256(changed.encode()).hexdigest()))
        capture['result']['location'] = '/program/functions/main/missing'
        with self.assertRaisesRegex(DraftError, 'DIAGNOSTIC_POINTER'):
            cli.locate_failure(SOURCE, capture, **pins)
        capture['result']['status'] = 'unknown'
        with self.assertRaisesRegex(DraftError, 'CAPTURE_RESULT'):
            cli.locate_failure(SOURCE, capture, **pins)
        capture['result'].update(status='success', reason=None, location=None, value_type='Int64', value=1)
        with self.assertRaisesRegex(DraftError, 'DIAGNOSTIC_STATUS'):
            cli.locate_failure(SOURCE, capture, **pins)

    def test_cli_main_and_preservation(self):
        capture, pins = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, saved, output = root / 'source', root / 'capture', root / 'output'
            source.write_text(SOURCE, encoding='utf8')
            saved.write_text(json.dumps(capture), encoding='utf8')
            original = source.read_bytes(), saved.read_bytes()
            args = [str(source), str(saved), '--form', '5', '--program-sha256', pins['program_sha256'],
                    '--arguments-sha256', pins['arguments_sha256'], '--source-sha256', pins['source_sha256'],
                    '--output', str(output)]
            def invoke(argv):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    code = cli.main(argv)
                return code, json.loads(stream.getvalue())
            code, receipt = invoke(args)
            self.assertEqual(code, 0)
            raw = output.read_bytes()
            self.assertEqual(receipt['result']['output_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(json.loads(raw)['capture_file_sha256'], hashlib.sha256(original[1]).hexdigest())
            code, receipt = invoke(args)
            self.assertEqual((code, receipt['error']['code']), (2, 'RECORD_PATH'))
            self.assertEqual(output.read_bytes(), raw)
            refused = args[:-1] + [str(root / 'refused')]
            refused[refused.index('--source-sha256') + 1] = '0' * 64
            code, receipt = invoke(refused)
            self.assertEqual((code, receipt['error']['code']), (2, 'DIAGNOSTIC_LAYOUT'))
            self.assertFalse((root / 'refused').exists())
            self.assertEqual((source.read_bytes(), saved.read_bytes()), original)


if __name__ == '__main__':
    unittest.main()
