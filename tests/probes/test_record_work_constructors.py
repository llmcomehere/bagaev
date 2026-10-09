"""Scalar construction preserves declared identity without expanding opaque shapes."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work import analyze

class Constructors(unittest.TestCase):
    def test_direct_and_helper_frozen_work(self):
        records={'Item':{'amount':'Int64'}}
        value=['record','Item',['int',7]]
        self.assertEqual(analyze(['field',value,'amount'],{},records=records)['upper_work'],3)
        functions={'make':{'params':[['n','Int64']],'result':'Item','body':['record','Item',['arg','n']]}}
        r=analyze(['field',['call','make',['int',7]],'amount'],{},functions,records)
        self.assertEqual(r['upper_work'],5)
        self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])

    def test_sorted_field_kinds_not_map_insertion_order(self):
        records={'Flag':{'enabled':'Bool','amount':'Int64'}}
        body=['field',['record','Flag',['int',7],['bool',True]],'enabled']
        self.assertEqual(analyze(body,{},records=records)['upper_work'],4)
        body[1][2:]=[['bool',True],['int',7]]
        self.assertEqual(analyze(body,{},records=records)['status'],'UNKNOWN')

    def test_bad_arity_kind_and_nominal_identity(self):
        records={'Item':{'amount':'Int64'},'Other':{'amount':'Int64'}}
        for body in (['record','Item'],['record','Item',['int',1],['int',2]],['record','Item',['bool',True]]):
            self.assertEqual(analyze(body,{},records=records)['status'],'UNKNOWN')
        functions={'make':{'params':[],'result':'Other','body':['record','Item',['int',1]]}}
        self.assertEqual(analyze(['call','make'],{},functions,records)['status'],'UNKNOWN')

    def test_opaque_cost_only_compatibility(self):
        body=['record','Report',['text','x']]
        for records in ({},{'Report':{'value':'Text'}}):
            self.assertEqual(analyze(body,{},records=records)['upper_work'],3)
            self.assertEqual(analyze(['field',body,'value'],{},records=records)['status'],'UNKNOWN')
        self.assertEqual(analyze(['record','Item',['int',7]],{})['upper_work'],2)

if __name__=='__main__':unittest.main()
