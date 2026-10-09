"""Frozen language-order observations crosschecked with an ordinary baseline."""
from pathlib import Path
import hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_wide_form import decode
from bagaev_record_draft import digest
from bagaev_record_work_observation import observe_source
from active_total_reference import total
D=ROOT/'examples/probes/record-active-total';RAW=(D/'order-cases.json').read_bytes();CASES=json.loads(RAW)
class Ordered(unittest.TestCase):
    def test_full_literal_observations(self):
        self.assertEqual(hashlib.sha256(RAW).hexdigest(),'58684fd0b69f7e44973b1c18a36c7738b506ac9e95834d393323b15bbdbb51dc')
        self.assertEqual(len(CASES),8)
        self.assertEqual([c['expected']['work'] for c in CASES],[24,34,24,123,24,34,108,108])
        self.assertEqual([c['expected']['value'] for c in CASES],[None,None,None,2**63-2,None,None,-1,0])
        for c in CASES:
            self.assertEqual(decode(c['source']),c['program'])
            o=observe_source(c['source'],c['bounds'],c['arguments'],program_sha256=digest(c['program']))
            self.assertEqual(o['argument_dimensions']['status'],'WITHIN');self.assertEqual(o['work_bound']['upper_work'],c['upper'])
            self.assertFalse(o['execution_admission'])
    def test_application_projection_and_failure_order(self):
        for c in CASES:
            r=total(c['arguments'][0],active_only=c['side']=='after');e=c['expected']
            self.assertEqual({k:r[k] for k in ('status','value')},{k:e[k] for k in ('status','value')})
            if e['status']=='integer-overflow':
                self.assertEqual(r['failure_index'],1)
                self.assertEqual(e['location'],'/program/functions/main/body/5/2'+('/2' if c['side']=='after' else ''))
            else:self.assertIsNone(r['failure_index']);self.assertIsNone(e['location'])
if __name__=='__main__':unittest.main()
