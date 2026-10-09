"""Full-capacity data controls and detached source change; no evaluator launch."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
import bagaev_record_wide_draft as draft
from bagaev_record_work_observation import observe_source
from bagaev_record_draft import digest
D=ROOT/'examples/probes/record-active-total';RAW=(D/'boundary-cases.json').read_bytes();CASES=json.loads(RAW)
class Boundary(unittest.TestCase):
    def test_frozen_capacity_and_cost(self):
        self.assertEqual(hashlib.sha256(RAW).hexdigest(),'0ecdebd3b5c022b3ebbcdf6152ff9afddd05d03697b400d3d434b03915a2a618')
        self.assertEqual([c['expected']['value'] for c in CASES],[120,120,120,56,None,0])
        self.assertEqual([c['expected']['work'] for c in CASES],[178,258,178,218,24,178])
        for c in CASES:
            self.assertEqual(len(c['arguments'][0]),16)
            self.assertEqual(draft.form.decode(c['source']),c['program'])
            o=observe_source(c['source'],c['bounds'],c['arguments'],program_sha256=digest(c['program']))
            self.assertEqual(o['argument_dimensions']['status'],'WITHIN');self.assertEqual(o['work_bound']['upper_work'],c['upper'])
    def test_invalid_shapes_and_exceeded_bound(self):
        c=CASES[1];args=c['arguments'];bad=[]
        a=copy.deepcopy(args);a[0].append(copy.deepcopy(a[0][0]));bad.append(a)
        for field,value in [('amount',True),('active',1),('extra',0)]:
            a=copy.deepcopy(args);a[0][0][field]=value;bad.append(a)
        a=copy.deepcopy(args);del a[0][0]['active'];bad.append(a)
        for a in bad:
            o=observe_source(c['source'],c['bounds'],a,program_sha256=digest(c['program']))
            self.assertEqual(o['argument_dimensions']['status'],'INVALID_ARGUMENT');self.assertFalse(o['execution_admission'])
        o=observe_source(c['source'],{'items':{'type':'Items','items':15}},args,program_sha256=digest(c['program']))
        self.assertEqual(o['argument_dimensions']['status'],'EXCEEDS');self.assertFalse(o['execution_admission'])
    def test_detached_draft_scope_and_stale_pins(self):
        a,b=CASES[:2];base=digest(a['program']);target=digest(b['program'])
        r=draft.draft(a['source'],b['source'],base_sha256=base,target_sha256=target)
        self.assertEqual(r['delta'],{'add':[],'replace':['main']});self.assertEqual(r['program'],b['program'])
        self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])
        for k in ('schema','records','lists','variants','entry'):self.assertEqual(a['program'][k],b['program'][k])
        for x,y in [('0'*64,target),(base,'0'*64)]:
            with self.assertRaises(draft.DraftError):draft.draft(a['source'],b['source'],base_sha256=x,target_sha256=y)
if __name__=='__main__':unittest.main()
