"""Static work-bound regressions over frozen reference observations; no evaluator."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from bagaev_record_work import analyze


class CardinalityWork(unittest.TestCase):
    def setUp(self):
        raw = (ROOT / 'examples/probes/record-work-cardinality/cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '63e0192dbe999673d4721a3f00e785f7e2ae55c95fb4a32362b1df54dca744ff')
        self.data = json.loads(raw)

    def test_all_frozen_bounds_and_refusal_boundaries(self):
        data = self.data
        self.assertEqual(len(data['cases']), 49)
        self.assertEqual(len({c['name'] for c in data['cases']}), 49)
        counts = {'success': 0, 'integer-overflow': 0, 'list-index': 0}
        for case in data['cases']:
            with self.subTest(case=case['name']):
                result = analyze(data['bodies'][case['body']],
                                 {'items': {'type': 'Items', 'items': len(case['arguments'][0])}},
                                 records=data['records'], lists=data['lists'])
                self.assertEqual(result['status'], 'SUPPORTED')
                self.assertEqual(result['upper_work'], case['bound'])
                self.assertTrue(result['fits_work_budget'])
                self.assertFalse(result['semantic_check'])
                self.assertFalse(result['execution_admission'])
                self.assertTrue(result['requires_checked_program'])
                self.assertLessEqual(case['expected']['work'], case['bound'])
                counts[case['expected']['status']] += 1
        self.assertEqual(counts, {'success': 17, 'integer-overflow': 30, 'list-index': 2})

    def test_success_cardinality_coverage(self):
        cases = [c for c in self.data['cases'] if c['expected']['status'] == 'success']
        self.assertEqual([len(c['arguments'][0]) for c in cases], list(range(17)))
        for case in cases:
            values = [item['amount'] for item in case['arguments'][0]]
            self.assertEqual(case['expected']['value'], sum(values))
            self.assertEqual(case['expected']['work'], 98 + 5 * len(values))


if __name__ == '__main__':
    unittest.main()
