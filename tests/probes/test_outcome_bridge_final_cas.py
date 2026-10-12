"""Direct bridge final CAS with controlled callbacks and real SQLite files."""
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
import bagaev_outcome_image as image
from bagaev_outcome_storage import Bridge


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


class BridgeTests(unittest.TestCase):
    def exercise(self, command='observe', *, nested=0, changed=False, clock=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'owner.sqlite'
            original = {'clock_floor': 0, 'revision': 7}
            before = storage.create(path, encode(original))
            captured = copy.deepcopy(original)
            if changed:
                captured['revision'] = 8
            if clock:
                captured['clock_floor'] = 1
            answer = {'status': 'Unknown'}
            nested_row = None

            class Owner:
                def dispatch(self, packet):
                    nonlocal nested_row
                    if nested:
                        other = dict(original, nested=True)
                        nested_row = storage.compare_and_swap(
                            path, before['generation'], before['digest'], encode(other))
                        if nested == 2:
                            nested_row = storage.compare_and_swap(
                                path, nested_row['generation'], nested_row['digest'], before['image'])
                    return copy.deepcopy(answer)

                submit = observe = cancel = dispatch

            bridge = object.__new__(Bridge)
            bridge._settings = lambda: {'policy': {}, 'origin': {}, 'clock_domain': 'test'}
            bridge.checker = bridge.evaluator = bridge.conditions = None
            with patch.object(image, 'restore', return_value=Owner()), \
                 patch.object(image, 'capture', return_value=encode(captured)):
                if nested:
                    with self.assertRaises(storage.StorageError) as caught:
                        bridge.call(path, command, b'{}')
                    self.assertEqual(caught.exception.code, 'STORAGE_CONFLICT')
                    self.assertEqual(storage.read(path), {k: nested_row[k] for k in before})
                else:
                    self.assertEqual(bridge.call(path, command, b'{}'), answer)
                    current = storage.read(path)
                    if changed:
                        self.assertEqual(current['generation'], before['generation'] + 1)
                        self.assertEqual(json.loads(current['image']), captured)
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
