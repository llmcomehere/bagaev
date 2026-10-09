"""Finite branch-edit counterexample; tests inspect data without execution."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_wide_form import decode
from bagaev_record_draft import digest
from bagaev_record_work_observation import observe_source
from bagaev_record_work_compare import compare
D=ROOT/'examples/probes/record-branch-edit'
E=json.loads((D/'cases.json').read_bytes())
class BranchEdit(unittest.TestCase):
    def test_frozen_identity_and_equal_bounds(self):
        self.assertEqual(hashlib.sha256((D/'cases.json').read_bytes()).hexdigest(),'aba422ff545d8074bb5d6ed02d632fdc973c9b1c1eea304dc4f9816087eeae51')
        for c in E:
            self.assertEqual(decode(c['source']),c['program'])
            r=observe_source(c['source'],c['bounds'],c['arguments'],program_sha256=digest(c['program']))
            self.assertEqual(r['argument_dimensions']['status'],'WITHIN');self.assertEqual(r['work_bound']['upper_work'],5)
            self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])
        a=(D/'Before.bagaev').read_bytes();b=(D/'After.bagaev').read_bytes()
        r=compare(a,b,E[0]['bounds'],base_sha256=digest(E[0]['program']),target_sha256=digest(E[1]['program']))
        self.assertEqual(r['upper_work_delta'],0);self.assertFalse(r['equivalence_check'])
    def test_disabled_case_does_not_establish_equivalence(self):
        a,b,c,d=E[:4]
        self.assertEqual(a['expected'],b['expected']);self.assertEqual(a['expected']['value'],7)
        self.assertEqual((c['expected']['value'],d['expected']['value']),(8,9))
        self.assertEqual(c['expected']['work'],d['expected']['work']);self.assertEqual(c['arguments'],d['arguments'])
    def test_overflow_remains_possible_within_dimensions(self):
        for c in E[4:]:
            self.assertEqual(c['expected'],{'schema':'bagaev-typed-record-result/11','status':'integer-overflow','value_type':None,'value':None,'work':5,'reason':'RR_OVERFLOW','location':'/program/functions/main/body/2'})

if __name__=='__main__':unittest.main()
