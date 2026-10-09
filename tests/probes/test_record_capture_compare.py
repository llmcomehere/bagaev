"""Supplied scalar capture data comparisons, not authenticated runtime evidence."""
from pathlib import Path
import copy,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_capture_compare import compare_captures
from bagaev_record_draft import digest,DraftError
P=ROOT/'examples/probes'
HELPER=json.loads((P/'record-work-helper-edit/cases.json').read_bytes())
BRANCH=json.loads((P/'record-branch-edit/cases.json').read_bytes())
def pair(a,b,base,target,args):
    pin=digest(args)
    return ({'program_sha256':base,'arguments_sha256':pin,'result':a},{'program_sha256':target,'arguments_sha256':pin,'result':b},dict(base_sha256=base,target_sha256=target,arguments_sha256=pin))
def branch(i):
    a,b=BRANCH[i:i+2];return pair(a['expected'],b['expected'],digest(a['program']),digest(b['program']),a['arguments'])
class CaptureCompare(unittest.TestCase):
    def test_helper_values_and_work_are_separate(self):
        for c,delta in zip(HELPER['cases'],[0,4,32]):
            a,b,p=pair(c['before'],c['after'],HELPER['base'],HELPER['target'],c['arguments']);r=compare_captures(a,b,**p)
            self.assertTrue(r['same_success_value']);self.assertEqual(r['same_result'],delta==0);self.assertEqual(r['work_delta'],delta);self.assertIsNone(r['same_failure'])
    def test_changed_branch(self):
        for i,same in [(0,True),(2,False)]:
            a,b,p=branch(i);r=compare_captures(a,b,**p)
            self.assertEqual(r['same_result'],same);self.assertEqual(r['same_success_value'],same);self.assertEqual(r['work_delta'],0)
    def test_failure_is_separate_from_value(self):
        a,b,p=branch(4);r=compare_captures(a,b,**p)
        self.assertTrue(r['same_failure']);self.assertTrue(r['same_result']);self.assertIsNone(r['same_success_value'])
        b=copy.deepcopy(b);b['result']['location']+='/1';self.assertFalse(compare_captures(a,b,**p)['same_failure'])
    def test_stale_and_malformed_pins(self):
        a,b,p=branch(0)
        for key in p:
            q=dict(p);q[key]='bad'
            with self.assertRaises(DraftError):compare_captures(a,b,**q)
        for obj,key in [(a,'program_sha256'),(a,'arguments_sha256'),(b,'program_sha256'),(b,'arguments_sha256')]:
            old=obj[key];obj[key]='0'*64
            with self.assertRaises(DraftError):compare_captures(a,b,**p)
            obj[key]=old
    def test_result_shape_refusals(self):
        a,b,p=branch(0)
        for key,value in [('schema','other'),('status',[]),('value',True),('value',2**63),('value_type','Json'),('work',True),('work',65537),('reason','RR_OVERFLOW'),('location','/program/x')]:
            c=copy.deepcopy(a);c['result'][key]=value
            with self.assertRaises(DraftError):compare_captures(c,b,**p)
        for key in a['result']:
            c=copy.deepcopy(a);del c['result'][key]
            with self.assertRaises(DraftError):compare_captures(c,b,**p)
        a,b,p=branch(4)
        for key,value in [('value',0),('reason','RR_INDEX'),('location','x'),('location','/program/\ud800')]:
            c=copy.deepcopy(a);c['result'][key]=value
            with self.assertRaises(DraftError):compare_captures(c,b,**p)
    def test_typed_values_and_mixed_outcomes(self):
        a,b,p=branch(0);b=copy.deepcopy(b);b['result'].update(value_type='Bool',value=True)
        self.assertFalse(compare_captures(a,b,**p)['same_success_value'])
        b['result']=copy.deepcopy(BRANCH[4]['expected']);r=compare_captures(a,b,**p)
        self.assertIsNone(r['same_success_value']);self.assertIsNone(r['same_failure']);self.assertFalse(r['same_result'])
    def test_identity_flags_and_no_mutation(self):
        a,b,p=branch(2);old=copy.deepcopy((a,b,p));r=compare_captures(a,b,**p)
        self.assertEqual(r['before_result_sha256'],digest(a['result']));self.assertEqual(r['after_result_sha256'],digest(b['result']))
        for flag in ('source_check','capture_authentication','equivalence_check','execution_admission'):self.assertIs(r[flag],False)
        self.assertEqual((a,b,p),old)

if __name__=='__main__':unittest.main()
