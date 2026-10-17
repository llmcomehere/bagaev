"""Frozen literal cases; exact scalar types, input preservation, detached outputs."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from catalog_date_edit_reference import evaluate

def exact(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b

def containers(value):
    if type(value) is dict:
        return {id(value)}.union(*(containers(v) for v in value.values()))
    if type(value) is list:
        return {id(value)}.union(*(containers(v) for v in value))
    return set()

class DateEdit(unittest.TestCase):
    def test_literal_cases(self):
        raw=(ROOT/'examples/probes/catalog-date-edit/cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'1b5f3b4cf3e1499cbf2d60c4e30a454086db27d2463dec9cf8968e2231ac13b6')
        oracle=json.loads(raw)
        self.assertEqual(len(oracle['cases']),33)
        for case in oracle['cases']:
            with self.subTest(case=case['id']):
                request=copy.deepcopy(case['request'] if 'request' in case else {
                    'interface':'catalog-date-edit/1','state':oracle['states'][case['state']],
                    'entry_id':case['target'],'action':case['action']})
                before=copy.deepcopy(request)
                expected=({'kind':'refusal','reason':case['reason']} if 'reason' in case else
                          {'kind':'success','state':oracle['states'][case['output_state']],'entry_ids':case['view']})
                result=evaluate(request)
                self.assertTrue(exact(result,expected),(result,expected))
                self.assertTrue(exact(request,before))
                self.assertFalse(containers(request)&containers(result))

if __name__=='__main__':unittest.main()
