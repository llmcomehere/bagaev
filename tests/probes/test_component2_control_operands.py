"""Data-only component-form/2 comparison grouping, using frozen component data."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
import bagaev_component_outcome_form as form
DATA = ROOT/'examples/probes/component-outcomes/form'
IF = ['if', ['bool', True], ['int', 2], ['int', 3]]

def golden():
    cases = json.loads((DATA/'cases.json').read_bytes())['cases']
    return copy.deepcopy(next(c['expected']['source'] for c in cases if c['id'] == 'EXACT'))

def with_probe(body):
    value = golden()
    value['program']['functions']['probe'] = {'params': [], 'result': 'Bool', 'body': copy.deepcopy(body)}
    return value

class ComponentComparison(unittest.TestCase):
    def test_literal_source_tree(self):
        source = (DATA/'StockOutcome.bagaev').read_text().rstrip()
        source = source[:-1] + 'fn probe() -> Bool = (if true then 2 else 3) < 10; }'
        expected = with_probe(['lt', IF, ['int', 10]])
        self.assertEqual(form.decode(source), expected)
        self.assertEqual(form.decode(form.encode(expected)), expected)
        wrong = with_probe(['if', ['bool', True], ['int', 2], ['lt', ['int', 3], ['int', 10]]])
        self.assertNotEqual(expected, wrong)

    def test_positions_and_nested(self):
        nested = ['if', ['bool', False], IF, ['int', 4]]
        for left, right in ((IF, ['int', 10]), (['int', 10], IF), (IF, IF), (nested, IF)):
            with self.subTest(left=left, right=right):
                value = with_probe(['lt', left, right])
                before = copy.deepcopy(value)
                encoded = form.encode(value)
                self.assertEqual(value, before)
                self.assertEqual(form.decode(encoded), value)
                self.assertEqual(form.encode(form.decode(encoded)), encoded)

    def test_plain_comparison(self):
        value = with_probe(['lt', ['int', 2], ['int', 10]])
        encoded = form.encode(value)
        self.assertIn(b'  fn probe() -> Bool = (2 < 10);\n', encoded)
        self.assertEqual(form.decode(encoded), value)

    def test_unrepresentable_intrinsic_collision(self):
        value = with_probe(['variant', 'list', 'unique', ['int', 2]])
        value['program']['variants']['list'] = {'unique': 'Int64'}
        value['program']['functions']['probe']['result'] = 'list'
        before = copy.deepcopy(value)
        with self.assertRaises(form.FormError) as ctx:
            form.encode(value)
        self.assertEqual(ctx.exception.code, 'FORM_PROFILE')
        self.assertEqual(value, before)

    def test_frozen_cases_and_refusals(self):
        cases = json.loads((DATA/'cases.json').read_bytes())['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                try:
                    value = form.decode(case['text'])
                    actual = {'source': value}
                except form.FormError as error:
                    actual = {'error': error.code}
                self.assertEqual(actual, case['expected'])
                if 'source' in actual:
                    self.assertEqual(form.decode(form.encode(value)), value)
        with self.assertRaises(form.FormError) as ctx:
            form.encode(with_probe(['add', ['int', 2], ['int', 3]]))
        self.assertEqual(ctx.exception.code, 'FORM_PROFILE')
        import bagaev_component_form as old
        with self.assertRaises(old.FormError) as ctx:
            old.decode((DATA/'StockOutcome.bagaev').read_bytes())
        self.assertEqual(ctx.exception.code, 'FORM_VERSION')

if __name__ == '__main__':
    unittest.main()
