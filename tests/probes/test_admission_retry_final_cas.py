"""Retained admission ordering with controlled restore and actual SQLite."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_durable_programmes import DurableProgrammes


class AdmissionRetryTests(unittest.TestCase):
    def exercise(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'owner.sqlite'
            config = {'policy': {}, 'sources': [{'test': 'source'}]}
            source = image.pin(config['sources'][0])
            proposal = {'expected': {'generation': 0, 'source': source},
                        'target': source, 'policy': image.pin(config['policy']),
                        'assertions': 'a' * 64, 'producer': 'b' * 64,
                        'qualification': 'c' * 64}
            receipt = {'kind': 'Admitted', 'head': {'generation': 1, 'source': source}}
            value = {'admissions': [{'id': 'M1', 'intent': copy.deepcopy(proposal),
                                    'receipt': copy.deepcopy(receipt)}]}
            before = storage.create(path, envelope.encode(value))
            nested = []

            def restore(raw, **kwargs):
                if mode in ('changed', 'aba'):
                    other = storage.compare_and_swap(
                        path, before['generation'], before['digest'], b'{"nested":true}')
                    if mode == 'aba':
                        other = storage.compare_and_swap(
                            path, other['generation'], other['digest'], before['image'])
                    nested.append(other)
                return copy.deepcopy(value), object()

            manager = object.__new__(DurableProgrammes)
            manager._settings = lambda: copy.deepcopy(config)
            manager.bootstrap = source
            manager.checker = manager.evaluator = manager.conditions = None

            def forbidden(*args):
                self.fail('retained retry called qualifier or mutation authority')

            manager.qualifier = manager.authority = forbidden
            if mode == 'changed-intent':
                proposal['qualification'] = 'd' * 64
            with patch.object(envelope, 'restore', side_effect=restore):
                if mode in ('changed', 'aba'):
                    with self.assertRaises(storage.StorageError) as caught:
                        manager.admit(path, 'M1', proposal)
                    self.assertEqual(caught.exception.code, 'STORAGE_CONFLICT')
                elif mode == 'changed-intent':
                    with self.assertRaises(envelope.ProgrammeError) as caught:
                        manager.admit(path, 'M1', proposal)
                    self.assertEqual(caught.exception.code, 'PROGRAMME_INTENT_CONFLICT')
                else:
                    answer = manager.admit(path, 'M1', proposal)
                    self.assertEqual(answer, receipt)
                    answer['head']['source'] = 'detached'
                    self.assertEqual(value['admissions'][0]['receipt'], receipt)
            expected = {k: nested[-1][k] for k in before} if nested else before
            self.assertEqual(storage.read(path), expected)

    def test_stable_detached_retry_is_no_write(self):
        self.exercise('stable')

    def test_nested_change_conflicts(self):
        self.exercise('changed')

    def test_aba_conflicts(self):
        self.exercise('aba')

    def test_changed_intent_keeps_its_error(self):
        self.exercise('changed-intent')


if __name__ == '__main__':
    unittest.main()
