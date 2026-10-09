"""Pinned helper extraction with separate value, logical-work and admission facts."""
from pathlib import Path
import hashlib,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import bagaev_record_wide_draft as draft
import record_text

D=ROOT/'examples/probes/record-work-helper-edit'
C=json.loads((D/'cases.json').read_bytes())

class HelperEdit(unittest.TestCase):
    def test_exact_graphs_and_change_scope(self):
        old=(D/'Direct.bagaev').read_text();new=(D/'Extracted.bagaev').read_text()
        self.assertEqual(draft.form.decode(old),C['before_graph'])
        self.assertEqual(draft.form.decode(new),C['after_graph'])
        result=draft.draft(old,new,base_sha256=C['base'],target_sha256=C['target'])
        self.assertEqual(result['delta'],{'add':['amount'],'replace':['main']})
        self.assertEqual(result['program'],C['after_graph'])
        self.assertFalse(result['execution_admission']);self.assertFalse(result['semantic_check'])
        for key in ('schema','records','lists','variants','entry'):
            self.assertEqual(C['before_graph'][key],C['after_graph'][key])
        with self.assertRaises(draft.DraftError):
            draft.draft(old,new,base_sha256='0'*64,target_sha256=C['target'])

    def test_inspection_pins_and_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp=Path(directory)
            for case in C['cases']:
                bounds=tmp/'bounds';bounds.write_text(json.dumps(case['bounds']))
                for version,filename,pin in [('before','Direct.bagaev','base'),('after','Extracted.bagaev','target')]:
                    out=tmp/(case['name']+version)
                    record_text.convert(['inspect',str(D/filename),'--form','5','--bounds',str(bounds),'--output',str(out)])
                    actual=json.loads(out.read_bytes())
                    self.assertEqual(actual['program_sha256'],C[pin])
                    self.assertEqual(actual['source_sha256'],hashlib.sha256((D/filename).read_bytes()).hexdigest())
                    self.assertEqual(actual['argument_bounds_sha256'],hashlib.sha256(bounds.read_bytes()).hexdigest())
                    self.assertEqual(actual['work_bound']['upper_work'],case[version+'_bound'])
                    self.assertFalse(actual['work_bound']['execution_admission'])

    def test_value_equality_is_not_work_equality(self):
        for case in C['cases']:
            self.assertEqual(case['before']['status'],'success')
            self.assertEqual(case['after']['status'],'success')
            self.assertEqual(case['before']['value'],case['after']['value'])
            n=len(case['arguments'][0])
            self.assertEqual(case['after']['work']-case['before']['work'],2*n)
            self.assertLessEqual(case['before']['work'],case['before_bound'])
            self.assertLessEqual(case['after']['work'],case['after_bound'])

if __name__=='__main__':unittest.main()
