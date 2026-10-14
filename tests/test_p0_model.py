"""All frozen P0 model cases; no candidate byte execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.p0_model import check
from src.p0_handoff import snapshot_valid

class P0ModelTests(unittest.TestCase):
    def setUp(self):
        self.selection = json.loads((ROOT/'examples/probes/p0-model.json').read_bytes())
        for name, digest in self.selection['oracle_hashes'].items():
            self.assertEqual(hashlib.sha256((ROOT/'docs'/name).read_bytes()).hexdigest(), digest)
        self.oracle = json.loads((ROOT/'docs/p0-cases.json').read_bytes())

    def test_all_frozen_cases(self):
        before = deepcopy(self.oracle)
        result = check(self.oracle)
        self.assertEqual(self.oracle, before)
        self.assertEqual(result['case_count'], 85)
        self.assertEqual(result['projection_count'], 144)
        self.assertEqual(result['checker_refusals'], 6)
        self.assertEqual([r['case_id'] for r in result['cases']], self.selection['selected'])

    def test_snapshot_faults(self):
        original = self.oracle['fixtures']['handoff-successor-snapshot']
        self.assertTrue(snapshot_valid(original))
        for name in ('empty', 'duplicate-path', 'path-order', 'parent-path', 'content-change', 'file-digest', 'aggregate-digest', 'bad-id'):
            with self.subTest(fault=name):
                x = deepcopy(original)
                if name == 'empty': x['candidate_files'] = []
                elif name == 'duplicate-path': x['candidate_files'][1]['path'] = x['candidate_files'][0]['path']
                elif name == 'path-order': x['candidate_files'].reverse()
                elif name == 'parent-path': x['candidate_files'][0]['path'] = '../catalog'
                elif name == 'content-change': x['candidate_files'][0]['content_utf8'] += 'changed'
                elif name == 'file-digest': x['candidate_files'][0]['sha256'] = '0' * 64
                elif name == 'aggregate-digest': x['snapshot_bytes_sha256'] = '0' * 64
                elif name == 'bad-id': x['snapshot_id'] = '../escape'
                self.assertFalse(snapshot_valid(x))

if __name__ == '__main__':
    unittest.main()
