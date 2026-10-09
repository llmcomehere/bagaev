"""Ordinary application baseline and prior capture comparison, no bagaev run."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from active_total_reference import total
D=ROOT/'examples/probes/record-active-total'
class Baseline(unittest.TestCase):
    def test_literal_ordered_overflow(self):
        raw=(D/'baseline-cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'74b6aba91d772683fcd8da92d3eb8fd34283e2cbd4d36200c8f4031a8ae38587')
        for c in json.loads(raw):
            before=copy.deepcopy(c['items'])
            self.assertEqual(total(c['items'],active_only=c['active_only']),c['expected']);self.assertEqual(c['items'],before)
    def test_prior_application_observations(self):
        cases=json.loads((D/'cases.json').read_bytes())+json.loads((D/'boundary-cases.json').read_bytes());self.assertEqual(len(cases),18)
        for c in cases:
            items=c['arguments'][0];before=copy.deepcopy(items);r=total(items,active_only=c['side']=='after')
            self.assertEqual({k:r[k] for k in ('status','value')},{k:c['expected'][k] for k in ('status','value')})
            self.assertEqual(r['failure_index'],1 if r['status']=='integer-overflow' else None);self.assertEqual(items,before)
    def test_strict_whole_input_validation(self):
        good={'amount':1,'active':True}
        bad=[None,{},[good]*17,[{'amount':True,'active':False}],[{'amount':1,'active':1}],[{'amount':2**63,'active':False}],[{'amount':-(2**63)-1,'active':False}],[{'amount':1}],[dict(good,extra=0)],[good,None]]
        for items in bad:
            before=copy.deepcopy(items)
            with self.assertRaisesRegex(ValueError,'invalid-input'):total(items,active_only=True)
            self.assertEqual(items,before)
        for flag in (0,1,None,'true'):
            with self.assertRaises(ValueError):total([],active_only=flag)
        # A later invalid inactive record is rejected even if an earlier pair overflows.
        items=[{'amount':2**63-1,'active':True},good,{'amount':True,'active':False}]
        with self.assertRaises(ValueError):total(items,active_only=True)
    def test_modes_and_limits(self):
        items=[{'amount':-(2**63),'active':False},{'amount':2**63-1,'active':True}]
        self.assertEqual(total(items,active_only=False),{'status':'success','value':-1,'failure_index':None})
        self.assertEqual(total(items,active_only=True),{'status':'success','value':2**63-1,'failure_index':None})
        self.assertEqual(total([],active_only=False)['value'],0)
if __name__=='__main__':unittest.main()
