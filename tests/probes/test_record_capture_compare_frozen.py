"""Complete frozen capture comparisons; data-only, no evaluator subprocess."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
import record_capture_compare as cli
RAW=(ROOT/'examples/probes/record-capture-comparison/cases.json').read_bytes()
CASES=json.loads(RAW)
class Frozen(unittest.TestCase):
    def test_frozen_identity_and_axes(self):
        self.assertEqual(hashlib.sha256(RAW).hexdigest(),'9b1436bf3c98ff9add219677c3e260142feff4b913ae7b86a189834e2d1f626d')
        self.assertEqual(len(CASES),4)
        self.assertEqual([(c['expected']['same_result'],c['expected']['same_success_value'],c['expected']['same_failure'],c['expected']['work_delta']) for c in CASES],[(True,True,None,0),(False,False,None,0),(True,None,True,0),(False,True,None,4)])
    def test_complete_outputs_and_receipts(self):
        for c in CASES:
            with self.subTest(c['name']),tempfile.TemporaryDirectory() as temp:
                d=Path(temp);e=c['expected']
                for n in ('before','after'):(d/n).write_bytes(c[n+'_file'].encode('utf-8'))
                args=[str(d/'before'),str(d/'after'),'--base',e['base'],'--target',e['target'],'--arguments-sha256',e['arguments_sha256'],'--output',str(d/'out')]
                stdout=io.StringIO();stderr=io.StringIO()
                with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):code=cli.main(args)
                self.assertEqual(code,0);self.assertEqual(stderr.getvalue(),'')
                raw=(d/'out').read_bytes();self.assertEqual(json.loads(raw),e)
                self.assertEqual(hashlib.sha256(raw).hexdigest(),c['expected_sha256'])
                self.assertEqual(json.loads(stdout.getvalue()),{'schema':'bagaev-record-capture-compare-tool/1','ok':True,'result':{'output_bytes':len(raw),'output_sha256':c['expected_sha256'],'capture_authentication':False,'execution_admission':False}})
if __name__=='__main__':unittest.main()
