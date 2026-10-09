"""Source/argument applicability of prior captures; no new program execution."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work_observation import observe_source
from bagaev_record_wide_form import decode
from bagaev_record_draft import digest
D=ROOT/'examples/probes/record-work-helper-edit'
E=json.loads((D/'cases.json').read_bytes())
def observation(side,case,arguments=None,source=None):
    source=(D/('Direct.bagaev' if side=='before' else 'Extracted.bagaev')).read_bytes() if source is None else source
    return observe_source(source,case['bounds'],case['arguments'] if arguments is None else arguments,program_sha256=E['base' if side=='before' else 'target'])
class HelperApplicability(unittest.TestCase):
    def test_prior_graphs_arguments_and_bounds(self):
        for side,file in [('before','Direct.bagaev'),('after','Extracted.bagaev')]:
            self.assertEqual(decode((D/file).read_bytes()),E[side+'_graph'])
            for c in E['cases']:
                r=observation(side,c);dims=r['argument_dimensions']
                self.assertEqual(dims['status'],'WITHIN')
                self.assertEqual(dims['arguments_sha256'],digest({'items':c['arguments'][0]}))
                self.assertEqual(dims['dimensions'][0]['items'],len(c['arguments'][0]))
                self.assertEqual(r['work_bound']['upper_work'],c[side+'_bound'])
                self.assertLessEqual(c[side]['work'],r['work_bound']['upper_work'])
                self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])
    def test_same_dimensions_do_not_bind_the_same_values(self):
        c=E['cases'][1];changed=copy.deepcopy(c['arguments']);changed[0][0]['amount']+=1
        for side in ('before','after'):
            a=observation(side,c);b=observation(side,c,changed)
            self.assertEqual(a['argument_dimensions']['dimensions'],b['argument_dimensions']['dimensions'])
            self.assertEqual(a['work_bound'],b['work_bound'])
            self.assertNotEqual(a['argument_dimensions']['arguments_sha256'],b['argument_dimensions']['arguments_sha256'])
            self.assertFalse(b['execution_admission'])
    def test_source_bytes_and_program_graph_are_distinct(self):
        c=E['cases'][0];source=(D/'Direct.bagaev').read_bytes();commented=source+b'\n// explanatory comment\n'
        a=observation('before',c);b=observation('before',c,source=commented)
        self.assertEqual(a['program_sha256'],b['program_sha256']);self.assertNotEqual(a['source_sha256'],b['source_sha256'])
        self.assertEqual(b['source_sha256'],hashlib.sha256(commented).hexdigest())
        self.assertEqual(a['argument_dimensions'],b['argument_dimensions'])

if __name__=='__main__':unittest.main()
