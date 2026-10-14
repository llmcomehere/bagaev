"""Unchanged frozen P0 projections for the explicitly selected serial subset."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.p0_receiver import Receiver
from src.p0_scenario import Scenario

def project(actual, expected):
    if type(actual) is not type(expected):
        raise AssertionError('Observation type differs')
    if type(expected) is dict:
        if not set(expected) <= set(actual):
            raise AssertionError('Missing observed field')
        return {k: project(actual[k], v) for k, v in expected.items()}
    if type(expected) is list:
        if len(actual) != len(expected):
            raise AssertionError('Observation length differs')
        return [project(a, b) for a, b in zip(actual, expected)]
    if actual != expected:
        raise AssertionError((actual, expected))
    return actual

class P0ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT/'examples/probes/p0-serial-subset.json').read_bytes())
        for name, digest in self.plan['oracle_hashes'].items():
            self.assertEqual(hashlib.sha256((ROOT/'docs'/name).read_bytes()).hexdigest(), digest)
        oracle = json.loads((ROOT/'docs/p0-cases.json').read_bytes())
        self.fixtures = oracle['fixtures']
        self.cases = {c['id']: c for c in oracle['cases']}
        self.assertEqual(len(self.cases), len(oracle['cases']))
        all_ids = self.plan['receiver_cases'] + self.plan['scenario_cases'] + self.plan['excluded_cases']
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertEqual(set(all_ids), set(self.cases))

    def resolve(self, value, stack=()):
        if type(value) is dict:
            if '$ref' in value:
                self.assertEqual(set(value), {'$ref'})
                name = value['$ref']
                self.assertIs(type(name), str)
                self.assertIn(name, self.fixtures)
                self.assertNotIn(name, stack)
                return self.resolve(self.fixtures[name], stack + (name,))
            return {k: self.resolve(v, stack) for k, v in value.items()}
        if type(value) is list:
            return [self.resolve(v, stack) for v in value]
        return deepcopy(value)

    def fixture(self, value):
        return self.resolve(self.fixtures[value]) if type(value) is str else self.resolve(value)

    def expected(self, value):
        if type(value) is dict:
            return {k: self.fixture(v) if k == 'value' and type(v) is str and v in self.fixtures
                    else self.expected(v) for k, v in value.items()}
        if type(value) is list:
            return [self.expected(v) for v in value]
        return deepcopy(value)

    def test_frozen_serial_receiver_cases(self):
        self.assertEqual(len(self.plan['receiver_cases']), 22)
        count = 0
        for case_id in self.plan['receiver_cases']:
            with self.subTest(case_id=case_id):
                case = deepcopy(self.cases[case_id])
                initial, sessions = self.fixture(case['initial']), self.resolve(self.fixtures['sessions'])
                initial_before, sessions_before = deepcopy(initial), deepcopy(sessions)
                receiver = Receiver(initial, sessions)
                retained = []
                for step in case['steps']:
                    event = step['event']
                    observed = None
                    if event == 'revoke_grant':
                        receiver.fixture_revoke(step['principal'], step['grant'])
                    elif event.startswith('advance_'):
                        field = event[len('advance_'):]
                        receiver.fixture_revision(field, step[field])
                    elif event in ('deliver_write', 'deliver_transfer'):
                        intent = self.fixture(step['intent'])
                        intent_before = deepcopy(intent)
                        observed = receiver.command(event[len('deliver_'):], step['session'], intent,
                                                    step.get('presented_epoch'))
                        self.assertEqual(intent, intent_before)
                    elif event in ('query_operation', 'query_transfer'):
                        field = 'operation_id' if event == 'query_operation' else 'transfer_id'
                        observed = receiver.command(event, step['session'], task_id=step['task_id'], receipt_id=step[field])
                    else:
                        self.fail('Unsupported selected event: ' + event)
                    for old, frozen in retained:
                        self.assertEqual(old, frozen)
                    if 'expect' in step:
                        want = self.expected(step['expect'])
                        self.assertEqual(project(observed, want), want)
                        count += 1
                    if observed is not None:
                        retained.append((observed, deepcopy(observed)))
                self.assertEqual(case, self.cases[case_id])
                self.assertEqual(initial, initial_before)
                self.assertEqual(sessions, sessions_before)
                snapshot = receiver.snapshot()
                for returned, frozen in retained:
                    if returned['response']['kind'] == 'receipt':
                        returned['response']['value']['intent']['task_id'] = 'tampered-output'
                self.assertEqual(receiver.snapshot(), snapshot)
                detached = receiver.snapshot()
                detached['record']['tags'].append('tampered-snapshot')
                self.assertEqual(receiver.snapshot(), snapshot)
        self.assertEqual(count, 45)

    def test_frozen_loss_recovery_scenarios(self):
        self.assertEqual(len(self.plan['scenario_cases']), 11)
        count = 0
        for case_id in self.plan['scenario_cases']:
            with self.subTest(case_id=case_id):
                case = deepcopy(self.cases[case_id])
                initial, sessions = self.fixture(case['initial']), self.resolve(self.fixtures['sessions'])
                before_initial, before_sessions = deepcopy(initial), deepcopy(sessions)
                model = Scenario(initial, sessions)
                for raw in case['steps']:
                    step = deepcopy(raw)
                    for key in ('intent', 'request'):
                        if key in step:
                            step[key] = self.fixture(step[key])
                    observed = model.event(step)
                    if 'expect' in raw:
                        want = self.expected(raw['expect'])
                        self.assertEqual(project(observed, want), want)
                        count += 1
                self.assertEqual(case, self.cases[case_id])
                self.assertEqual(initial, before_initial)
                self.assertEqual(sessions, before_sessions)
        self.assertEqual(count, 31)

    def test_projection_refuses_wrong_observations(self):
        for actual, expected in [(True, 1), ({}, {'absent': 0}), ([1], [1, 2]), ({'x': 2}, {'x': 1})]:
            with self.subTest(actual=actual, expected=expected), self.assertRaises(AssertionError):
                project(actual, expected)

if __name__ == '__main__':
    unittest.main()
