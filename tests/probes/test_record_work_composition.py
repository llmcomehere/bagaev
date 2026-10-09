"""Frozen compositional work regressions; data-only, without native execution."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work import analyze

class Composition(unittest.TestCase):
    def test_frozen_compositions(self):
        raw=(ROOT/'examples/probes/record-work-composition/cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'3d1426dd50b1053db953d97728f95ed7e1971a2fb118c246aaf3a8d188648043')
        cases=json.loads(raw);self.assertEqual(len(cases),8)
        for c in cases:
            with self.subTest(name=c['name']):
                r=analyze(c['body'],c['bounds'],c['functions'])
                self.assertEqual(r['status'],'SUPPORTED')
                self.assertEqual(r['upper_work'],c['upper'])
                self.assertLessEqual(c['expected']['work'],r['upper_work'])
                self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])
                self.assertTrue(r['requires_checked_program'])
        overflow=next(c for c in cases if c['name']=='early-overflow')
        self.assertEqual(overflow['expected']['reason'],'RR_OVERFLOW')
        self.assertEqual(overflow['expected']['location'],'/program/functions/main/body/1')
        self.assertEqual(overflow['expected']['work'],4)
        self.assertEqual(overflow['upper'],3007)

if __name__=='__main__':unittest.main()
