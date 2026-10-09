"""TextList indexing preserves a conservative Text byte shape, not index safety."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work import analyze

class TextIndex(unittest.TestCase):
    def test_frozen_cases(self):
        raw=(ROOT/'examples/probes/record-work-text-index/cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'3704a40ccaa27d95b2d5e678f379ff4a6b54016c0d5cc4eae2ec45d54319af00')
        cases=json.loads(raw);self.assertEqual(len(cases),5)
        for c in cases:
            r=analyze(c['body'],c['bounds'],c['functions'])
            self.assertEqual(r['status'],'SUPPORTED');self.assertEqual(r['upper_work'],c['upper'])
            self.assertLessEqual(c['expected']['work'],r['upper_work']);self.assertFalse(r['execution_admission'])
        self.assertEqual(cases[1]['expected']['reason'],'RR_INDEX')
        self.assertEqual(cases[2]['expected']['reason'],'RR_INDEX')
    def test_item_maximum_not_total_maximum(self):
        body=['text.eq',['list.at',['arg','xs'],['int',0]],['text','']]
        for n,b,expected in [(0,0,5),(2,17,22),(64,4096,1029)]:
            r=analyze(body,{'xs':{'type':'TextList','items':n,'bytes':b}})
            self.assertEqual(r['upper_work'],expected)
            self.assertFalse(r['semantic_check'])
    def test_types_and_arity(self):
        for x in (['list.at',['text','x'],['int',0]],['list.at',['arg','xs'],['bool',False]],['list.at',['arg','xs']]):
            self.assertEqual(analyze(x,{'xs':{'type':'TextList','items':1,'bytes':1}})['status'],'UNKNOWN')
    def test_index_expression_cost_and_unknown_location(self):
        bounds={'xs':{'type':'TextList','items':1,'bytes':1}}
        self.assertEqual(analyze(['list.at',['arg','xs'],['add',['int',0],['int',1]]],bounds)['upper_work'],5)
        r=analyze(['list.at',['arg','xs'],['unsupported']],bounds)
        self.assertEqual(r['status'],'UNKNOWN');self.assertEqual(r['location']['pointer'],'/2')

if __name__=='__main__':unittest.main()
