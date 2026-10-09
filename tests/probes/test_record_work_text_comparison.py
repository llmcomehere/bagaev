"""Conditional byte-bound Text comparisons; no native execution."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work import analyze

class TextComparison(unittest.TestCase):
    def test_frozen_cases(self):
        raw=(ROOT/'examples/probes/record-work-text-comparison/cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'519dcb28b0831f509cea61f3326bff4c2aba33119392f6814333fb7322c7921d')
        cases=json.loads(raw);self.assertEqual(len(cases),6)
        for c in cases:
            r=analyze(c['body'],c['bounds'],c['functions'])
            self.assertEqual(r['status'],'SUPPORTED');self.assertEqual(r['upper_work'],c['upper'])
            self.assertLessEqual(c['expected']['work'],r['upper_work'])
            self.assertFalse(r['execution_admission']);self.assertFalse(r['semantic_check'])
    def test_exact_shape_and_byte_bounds(self):
        for n in (0,1,1024):self.assertEqual(analyze(['arg','x'],{'x':{'type':'Text','bytes':n}})['upper_work'],1)
        for n in (-1,1025,True,'1',None):self.assertEqual(analyze(['arg','x'],{'x':{'type':'Text','bytes':n}})['status'],'UNKNOWN')
        for s in ({'type':'Text'},{'type':'Text','bytes':0,'items':0}):self.assertEqual(analyze(['arg','x'],{'x':s})['status'],'UNKNOWN')
    def test_wrong_types_and_old_unknowns(self):
        for x in (['text.eq',['int',1],['text','x']],['text.lt',['text','x'],['bool',True]],['eq',['text','x'],['text','x']],['text.bytes',['text','x']],['text.eq',['text','x']]):
            self.assertEqual(analyze(x,{})['status'],'UNKNOWN')
    def test_branch_maximum_and_loop_invariant(self):
        branch=['if',['arg','b'],['text','é'],['text','abc']]
        r=analyze(['text.eq',branch,['text','a']],{'b':{'type':'Bool'}})
        self.assertEqual(r['upper_work'],13)
        loop=['loop',2,'i','a',['arg','x'],['arg','x']]
        r=analyze(['text.eq',loop,['text','é']],{'x':{'type':'Text','bytes':2}})
        self.assertEqual(r['upper_work'],12)
    def test_bulk_refusal_is_below_limit(self):
        self.assertEqual(2+32*(3+2048),65634)
        self.assertEqual(2+31*(3+2048)+3,63586)
        self.assertGreater(63586+2048,65536)

if __name__=='__main__':unittest.main()
