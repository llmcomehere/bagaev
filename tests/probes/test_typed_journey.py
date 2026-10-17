"""Portable data-only checks; these do not repeat the recorded reference runs."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT
DATA = ROOT / 'examples/probes/typed-journey'
sys.path.insert(0, str(ROOT / 'src'))
import bagaev_record_wide_form as form
import bagaev_record_wide_function as edit
import bagaev_record_export as export
import bagaev_record_revisions as revisions
from bagaev_record_draft import digest

BASE = 'b4755a73e1090e2b4ed563f42c29250dc759c5b1224d3c5765a239cb6584351e'
FUNCTION = '7c2d12d8944682ca1ee7717de1a9e5fcc77477a3885472e8f75e032b5bba9c31'
TARGET = '77e72b2cab462713df4e4d56febe3709f49423ca16a62963969c3d049a022042'
SOURCE = 'dbab1ba6b3fabcfc6031ad0b7f9e58a6950b8264b1d0e5e179251b5d14cdb65e'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

class TypedJourney(unittest.TestCase):
    def test_cpython_raw_case_preserves_the_literal_business_oracle(self):
        args = (DATA / 'cross10.arguments.json').read_bytes()
        raw = (DATA / 'cross10.expectations.json').read_bytes()
        self.assertEqual(sha(args), 'a006adda514b6ec2f7f65b88801dec5c555e017eafc8554c7b0db31ace66f984')
        self.assertEqual(sha(raw), 'a81343f5311bd4d501bed0dd9839354f2e2289955f23b1c3c8d5eea7c577c9ea')
        original = next(row for row in json.loads((DATA / 'cases.json').read_bytes())['cases'] if row['id'] == 'cross10')
        self.assertEqual(json.loads(args), [original['request']])
        expected = {'schema':'bagaev-record-run-expectations/2','form':'record-form/5','cases':[
            {'id':'cross10','arguments_raw':args.decode(),'argument_count':1,'expected':{
                'status':'success','value_type':'Variant:BatchOutcome','value':original['value'],'reason':None,'location':None}}]}
        self.assertEqual(json.loads(raw), expected)

    def source(self):
        return (SOURCE_ROOT / 'examples/probes/inventory-batch-change/BatchLimited.bagaev').read_bytes()

    def change(self):
        source = self.source()
        fragment = (DATA / 'PerSku.fragment.bagaev').read_bytes()
        packet = edit.replace(source, fragment, base_sha256=BASE, function_sha256=FUNCTION)
        changed = export.export_source_with_fragment_layout(source, packet, fragment,
            base_sha256=BASE, target_sha256=TARGET, source_sha256=sha(source))
        return source, packet, changed

    def test_frozen_oracle_and_partition(self):
        raw = (DATA / 'cases.json').read_bytes()
        self.assertEqual(sha(raw), 'baecd43629e4d94714816847ceae8fe72a4d8810c2a173db977819855b111b0e')
        rows = json.loads(raw)['cases']
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({row['id'] for row in rows}), 12)
        self.assertEqual(sum(row['phase'] == 'predecessor' for row in rows), 8)
        self.assertEqual(sum(row['phase'] == 'successor' for row in rows), 4)
        for row in rows:
            if row['value']['case'] == 'BatchRejected':
                self.assertEqual(row['value']['value']['stock'], row['request']['stock'])
        self.assertEqual(next(row for row in rows if row['id'] == 'cross10')['value']['case'], 'BatchCommitted')

    def test_exact_one_function_and_preserved_bytes(self):
        source, packet, changed = self.change()
        self.assertEqual(sha(source), '8caccd806134b0a96cf10492e3aac5ac14a18212f0e2cb4303feea7187dc8e88')
        self.assertEqual(sha(changed), SOURCE)
        self.assertEqual(packet['delta'], {'add': [], 'replace': ['batch_apply']})
        before, after = form.decode(source), form.decode(changed)
        self.assertEqual(digest(before), BASE)
        self.assertEqual(digest(after), TARGET)
        self.assertEqual([name for name in before['functions'] if before['functions'][name] != after['functions'][name]], ['batch_apply'])
        for key in ('schema', 'records', 'lists', 'variants', 'entry'):
            self.assertEqual(before[key], after[key])
        start = source.index(b'= let size =') + 2
        end = source.index(b';\n  fn batch_main')
        fragment = (DATA / 'PerSku.fragment.bagaev').read_bytes()
        self.assertEqual(changed, source[:start] + fragment[fragment.index(b'let size ='):fragment.rindex(b';')] + source[end:])

    def test_history_roundtrip_without_execution(self):
        source, packet, changed = self.change()
        first = revisions.initialize(source, source_sha256=sha(source), program_sha256=BASE)
        second = revisions.append(first, changed, expected_package_sha256=revisions.package_digest(first),
            expected_head=first['head'], source_sha256=SOURCE, program_sha256=TARGET)
        portable = revisions.loads(revisions.canonical(second))
        self.assertEqual(revisions.checkout(portable, portable['head']), changed)
        self.assertEqual(revisions.checkout(portable, first['head']), source)
        self.assertFalse(portable['semantic_check'])
        self.assertFalse(portable['execution_admission'])
        self.assertEqual(len(first['revisions']), 1)

if __name__ == '__main__':
    unittest.main()
