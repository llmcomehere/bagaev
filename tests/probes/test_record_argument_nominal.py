"""Finite nominal argument dimensions; no evaluator or admission."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_argument_dimensions import observe
from bagaev_record_work_observation import observe_source
from bagaev_record_draft import digest
from bagaev_record_wide_form import decode
RECORDS={'Item':{'amount':'Int64','active':'Bool'}}
LISTS={'Items':{'element':'Item','capacity':2}}
VALUE={'amount':3,'active':True}
def run(value,maximum=2,records=None,lists=None):
    return observe({'items':{'type':'Items','items':maximum}},{'items':value},records=RECORDS if records is None else records,lists=LISTS if lists is None else lists)
class NominalDimensions(unittest.TestCase):
    def test_applicability_and_identity(self):
        for value,maximum,status in [([],0,'WITHIN'),([VALUE],0,'EXCEEDS'),([VALUE,VALUE],2,'WITHIN')]:
            r=run(value,maximum);self.assertEqual(r['status'],status)
            self.assertEqual(r['dimensions'],[{'name':'items','type':'Items','element':'Item','capacity':2,'items':len(value),'within_declared_bounds':status=='WITHIN'}])
            raw=json.dumps({'records':RECORDS,'lists':LISTS},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
            self.assertEqual(r['argument_declarations_sha256'],hashlib.sha256(raw).hexdigest())
            self.assertFalse(r['execution_admission']);self.assertFalse(r['semantic_check']);self.assertTrue(r['requires_checked_program'])
    def test_capacity_and_exact_records(self):
        for value in [[VALUE]*3,{},[{}],[dict(VALUE,extra=0)],[{'amount':3}]]:
            r=run(value);self.assertEqual(r['status'],'INVALID_ARGUMENT');self.assertIsNone(r['within_declared_bounds']);self.assertNotIn('dimensions',r)
    def test_scalar_limits(self):
        for amount in [-(2**63),2**63-1]:self.assertEqual(run([dict(VALUE,amount=amount)])['status'],'WITHIN')
        for value in [dict(VALUE,amount=True),dict(VALUE,amount=2**63),dict(VALUE,active=1),dict(VALUE,amount=3.0)]:
            self.assertEqual(run([value])['status'],'INVALID_ARGUMENT')
    def test_unsupported_declarations(self):
        for records,lists in [({},LISTS),({'Item':{'amount':'Text'}},LISTS),({'Item':{'nested':'Item'}},LISTS),(RECORDS,{'Items':{'element':'Item','capacity':17}}),(RECORDS,{'Items':{'element':'Item','capacity':True}})]:
            self.assertEqual(run([],records=records,lists=lists)['status'],'UNKNOWN')
        for records in [[],{'Text':{'amount':'Int64'}},{'Items':{'amount':'Int64'}}, {1:{'amount':'Int64'}}]:
            self.assertEqual(run([],records=records)['status'],'UNKNOWN')
        self.assertEqual(observe({'x':{'type':'Item'}},{'x':VALUE},records=RECORDS,lists=LISTS)['status'],'UNKNOWN')
    def test_shape_precedence(self):
        r=observe({'a':{'type':'Int64'},'z':{'type':'Missing','items':0}},{'a':False,'z':[]},records=RECORDS,lists=LISTS)
        self.assertEqual(r['status'],'UNKNOWN');self.assertEqual(r['argument'],'z')
    def test_source_binding(self):
        s='bagaev record-form/5; program { record Item { amount: Int64, active: Bool }; list Items of Item capacity 2; entry main; fn main(items: Items) -> Int64 = records.len(items); }'
        r=observe_source(s,{'items':{'type':'Items','items':1}},[[VALUE,VALUE]],program_sha256=digest(decode(s)))
        self.assertEqual(r['argument_dimensions']['status'],'EXCEEDS');self.assertEqual(r['work_bound']['upper_work'],2);self.assertFalse(r['execution_admission'])
    def test_input_preservation_and_zero_capacity(self):
        value=[dict(VALUE)];old=copy.deepcopy((value,RECORDS,LISTS));run(value)
        self.assertEqual((value,RECORDS,LISTS),old)
        self.assertEqual(run([],0,lists={'Items':{'element':'Item','capacity':0}})['status'],'WITHIN')
        self.assertEqual(run([VALUE],0,lists={'Items':{'element':'Item','capacity':0}})['status'],'INVALID_ARGUMENT')

if __name__=='__main__':unittest.main()
