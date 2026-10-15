"""Frozen logical-work controls; no language evaluator or native dispatch."""
from pathlib import Path
import copy
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from bagaev_record_work_correlation import analyze
from bagaev_record_work import analyze as baseline


def inputs(n=64, b=0, m=1, d=1024):
    return {'c': {'type': 'Bool'},
            'xs': {'type': 'TextList', 'items': n, 'bytes': b},
            'ys': {'type': 'TextList', 'items': m, 'bytes': d}}


def expression(op, yes=None, no=None):
    return [op, ['if', ['arg', 'c'],
                 ['arg', 'xs'] if yes is None else yes,
                 ['arg', 'ys'] if no is None else no]]


class Correlation(unittest.TestCase):
    def test_literal_correlated_bounds(self):
        for op, old, new in (('list.unique', 135172, 4100),
                             ('list.increasing', 2116, 2053),
                             ('list.len', 4, 4)):
            with self.subTest(op=op):
                tree, args = expression(op), inputs()
                snapshot = copy.deepcopy((tree, args))
                result = analyze(tree, args)
                self.assertEqual(baseline(tree, args)['upper_work'], old)
                self.assertEqual(result['baseline_upper_work'], old)
                self.assertEqual(result['upper_work'], new)
                self.assertEqual(result['refinement'], 'root-unary-if')
                self.assertTrue(result['fits_work_budget'])
                self.assertFalse(result['semantic_check'])
                self.assertFalse(result['execution_admission'])
                self.assertTrue(result['requires_checked_program'])
                self.assertEqual((tree, args), snapshot)

    def test_equal_bounds_and_branch_costs(self):
        args = inputs(3, 5, 4, 1)
        for tree, old, new in (
                (expression('list.unique'), 60, 43),
                (expression('list.unique', no=['arg', 'xs']), 43, 43),
                (expression('list.unique', ['list.unique', ['arg', 'xs']],
                            ['arg', 'xs']), 83, 83)):
            result = analyze(tree, args)
            self.assertEqual(result['baseline_upper_work'], old)
            self.assertEqual(result['upper_work'], new)

    def test_original_refusals_survive(self):
        args = inputs()
        cases = [
            ['list.unique', ['if', ['bool', False], ['call', 'missing'], ['arg', 'xs']]],
            expression('list.unique', no=['int', 1]),
            ['list.unique', ['if', ['int', 0], ['arg', 'xs'], ['arg', 'ys']]],
            ['list.unique', ['if', ['arg', 'c'], ['use', 'missing'], ['arg', 'ys']]],
        ]
        for tree in cases:
            original, result = baseline(tree, args), analyze(tree, args)
            self.assertEqual(original['status'], 'UNKNOWN')
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['reason'], original['reason'])
            self.assertEqual(result.get('location'), original.get('location'))
            self.assertNotIn('upper_work', result)
            self.assertNotIn('baseline_upper_work', result)

    def test_unselected_shape_retains_baseline(self):
        tree, args = ['list.unique', ['arg', 'xs']], inputs(3, 5, 4, 1)
        result = analyze(tree, args)
        self.assertEqual(result['upper_work'], 41)
        self.assertEqual(result['baseline_upper_work'], 41)
        self.assertEqual(result['refinement'], 'none')

    def test_refinement_failure_or_larger_bound_keeps_original(self):
        tree, args = expression('list.unique'), inputs()
        original = baseline(tree, args)
        for refused in ({'status': 'UNKNOWN', 'reason': 'analysis-bounds'},
                        dict(original, upper_work=original['upper_work'] + 1)):
            with patch('bagaev_record_work_correlation.baseline_analyze',
                       side_effect=[original, refused]) as calls:
                result = analyze(tree, args)
            self.assertEqual(calls.call_count, 2)
            self.assertEqual(result['upper_work'], original['upper_work'])
            self.assertEqual(result['fits_work_budget'], original['fits_work_budget'])
            self.assertEqual(result['refinement'], 'none')

    def test_concrete_visit_budget_fallback(self):
        def additions(leaves, special=False):
            if leaves == 1:
                return ['list.len', ['arg', 'xs']] if special else ['int', 0]
            left = leaves // 2
            return ['add', additions(left, special), additions(leaves - left)]
        initial = additions(1021, True)  # 2042 visits, balanced depth.
        yes = ['let', 'scratch', initial, ['arg', 'xs']]  # 2044 visits.
        tree, args = expression('list.unique', yes=yes), inputs(3, 5, 4, 1)
        original = baseline(tree, args)  # Exactly 2048 static visits.
        distributed = ['if', ['arg', 'c'], ['list.unique', yes],
                       ['list.unique', ['arg', 'ys']]]
        refused = baseline(distributed, args)  # Exactly 2049 static visits.
        self.assertEqual(original['status'], 'SUPPORTED')
        self.assertEqual(original['upper_work'], 2103)
        self.assertEqual(refused['status'], 'UNKNOWN')
        self.assertEqual(refused['reason'], 'analysis-bounds')
        result = analyze(tree, args)
        self.assertEqual(result['refinement'], 'none')
        self.assertEqual(result['upper_work'], 2103)
        self.assertEqual(result['baseline_upper_work'], 2103)


if __name__ == '__main__':
    unittest.main()
