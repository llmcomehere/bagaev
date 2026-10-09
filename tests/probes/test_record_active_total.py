"""Data regressions for the active-total change; no runtime launch."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_wide_form import decode
from bagaev_record_work_observation import observe_source
from bagaev_record_draft import digest
from bagaev_record_capture_compare import compare_captures
D=ROOT/'examples/probes/record-active-total';RAW=(D/'cases.json').read_bytes();CASES=json.loads(RAW)
class ActiveTotal(unittest.TestCase):
    def test_frozen_sources_and_observations(self):
        self.assertEqual(hashlib.sha256(RAW).hexdigest(),'920bac1aa85cd67fb6b2e900886ff629136631da2fdec919101004ca074597d9')
        self.assertEqual(len(CASES),12)
        for c in CASES:
            with self.subTest(c['name']):
                self.assertEqual(decode(c['source']),c['program'])
                self.assertEqual((D/('All.bagaev' if c['side']=='before' else 'Active.bagaev')).read_text(),c['source'])
                o=observe_source(c['source'],c['bounds'],c['arguments'],program_sha256=digest(c['program']))
                self.assertEqual(o['argument_dimensions']['status'],'WITHIN')
                self.assertEqual(o['work_bound']['upper_work'],c['upper'])
                self.assertLessEqual(c['expected']['work'],c['upper']);self.assertFalse(o['execution_admission'])
    def test_changed_values_and_lazy_overflow(self):
        self.assertEqual([c['expected']['value'] for c in CASES],[0,0,7,7,7,4,1,4,None,2**63-1,None,None])
        self.assertEqual([c['expected']['work'] for c in CASES],[98,98,108,118,108,113,108,113,24,113,24,34])
        self.assertEqual(CASES[8]['expected']['reason'],'RR_OVERFLOW')
        self.assertEqual(CASES[9]['expected']['status'],'success')
        for i,path in [(10,'/program/functions/main/body/5/2'),(11,'/program/functions/main/body/5/2/2')]:self.assertEqual(CASES[i]['expected']['location'],path)
    def test_supplied_comparison_axes(self):
        expected=[(True,True,None,0),(False,True,None,10),(False,False,None,5),(False,False,None,5),(False,None,None,89),(False,None,False,10)]
        for i,axes in zip(range(0,12,2),expected):
            a,b=CASES[i:i+2];base=digest(a['program']);target=digest(b['program']);pin=digest(a['arguments'])
            r=compare_captures({'program_sha256':base,'arguments_sha256':pin,'result':a['expected']},{'program_sha256':target,'arguments_sha256':pin,'result':b['expected']},base_sha256=base,target_sha256=target,arguments_sha256=pin)
            self.assertEqual(tuple(r[k] for k in ('same_result','same_success_value','same_failure','work_delta')),axes)
            self.assertFalse(r['capture_authentication']);self.assertFalse(r['execution_admission'])
if __name__=='__main__':unittest.main()
