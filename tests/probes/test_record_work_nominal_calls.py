"""Work analysis stays useful across scalar-record helper extraction."""
from pathlib import Path
import copy
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work import analyze

RECORDS={'Item':{'amount':'Int64'},'Other':{'amount':'Int64'}}
LISTS={'Items':{'element':'Item','capacity':16},'Others':{'element':'Other','capacity':16}}
ARG={'items':{'type':'Items','items':16}}
AT=['records.at',['arg','items'],['int',0]]
FUNCTIONS={'amount':{'params':[['item','Item']],'result':'Int64','body':['field',['arg','item'],'amount']},
           'record_id':{'params':[['item','Item']],'result':'Item','body':['arg','item']},
           'list_id':{'params':[['items','Items']],'result':'Items','body':['arg','items']}}


class NominalCalls(unittest.TestCase):
    def inspect(self,body,functions=FUNCTIONS,args=ARG,records=RECORDS):
        return analyze(body,args,functions,records,LISTS)

    def test_helper_extraction_frozen_work(self):
        body=['loop',16,'i','sum',['int',0],
              ['if',['lt',['use','i'],['records.len',['arg','items']]],
               ['add',['use','sum'],['call','amount',['records.at',['arg','items'],['use','i']]]],['use','sum']]]
        for n in (0,2,16):
            r=self.inspect(body,args={'items':{'type':'Items','items':n}})
            self.assertEqual(r['upper_work'],210)
            self.assertFalse(r['execution_admission'])
            self.assertFalse(r['semantic_check'])

    def test_record_and_list_results_preserve_kind(self):
        self.assertEqual(self.inspect(['field',['call','record_id',AT],'amount'])['upper_work'],6)
        self.assertEqual(self.inspect(['records.len',['call','list_id',['arg','items']]])['upper_work'],4)
        self.assertEqual(self.inspect(['call','amount',['call','record_id',AT]])['upper_work'],8)

    def test_wrong_nominal_argument_and_result_refuse(self):
        for slot in ('params','result'):
            f=copy.deepcopy(FUNCTIONS)
            if slot=='params':f['record_id'][slot]=[['item','Other']]
            else:f['record_id'][slot]='Other'
            r=self.inspect(['call','record_id',AT],functions=f)
            self.assertEqual(r['status'],'UNKNOWN')
            self.assertNotIn('upper_work',r)
        f=copy.deepcopy(FUNCTIONS);f['list_id']['result']='Others'
        self.assertEqual(self.inspect(['call','list_id',['arg','items']],functions=f)['status'],'UNKNOWN')

    def test_invalid_metadata_and_cycles_refuse(self):
        for kind in ('Text','Missing',[]):
            records={'Item':{'amount':kind}}
            self.assertEqual(self.inspect(['call','amount',AT],records=records)['status'],'UNKNOWN')
        f=copy.deepcopy(FUNCTIONS);f['record_id']['body']=['call','record_id',['arg','item']]
        r=self.inspect(['call','record_id',AT],functions=f)
        self.assertEqual(r['reason'],'call-cycle')
        self.assertEqual(r['location'],{'function':'record_id','pointer':''})

    def test_nominal_loop_accumulator_still_refuses(self):
        r=self.inspect(['loop',0,'i','acc',['call','record_id',AT],['use','acc']])
        self.assertEqual(r['reason'],'loop-invariant')

    def test_input_maps_remain_unchanged(self):
        before=copy.deepcopy((RECORDS,LISTS,ARG,FUNCTIONS))
        self.inspect(['call','amount',AT])
        self.assertEqual((RECORDS,LISTS,ARG,FUNCTIONS),before)


if __name__=='__main__':
    unittest.main()
