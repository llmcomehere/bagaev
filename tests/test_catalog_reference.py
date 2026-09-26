"""Frozen application observations and state/ownership regressions.

Run only under a separately admitted execution profile. The fixture supplies
expectations; this test module does not derive them from the implementation.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from catalog_reference import evaluate


def same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def containers(value):
    found, pending = set(), [value]
    while pending:
        current = pending.pop()
        if type(current) in (dict, list) and id(current) not in found:
            found.add(id(current))
            pending.extend(current.values() if type(current) is dict else current)
    return found


class CatalogReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = json.loads((ROOT / 'examples/beta/catalog-cases.json').read_bytes())
        cls.cases = {c['id']: c for c in cls.oracle['cases']}

    def checked(self, request, expected, evaluator=evaluate):
        before = copy.deepcopy(request)
        actual = evaluator(request)
        self.assertTrue(same(request, before), 'input mutation')
        self.assertTrue(same(actual, expected), 'complete typed response')
        self.assertFalse(containers(actual) & containers(request), 'input/output alias')
        return actual

    def fixture(self, name):
        case = self.cases[name]
        return (copy.deepcopy(self.oracle['requests'][case['request']]),
                self.oracle['responses'][case['expect']])

    def test_all_frozen_cases(self):
        self.assertEqual(len(self.cases), 99)
        self.assertEqual(sum(self.oracle['responses'][c['expect']]['kind'] == 'success'
                             for c in self.cases.values()), 30)
        for name in self.cases:
            with self.subTest(case=name):
                request, expected = self.fixture(name)
                self.checked(request, expected)

    def test_actual_evolution_chain(self):
        self.assertEqual(self.oracle['chains'], [
            {'id': 'EVOLUTION', 'cases': ['CHAIN-0', 'CHAIN-1', 'CHAIN-2', 'CHAIN-3']}])
        previous = None
        for name in self.oracle['chains'][0]['cases']:
            with self.subTest(case=name):
                request, expected = self.fixture(name)
                if previous is not None:
                    self.assertTrue(same(previous['state'], request['state']))
                    request['state'] = previous['state']
                previous = self.checked(request, expected)

    def test_repeatability_and_idempotence(self):
        for name in self.cases:
            with self.subTest(case=name):
                request, expected = self.fixture(name)
                first = self.checked(request, expected)
                second = self.checked(request, expected)
                self.assertFalse(containers(first) & containers(second))
                if first['kind'] == 'success':
                    request['state'] = first['state']
                    self.checked(request, expected)

    def test_result_mutation_does_not_reach_request(self):
        request, expected = self.fixture('REV-3')
        before = copy.deepcopy(request)
        result = self.checked(request, expected)
        result['state']['entries'][0]['manual_tags'].append('changed')
        result['state']['entries'][1]['indexed_tags'].clear()
        result['state']['entries'][0]['title'] = 'Changed'
        result['entry_ids'].clear()
        result['state']['entries'].clear()
        self.assertTrue(same(request, before))
        self.checked(request, expected)

    def test_every_output_state_is_valid_in_every_revision(self):
        for name in self.cases:
            request, expected = self.fixture(name)
            if expected['kind'] != 'success':
                continue
            result = self.checked(request, expected)
            for revision in range(4):
                with self.subTest(case=name, revision=revision):
                    replay = {'interface': 'catalog-application/2',
                              'behavior_revision': revision,
                              'state': result['state'], 'reindex': None}
                    before = copy.deepcopy(replay)
                    actual = evaluate(replay)
                    self.assertEqual(actual['kind'], 'success')
                    self.assertTrue(same(replay, before))
                    self.assertFalse(containers(actual) & containers(replay))
                    replay['state'] = actual['state']
                    self.checked(replay, actual)

    def test_malformed_json_shapes_and_deferred_dates(self):
        refusal = {'kind': 'refusal', 'reason': 'invalid-request'}
        values = [None, False, True, 0, 1.0, '', 'x', [], {}, [None], {'x': []}]
        paths = [('state',), ('state', 'entries'), ('state', 'entries', 0),
                 ('state', 'entries', 0, 'id'), ('state', 'entries', 0, 'title'),
                 ('state', 'entries', 0, 'manual_tags'),
                 ('state', 'entries', 0, 'indexed_tags'), ('reindex',),
                 ('reindex', 'entry_id'), ('reindex', 'tags')]
        for value in values:
            if type(value) is not dict:
                self.checked(copy.deepcopy(value), refusal)
            for path in paths:
                # Exclude shape-correct values, covered by literal cases instead.
                if ((path[-1] in ('id', 'title', 'entry_id') and value == 'x')
                        or (path[-1] in ('entries', 'manual_tags', 'indexed_tags', 'tags')
                            and value == [] and type(value) is list)
                        or (path == ('reindex',) and value is None)):
                    continue
                request, _ = self.fixture('REV-3')
                parent = request
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = copy.deepcopy(value)
                with self.subTest(path=path, value=value):
                    self.checked(request, refusal)
        # Arbitrarily nested malformed date values are never recursively visited.
        nested = []
        for _ in range(2000):
            nested = [nested]
        request, _ = self.fixture('REV-3')
        request['state']['entries'][0]['date'] = nested
        self.assertTrue(same(evaluate(request), {'kind': 'refusal', 'reason': 'invalid-date'}))
        self.assertIs(request['state']['entries'][0]['date'], nested)

    def test_checker_rejects_selected_wrong_behaviors(self):
        # Exercise behavioral detection, not just witness metadata.
        def first_seen(request):
            response = evaluate(request)
            response['state']['entries'][0]['manual_tags'] = list(
                dict.fromkeys(request['state']['entries'][0]['manual_tags']))
            return response

        def drop_manual(request):
            response = evaluate(request)
            response['state']['entries'][0]['manual_tags'] = []
            return response

        def wrong_missing_order(request):
            response = evaluate(request)
            response['entry_ids'] = ['b', 'c', 'd', 'a']
            return response

        def mutate(request):
            response = evaluate(request)
            request['state']['entries'].clear()
            return response

        def alias(request):
            return {'kind': 'success', 'state': request['state'], 'entry_ids': []}

        def partial(request):
            return {**evaluate(request), 'state': {}}

        for name, bad in [('SET-1', first_seen), ('REV-2', drop_manual),
                          ('REV-3', wrong_missing_order), ('REV-1', mutate),
                          ('EMPTY-3', alias), ('LATE-INVALID', partial)]:
            with self.subTest(case=name), self.assertRaises(AssertionError):
                self.checked(*self.fixture(name), evaluator=bad)
        self.assertFalse(same({'date': 1}, {'date': True}))
        self.assertFalse(same({'date': 1}, {'date': 1.0}))
        self.assertFalse(same([], ()))


if __name__ == '__main__':
    unittest.main()
