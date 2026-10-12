"""Dispatcher ordering with controlled owner callbacks and actual SQLite CAS.

No typed evaluator, native kernel or production fault is executed here.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_durable_programmes import DurableProgrammes


class DispatchTests(unittest.TestCase):
    def exercise(self, command='observe', *, nested=0, changed=False, clock=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'owner.sqlite'
            receiver = {'clock_floor': 0, 'revision': 7}
            value = {'receiver': receiver, 'runs': [{'id': 'old', 'head': {'source': 's1'}}]}
            before = storage.create(path, envelope.encode(value))
            after_receiver = copy.deepcopy(receiver)
            if changed:
                after_receiver['revision'] = 8
            if clock:
                after_receiver['clock_floor'] = 1
            answer = {'kind': 'Declined', 'revision': 7}
            nested_row = None

            class Owner:
                def _packet(self, packet):
                    return {'source': 's1'}, None, None

                def dispatch(self, packet):
                    nonlocal nested_row
                    if nested:
                        other = copy.deepcopy(value)
                        other['nested'] = True
                        nested_row = storage.compare_and_swap(
                            path, before['generation'], before['digest'], envelope.encode(other))
                        if nested == 2:
                            nested_row = storage.compare_and_swap(
                                path, nested_row['generation'], nested_row['digest'], before['image'])
                    return copy.deepcopy(answer)

                submit = observe = cancel = dispatch

            owner = Owner()
            manager = object.__new__(DurableProgrammes)
            manager._load = lambda unused: ({'policy': {}, 'origin': {}, 'clock_domain': 'test'},
                                            before, copy.deepcopy(value), owner)
            with patch.object(image_codec, 'capture', return_value=envelope.encode(after_receiver)):
                if nested:
                    with self.assertRaises(storage.StorageError) as caught:
                        manager.call(path, 'old', command, b'{}')
                    self.assertEqual(caught.exception.code, 'STORAGE_CONFLICT')
                    self.assertEqual(storage.read(path), {k: nested_row[k] for k in before})
                else:
                    self.assertEqual(manager.call(path, 'old', command, b'{}'), answer)
                    current = storage.read(path)
                    if changed:
                        self.assertEqual(current['generation'], before['generation'] + 1)
                        self.assertEqual(json.loads(current['image'])['receiver'], after_receiver)
                    else:
                        self.assertEqual(current, before)

    def test_stable_noop_commands(self):
        for command in ('submit', 'observe', 'cancel'):
            with self.subTest(command=command):
                self.exercise(command)

    def test_nested_noop_commands(self):
        for command in ('submit', 'observe', 'cancel'):
            with self.subTest(command=command):
                self.exercise(command, nested=1)

    def test_noop_aba(self):
        self.exercise(nested=2)

    def test_clock_floor_only_is_not_a_write(self):
        self.exercise(clock=True)

    def test_changed_receiver_commits_once(self):
        self.exercise(changed=True)

    def test_changed_receiver_keeps_conflict(self):
        self.exercise(changed=True, nested=1)


if __name__ == '__main__':
    unittest.main()
