"""A conditional bound is inapplicable when actual inputs violate its maxima."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work import analyze

class Assumptions(unittest.TestCase):
    def test_applicability_controls(self):
        cases=json.loads((ROOT/'examples/probes/record-work-assumptions/cases.json').read_bytes())
        self.assertEqual(hashlib.sha256((ROOT/'examples/probes/record-work-assumptions/cases.json').read_bytes()).hexdigest(),'3bc18a861694447d4e27b75718f0dfad9cff33ba1b29909606472dcf8ad4d410')
        self.assertEqual(len(cases),2)
        for c in cases:
            low=analyze(c['body'],c['violating_bounds'])
            good=analyze(c['body'],c['applicable_bounds'])
            self.assertEqual(low['upper_work'],c['violating_upper'])
            self.assertEqual(good['upper_work'],c['applicable_upper'])
            self.assertLess(low['upper_work'],c['prior_full_observation']['work'])
            self.assertGreaterEqual(good['upper_work'],c['prior_full_observation']['work'])
            self.assertFalse(low['execution_admission']);self.assertFalse(low['semantic_check'])
            for arg,shape in zip(c['arguments'],c['applicable_bounds'].values()):
                actual=sum(len(s.encode('utf-8')) for s in arg) if isinstance(arg,list) else len(arg.encode('utf-8'))
                self.assertGreater(actual,0);self.assertLessEqual(actual,shape['bytes'])
    def test_prior_observation_provenance(self):
        cases=json.loads((ROOT/'examples/probes/record-work-assumptions/cases.json').read_bytes())
        for c,directory in zip(cases,['record-work-text-comparison','record-work-text-index']):
            prior=json.loads((ROOT/'examples/probes'/directory/'cases.json').read_bytes())
            p=next(x for x in prior if x['name']==c['name'])
            self.assertEqual(p['body'],c['body']);self.assertEqual(p['arguments'],c['arguments'])
            self.assertEqual(p['expected'],c['prior_full_observation'])

if __name__=='__main__':unittest.main()
