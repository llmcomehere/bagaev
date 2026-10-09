"""Own resource-aware draft specimen, data-only integration checks."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import bagaev_record_wide_draft as draft
from bagaev_record_work import analyze
import record_text

DIRECTORY = ROOT / 'examples/probes/record-work-edit'
CASES = json.loads((DIRECTORY / 'cases.json').read_bytes())


class ResourceEdit(unittest.TestCase):
    def test_exact_draft_and_scope(self):
        before = (DIRECTORY / 'Repeated.bagaev').read_text()
        after = (DIRECTORY / 'Reuse.bagaev').read_text()
        self.assertEqual(draft.form.decode(before), CASES['before_graph'])
        self.assertEqual(draft.form.decode(after), CASES['after_graph'])
        result = draft.draft(before, after, base_sha256=CASES['base'],
                             target_sha256=CASES['target'])
        self.assertEqual(result['program'], CASES['after_graph'])
        self.assertEqual(result['delta'], {'add': [], 'replace': ['summarize']})
        self.assertFalse(result['semantic_check'])
        self.assertFalse(result['execution_admission'])
        self.assertEqual(result['program']['functions']['marker'], CASES['before_graph']['functions']['marker'])
        with self.assertRaises(draft.DraftError):
            draft.draft(before, after, base_sha256='0'*64, target_sha256=CASES['target'])

    def test_expectations_distinguish_values_work_and_refusal(self):
        for case in CASES['cases']:
            if case['before']['status'] == 'success':
                self.assertEqual(case['before']['value'], case['after']['value'])
                self.assertGreater(case['before']['work'], case['after']['work'])
            else:
                self.assertEqual(case['before']['reason'], 'RR_WORK')
                self.assertEqual(case['after']['status'], 'success')
                self.assertGreater(case['before_bound'], 65536)
                self.assertLessEqual(case['after_bound'], 65536)

    def test_frozen_bounds_and_inspection_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            for case in CASES['cases']:
                bounds = d / 'bounds.json'
                bounds.write_text(json.dumps(case['bounds']))
                for version, filename in [('before', 'Repeated.bagaev'), ('after', 'Reuse.bagaev')]:
                    graph = CASES[version + '_graph']
                    value = analyze(graph['functions']['summarize']['body'], case['bounds'], graph['functions'])
                    self.assertEqual(value['upper_work'], case[version + '_bound'])
                    self.assertEqual(value['fits_work_budget'], case[version + '_bound'] <= 65536)
                    output = d / (case['name'] + version + '.json')
                    source = DIRECTORY / filename
                    record_text.convert(['inspect', str(source), '--form', '5', '--bounds',
                                         str(bounds), '--output', str(output)])
                    inspection = json.loads(output.read_bytes())
                    self.assertEqual(inspection['work_bound'], value)
                    self.assertEqual(inspection['program_sha256'], CASES['base' if version == 'before' else 'target'])
                    self.assertEqual(inspection['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
                    self.assertEqual(inspection['argument_bounds_sha256'], hashlib.sha256(bounds.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
