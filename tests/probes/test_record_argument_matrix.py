"""Complete finite item-count/maxima matrix, data observation only."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_argument_dimensions import observe
E=json.loads((ROOT/'examples/probes/record-argument-matrix/expected.json').read_bytes())
def run(values,maximum):
    return observe({'items':{'type':'Items','items':maximum}},{'items':values},records=E['records'],lists=E['lists'])
class Matrix(unittest.TestCase):
    def test_all_count_maximum_pairs(self):
        rows=[]
        for n in range(17):
            values=[{'amount':i,'active':i%2==0} for i in range(n)]
            for maximum in range(17):
                r=run(values,maximum);rows.append(r)
                self.assertEqual(r['status'],'WITHIN' if n<=maximum else 'EXCEEDS')
                self.assertFalse(r['execution_admission']);self.assertFalse(r['semantic_check'])
        self.assertEqual(len(rows),E['cases']);self.assertEqual(sum(r['status']=='WITHIN' for r in rows),E['within'])
        self.assertEqual(sum(r['status']=='EXCEEDS' for r in rows),E['exceeds'])
        raw=json.dumps(rows,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),E['complete_observations_sha256'])
    def test_capacity_is_not_a_declared_maximum(self):
        value={'amount':1,'active':False}
        for maximum in range(17):
            r=run([value]*17,maximum)
            self.assertEqual(r,{'schema':'bagaev-record-argument-dimensions/1','semantic_check':False,'execution_admission':False,'requires_checked_program':True,'status':'INVALID_ARGUMENT','reason':'record-list-value','argument':'items','within_declared_bounds':None})
        for maximum in [-1,17,True,1.0]:self.assertEqual(run([],maximum)['status'],'UNKNOWN')
    def test_bad_record_never_becomes_exceeds(self):
        for value in [{'amount':True,'active':False},{'amount':1,'active':0},{'amount':2**63,'active':True},{'amount':0},{'amount':0,'active':True,'other':0}]:
            r=run([value],0)
            self.assertEqual(r['status'],'INVALID_ARGUMENT');self.assertEqual(r['reason'],'record-value');self.assertIsNone(r['within_declared_bounds']);self.assertNotIn('dimensions',r)

if __name__=='__main__':unittest.main()
