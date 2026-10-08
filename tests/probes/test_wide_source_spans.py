"""Literal source ranges frozen before the mapping implementation."""
import hashlib
import json
import re
from pathlib import Path
import sys
import unittest
T = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(T / 'src'))
import bagaev_record_wide_spans as spans
import bagaev_record_wide_form as form
from bagaev_record_draft import digest


class SourceMaps(unittest.TestCase):
    def test_frozen_fragments(self):
        cases = json.loads((T / 'examples/probes/wide-source-spans/cases.json').read_bytes())
        for case in cases:
            with self.subTest(case=case['id']):
                source = case['source']
                result = spans.source_map(source)
                self.assertFalse(result['semantic_check'])
                self.assertFalse(result['execution_admission'])
                self.assertEqual(result['program_pin'], 'sha256:' + digest(form.decode(source)))
                self.assertEqual(result['source_sha256'], hashlib.sha256(source.encode()).hexdigest())
                actual = {x['program_pointer'].removeprefix('/program/functions/main/body'): x for x in result['locations']}
                self.assertEqual(set(actual), set(case['expected']))
                expression_start = source.index(' = ') + 3
                for pointer, expected in case['expected'].items():
                    fragment, precision, *occurrence = expected
                    start = expression_start
                    for _ in range((occurrence or [0])[0] + 1):
                        if fragment.isidentifier():
                            match = re.search(r'(?<![A-Za-z0-9_])' + re.escape(fragment) + r'(?![A-Za-z0-9_])', source[start:])
                            self.assertIsNotNone(match)
                            start += match.start()
                        else:
                            start = source.index(fragment, start)
                        end = start + len(fragment)
                        if _ < (occurrence or [0])[0]:start = end
                    item = actual[pointer]
                    self.assertEqual(item['precision'], precision)
                    self.assertEqual(item['start_byte'], len(source[:start].encode()))
                    self.assertEqual(item['end_byte'], len(source[:end].encode()))
                    for label, index in [('start', start), ('end', end)]:
                        self.assertEqual(item[label + '_line'], source.count('\n', 0, index) + 1)
                        self.assertEqual(item[label + '_column'], index - source.rfind('\n', 0, index))

    def test_layout_identity(self):
        source = 'bagaev record-form/5; program { entry main; fn main() -> Int64 = 1 + 2; }'
        changed = source.replace('1 + 2', '1\r\n + 2')
        a, b = spans.source_map(source), spans.source_map(changed)
        self.assertEqual(a['program_pin'], b['program_pin'])
        self.assertNotEqual(a['source_sha256'], b['source_sha256'])
        self.assertEqual(b['locations'][-1]['start_line'], 2)
        self.assertEqual(b['locations'][-1]['start_column'], 4)

    def test_existing_sum(self):
        source = (T / 'examples/probes/wide-record-literals/sum-before-fix.bagaev').read_bytes()
        result = spans.source_map(source)
        self.assertEqual(result['program_pin'], 'sha256:' + digest(form.decode(source)))
        self.assertGreater(len(result['locations']), 32)

    def test_catalogue(self):
        source = (T / 'examples/probes/catalog-wide/Catalog.bagaev').read_bytes()
        result = spans.source_map(source)
        self.assertEqual(result['program_pin'], 'sha256:' + digest(form.decode(source)))
        self.assertGreater(len(result['locations']), 100)
        self.assertEqual(len({x['program_pointer'] for x in result['locations']}), len(result['locations']))
        for item in result['locations']:
            fragment = source[item['start_byte']:item['end_byte']].decode('utf8')
            self.assertTrue(fragment)

    def test_node_boundary(self):
        expression = '1'
        for _ in range(10):
            expression = '(' + expression + ' + ' + expression + ')'
        source = 'bagaev record-form/5; program { entry main; fn main() -> Int64 = ' + expression + '; fn other() -> Int64 = 1; }'
        self.assertEqual(len(spans.source_map(source)['locations']), 2048)
        excessive = source.replace('fn other() -> Int64 = 1;', 'fn other() -> Int64 = 1 + 2;')
        form.decode(excessive)
        with self.assertRaises(form.FormError) as error:
            spans.source_map(excessive)
        self.assertEqual(error.exception.code, 'SPAN_BOUNDS')

    def test_bad_input(self):
        for source in [None, b'\xff', 'bagaev record-form/4;', 'bagaev record-form/5; program {}']:
            with self.assertRaises(form.FormError):spans.source_map(source)


if __name__ == '__main__':unittest.main()
