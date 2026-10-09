"""Data-only regression for a value-preserving extraction crossing the work limit."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work import analyze

class HelperLimit(unittest.TestCase):
    def test_frozen_boundary(self):
        raw=(ROOT/'examples/probes/record-work-helper-limit/cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'49fceb4278cc87ffbb3b0398514858ef1e0440beae4d25a812dae013221fae9c')
        cases=json.loads(raw)
        self.assertEqual(len(cases),2)
        for c in cases:
            r=analyze(c['body'],c['bounds'],c['functions'])
            self.assertEqual(r['status'],'SUPPORTED')
            self.assertEqual(r['upper_work'],c['upper'])
            self.assertEqual(r['fits_work_budget'],c['name']=='direct')
            self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])
        self.assertEqual(cases[0]['expected']['value'],31744)
        self.assertEqual(cases[0]['expected']['work'],64514)
        self.assertEqual(cases[1]['expected']['status'],'work-limit')
        self.assertEqual(cases[1]['expected']['work'],65536)
        self.assertEqual(cases[1]['expected']['location'],'/program/functions/main/body/5/2/2/2/2/2')

    def test_independent_charge_sequence(self):
        cases=json.loads((ROOT/'examples/probes/record-work-helper-limit/cases.json').read_bytes())
        def walk(x,p):
            yield p
            if x[0]=='add':
                yield from walk(x[1],p+'/1')
                yield from walk(x[2],p+'/2')
            elif x[0]=='call':
                yield '/program/functions/one/body'
        old=list(walk(cases[0]['body'][5],'/program/functions/main/body/5'))
        new=list(walk(cases[1]['body'][5],'/program/functions/main/body/5'))
        self.assertEqual(len(old),63);self.assertEqual(len(new),64)
        before_last=2+1023*len(new)
        self.assertEqual(before_last,65474)
        self.assertEqual(new[65536-before_last],cases[1]['expected']['location'])
        self.assertEqual(31*1024,31744)

if __name__=='__main__':unittest.main()
