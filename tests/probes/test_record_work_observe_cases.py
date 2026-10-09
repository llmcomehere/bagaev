"""Frozen full observations and transport receipts; no program evaluation."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
import record_work_observe as cli
from bagaev_record_wide_form import decode
from bagaev_record_draft import digest
CASES=ROOT/'examples/probes/record-work-observe/cases.json'

class FrozenObservations(unittest.TestCase):
    def test_frozen_identities(self):
        raw=CASES.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'a0d67f28b97d129571a60363dff11d8aa153eed496f2bbd0841f5f07106dd480')
        cases=json.loads(raw);self.assertEqual(len(cases),4)
        for c in cases:
            self.assertEqual(decode(c['source']),c['program'])
            self.assertEqual(digest(c['program']),c['expected']['program_sha256'])
            self.assertFalse(c['expected']['execution_admission'])
    def test_complete_outputs(self):
        for c in json.loads(CASES.read_bytes()):
            with self.subTest(case=c['name']),tempfile.TemporaryDirectory() as t:
                d=Path(t)
                for n,k in [('source','source'),('bounds','bounds_file'),('args','arguments_file')]: (d/n).write_text(c[k],encoding='utf-8')
                stream=io.StringIO()
                with contextlib.redirect_stdout(stream):
                    code=cli.main([str(d/'source'),'--form','5','--program',c['expected']['program_sha256'],'--bounds',str(d/'bounds'),'--arguments',str(d/'args'),'--output',str(d/'out')])
                self.assertEqual(code,0);raw=(d/'out').read_bytes()
                self.assertEqual(json.loads(raw),c['expected'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(),c['expected_sha256'])
                self.assertEqual(json.loads(stream.getvalue()),{'schema':'bagaev-record-work-observe-tool/1','ok':True,'result':{'output_bytes':len(raw),'output_sha256':c['expected_sha256'],'semantic_check':False,'execution_admission':False}})

if __name__=='__main__':unittest.main()
