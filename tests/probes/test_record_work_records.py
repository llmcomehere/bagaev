"""Data-only bounds for the existing compact-guide scalar record-list fold."""
from pathlib import Path
import json
import copy
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from bagaev_record_work import analyze
import record_text

RECORDS = {'Item': {'amount': 'Int64'}}
LISTS = {'Items': {'element': 'Item', 'capacity': 16}}
BODY = ['loop', 16, 'i', 'sum', ['int', 0],
        ['if', ['lt', ['use', 'i'], ['records.len', ['arg', 'items']]],
         ['add', ['use', 'sum'], ['field', ['records.at', ['arg', 'items'], ['use', 'i']], 'amount']],
         ['use', 'sum']]]
SOURCE = '''bagaev record-form/5; program {
record Item { amount: Int64 }; list Items of Item capacity 16; entry main;
fn main(items: Items) -> Int64 = fold (16, 0) with (i, sum) in
if i < records.len(items) then sum + record.field(records.at(items, i), "amount") else sum;
}'''


class RecordWork(unittest.TestCase):
    def run_analysis(self, body=BODY, count=16, records=RECORDS, lists=LISTS):
        return analyze(body, {'items': {'type': 'Items', 'items': count}}, records=records, lists=lists)

    def test_frozen_guide_bounds(self):
        for count in (0, 2, 16):
            result = self.run_analysis(count=count)
            self.assertEqual(result['upper_work'], 178)
            self.assertTrue(result['fits_work_budget'])
            self.assertFalse(result['semantic_check'])
            self.assertFalse(result['execution_admission'])
        unguarded = ['field', ['records.at', ['arg', 'items'], ['int', 0]], 'amount']
        self.assertEqual(self.run_analysis(unguarded, 0)['upper_work'], 4)

    def test_bound_and_declaration_refusals(self):
        for count in (-1, 17, True, '1'):
            self.assertEqual(self.run_analysis(count=count)['status'], 'UNKNOWN')
        for records, lists in [({}, LISTS), ({'Item': {'amount': 'Text'}}, LISTS),
                               (RECORDS, {'Items': {'element': 'Item', 'capacity': True}}),
                               (RECORDS, {'Items': {'element': 'Item'}}), ([], LISTS)]:
            result = self.run_analysis(records=records, lists=lists)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertNotIn('upper_work', result)
        self.assertEqual(analyze(BODY, {'items': {'type': 'Items', 'items': 16}})['status'], 'UNKNOWN')

    def test_projection_and_nominal_refusals(self):
        for expression in (['records.at', ['arg', 'items'], ['bool', True]],
                           ['field', ['records.at', ['arg', 'items'], ['int', 0]], 'missing'],
                           ['field', ['int', 0], 'amount']):
            self.assertEqual(self.run_analysis(expression)['status'], 'UNKNOWN')
        lists = dict(LISTS, Other={'element': 'Item', 'capacity': 16})
        args = {'a': {'type': 'Items', 'items': 0}, 'b': {'type': 'Other', 'items': 0}}
        result = analyze(['if', ['bool', True], ['arg', 'a'], ['arg', 'b']], args,
                         records=RECORDS, lists=lists)
        self.assertEqual(result['status'], 'UNKNOWN')

    def test_boolean_field_and_input_immutability(self):
        records = {'Flag': {'enabled': 'Bool'}}
        lists = {'Flags': {'element': 'Flag', 'capacity': 1}}
        args = {'flags': {'type': 'Flags', 'items': 1}}
        before = copy.deepcopy((records, lists, args))
        body = ['not', ['field', ['records.at', ['arg', 'flags'], ['int', 0]], 'enabled']]
        result = analyze(body, args, records=records, lists=lists)
        self.assertEqual(result['upper_work'], 5)
        self.assertEqual((records, lists, args), before)

    def test_inspection_keeps_default_and_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            source = d/'source'; source.write_text(SOURCE)
            bounds = d/'bounds'; bounds.write_text('{"items":{"type":"Items","items":16}}')
            output = d/'out'
            record_text.convert(['inspect', str(source), '--form', '5', '--bounds', str(bounds), '--output', str(output)])
            result = json.loads(output.read_bytes())['work_bound']
            self.assertEqual(result['upper_work'], 178)
            self.assertFalse(result['execution_admission'])


if __name__ == '__main__':
    unittest.main()
