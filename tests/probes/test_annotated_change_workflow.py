"""Four data-tool steps on portable public fixtures; no program/kernel execution."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/annotated-change';sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as f
import bagaev_record_wide_spans as spans
class AnnotatedChange(unittest.TestCase):
    def test_fixture_graph_and_outside_bytes(self):
        m=json.loads((D/'manifest.json').read_bytes());raw=(D/'Batch.annotated.bagaev').read_bytes();out=(D/'BatchLimited.annotated.bagaev').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),m['source_sha256']);self.assertEqual(hashlib.sha256(out).hexdigest(),m['expected_source_sha256'])
        self.assertEqual(f.decode(raw),json.loads((T/'examples/probes/inventory-batch/program.json').read_bytes()));self.assertEqual(f.decode(out),json.loads((T/'examples/probes/inventory-batch-change/program.json').read_bytes()))
        old,new=[next(x for x in spans.source_map(s)['locations'] if x['program_pointer']=='/program/functions/batch_apply/body') for s in [raw,out]]
        self.assertEqual(raw[:old['start_byte']],out[:new['start_byte']]);self.assertEqual(raw[old['end_byte']:],out[new['end_byte']:])
    def test_four_data_commands(self):
        m=json.loads((D/'manifest.json').read_bytes());source=D/'Batch.annotated.bagaev';original=source.read_bytes();fragment=T/'examples/probes/inventory-batch-change/BatchLimited.fragment.bagaev'
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);context=out/'context.json';draft=out/'draft.json';target=out/'BatchLimited.annotated.bagaev';inspection=out/'inspection.json'
            commands=[['record_function.py','context',str(source),'--form','5','--name','batch_apply','--locations','--output',str(context)],['record_function.py','replace',str(source),'--form','5','--replacement',str(fragment),'--base',m['base'],'--function-pin',m['function'],'--output',str(draft)],['record_export.py',str(source),'--draft',str(draft),'--form','5','--base',m['base'],'--target',m['target'],'--preserve-layout','--source-sha256',m['source_sha256'],'--output',str(target)],['record_text.py','inspect',str(target),'--form','5','--output',str(inspection)]]
            for args in commands:
                q=subprocess.run([sys.executable,'-B',str(T/'tools'/args[0])]+args[1:],capture_output=True,timeout=20);self.assertEqual(q.returncode,0,q.stdout);self.assertEqual(q.stderr,b'')
            for path,key in [(context,'context_sha256'),(draft,'draft_sha256'),(target,'expected_source_sha256'),(inspection,'inspection_sha256')]:self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),m[key])
            self.assertEqual(target.read_bytes(),(D/'BatchLimited.annotated.bagaev').read_bytes());self.assertEqual(json.loads(inspection.read_bytes())['program_sha256'],m['target'])
        self.assertEqual(source.read_bytes(),original)
if __name__=='__main__':unittest.main()
