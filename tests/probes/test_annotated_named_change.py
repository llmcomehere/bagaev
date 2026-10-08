"""Four data commands reproduce an authored named-body change; no evaluation."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/annotated-named-change';sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as f
import bagaev_record_wide_spans as spans
class AnnotatedNamedChange(unittest.TestCase):
    def test_fixture_target_and_boundaries(self):
        source=(T/'examples/probes/annotated-change/Batch.annotated.bagaev').read_bytes();out=(D/'BatchLimited.named.bagaev').read_bytes();m=json.loads((D/'manifest.json').read_bytes())
        self.assertEqual(f.decode(out),json.loads((T/'examples/probes/inventory-batch-change/program.json').read_bytes()));self.assertEqual(hashlib.sha256(out).hexdigest(),m['expected_source_sha256'])
        old,new=[next(x for x in spans.source_map(s)['locations'] if x['program_pointer']=='/program/functions/batch_apply/body') for s in [source,out]]
        self.assertEqual(source[:old['start_byte']],out[:new['start_byte']]);self.assertEqual(source[old['end_byte']:],out[new['end_byte']:]);self.assertIn(b'Authored body note retained',out);self.assertNotIn(b'Original body note',out)
    def test_four_commands(self):
        m=json.loads((D/'manifest.json').read_bytes());source=T/'examples/probes/annotated-change/Batch.annotated.bagaev';fragment=D/'BatchLimited.named.fragment.bagaev';original=source.read_bytes();frag=fragment.read_bytes();self.assertEqual(hashlib.sha256(original).hexdigest(),m['source_sha256']);self.assertEqual(hashlib.sha256(frag).hexdigest(),m['fragment_sha256'])
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);context=d/'context.json';draft=d/'draft.json';out=d/'BatchLimited.named.bagaev';inspection=d/'inspection.json'
            commands=[['record_function.py','context',str(source),'--form','5','--name','batch_apply','--source-body','--output',str(context)],['record_function.py','replace',str(source),'--form','5','--callee-context','--replacement',str(fragment),'--base',m['base'],'--function-pin',m['function'],'--output',str(draft)],['record_export.py',str(source),'--draft',str(draft),'--form','5','--base',m['base'],'--target',m['target'],'--preserve-layout','--source-sha256',m['source_sha256'],'--replacement-source',str(fragment),'--callee-context','--output',str(out)],['record_text.py','inspect',str(out),'--form','5','--output',str(inspection)]]
            for args in commands:
                q=subprocess.run([sys.executable,'-B',str(T/'tools'/args[0])]+args[1:],capture_output=True,timeout=20);self.assertEqual(q.returncode,0,q.stdout);self.assertEqual(q.stderr,b'')
            for path,key in [(context,'context_sha256'),(draft,'draft_sha256'),(out,'expected_source_sha256'),(inspection,'inspection_sha256')]:self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),m[key])
            self.assertEqual(out.read_bytes(),(D/'BatchLimited.named.bagaev').read_bytes());self.assertEqual(json.loads(inspection.read_bytes())['program_sha256'],m['target']);old=json.loads((T/'examples/probes/annotated-change/manifest.json').read_bytes());self.assertEqual(m['draft_sha256'],old['draft_sha256'])
        self.assertEqual(source.read_bytes(),original);self.assertEqual(fragment.read_bytes(),frag)
if __name__=='__main__':unittest.main()
