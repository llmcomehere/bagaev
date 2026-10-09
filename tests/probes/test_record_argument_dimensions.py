"""Data-only actual-dimension observations, explicitly not admission."""
from pathlib import Path
import copy,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_argument_dimensions import observe

class Dimensions(unittest.TestCase):
    def one(self,shape,value):return observe({'x':shape},{'x':value})
    def test_text_assumptions(self):
        for maximum,status in [(0,'EXCEEDS'),(2,'WITHIN')]:
            r=self.one({'type':'Text','bytes':maximum},'é')
            self.assertEqual(r['status'],status);self.assertEqual(r['dimensions'][0]['bytes'],2)
            self.assertEqual(r['dimensions'][0]['scalars'],1)
            self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission']);self.assertTrue(r['requires_checked_program'])
    def test_list_assumptions(self):
        for items,maximum,status in [(2,0,'EXCEEDS'),(1,5,'EXCEEDS'),(2,5,'WITHIN')]:
            r=self.one({'type':'TextList','items':items,'bytes':maximum},['é','abc'])
            self.assertEqual(r['status'],status);self.assertEqual(r['dimensions'][0]['bytes'],5)
            self.assertEqual(r['dimensions'][0]['items'],2)
    def test_zero_and_unicode_boundaries(self):
        for shape,value in [({'type':'Text','bytes':0},''),({'type':'TextList','items':0,'bytes':0},[]),({'type':'Text','bytes':1024},'😀'*256)]:
            self.assertEqual(self.one(shape,value)['status'],'WITHIN')
        for value in ['a'*257,'\ud800',1,None]:
            r=self.one({'type':'Text','bytes':1024},value)
            self.assertEqual(r['status'],'INVALID_ARGUMENT');self.assertIsNone(r['within_declared_bounds'])
    def test_scalar_types_and_limits(self):
        for value in [-(2**63),2**63-1,0]:self.assertEqual(self.one({'type':'Int64'},value)['status'],'WITHIN')
        for value in [True,2**63,-(2**63)-1,1.0]:self.assertEqual(self.one({'type':'Int64'},value)['status'],'INVALID_ARGUMENT')
        for value in [True,False]:self.assertEqual(self.one({'type':'Bool'},value)['status'],'WITHIN')
        self.assertEqual(self.one({'type':'Bool'},0)['status'],'INVALID_ARGUMENT')
    def test_list_profile_limits(self):
        shape={'type':'TextList','items':64,'bytes':4096}
        for value in [['']*65,['😀'*256]*5,['a'*257],[False],{}]:
            self.assertEqual(self.one(shape,value)['status'],'INVALID_ARGUMENT')
        self.assertEqual(self.one(shape,['😀'*256]*4)['status'],'WITHIN')
    def test_unknown_is_not_applicability(self):
        for shape in [{'type':'Items','items':1},{'type':'Text','bytes':True},{'type':'Text','bytes':-1},{'type':'Text','bytes':0,'extra':0},None]:
            r=self.one(shape,'');self.assertEqual(r['status'],'UNKNOWN');self.assertIsNone(r['within_declared_bounds'])
        for bounds,args in [({}, {'x':0}),({'x':{'type':'Int64'}},{}),({str(i):{'type':'Int64'} for i in range(9)},{str(i):0 for i in range(9)}),(None,{})]:
            self.assertEqual(observe(bounds,args)['status'],'UNKNOWN')
    def test_order_and_immutability(self):
        bounds={'b':{'type':'Text','bytes':2},'a':{'type':'Bool'}};args={'b':'é','a':True};old=copy.deepcopy((bounds,args))
        r=observe(bounds,args);q=observe(dict(reversed(list(bounds.items()))),dict(reversed(list(args.items()))))
        self.assertEqual(r,q);self.assertEqual((bounds,args),old)
        self.assertEqual([d['name'] for d in r['dimensions']],['a','b'])
        self.assertNotIn('values',r)
    def test_precondition_controls(self):
        import json
        cases=json.loads((ROOT/'examples/probes/record-work-assumptions/cases.json').read_bytes())
        for c in cases:
            args=dict(zip(c['applicable_bounds'],c['arguments']))
            self.assertEqual(observe(c['violating_bounds'],args)['status'],'EXCEEDS')
            self.assertEqual(observe(c['applicable_bounds'],args)['status'],'WITHIN')

if __name__=='__main__':unittest.main()
