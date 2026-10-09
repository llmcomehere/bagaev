"""Readable bridge to frozen helper-limit graphs; data-only checks."""
from pathlib import Path
import hashlib,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
import record_work_compare as cli
import bagaev_record_wide_form as form
from bagaev_record_draft import DraftError,digest
D=ROOT/'examples/probes/record-work-helper-limit'
BASE='fa7ad5fdb6902b44f5d04b77abd3f0e07411d171899d296d973f1b93528d2cd0'
TARGET='2c9086769a4bee8f1453d271924103b71be96e9c6dcfeb64d9d80ce3656b6cff'

class Source(unittest.TestCase):
    def args(self,out):
        return [str(D/'Direct.bagaev'),str(D/'Extracted.bagaev'),'--form','5','--bounds',str(D/'bounds.json'),'--base',BASE,'--target',TARGET,'--output',str(out)]
    def test_exact_original_graphs(self):
        cases=json.loads((D/'cases.json').read_bytes())
        for c,name,pin in zip(cases,['Direct.bagaev','Extracted.bagaev'],[BASE,TARGET]):
            graph=form.decode((D/name).read_bytes())
            self.assertEqual(graph['functions']['main']['body'],c['body'])
            self.assertEqual({n:f for n,f in graph['functions'].items() if n!='main'},c['functions'])
            self.assertEqual(digest(graph),pin)
    def test_exact_cli_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'comparison.json';receipt=cli.convert(self.args(out))
            self.assertEqual(out.read_bytes(),(D/'comparison.json').read_bytes())
            self.assertEqual(receipt['output_sha256'],'e2d91fc31a064baeba8645a889e1d33e545a23bbc48027ea898500a5e64a5a1a')
            r=json.loads(out.read_bytes());self.assertEqual(r['upper_work_delta'],1024)
            self.assertTrue(r['before']['fits_work_budget']);self.assertFalse(r['after']['fits_work_budget'])
    def test_changed_source_stale_pin(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out';changed=Path(td)/'changed'
            changed.write_bytes((D/'Extracted.bagaev').read_bytes().replace(b'1024',b'1023',1))
            args=self.args(out);args[1]=str(changed)
            with self.assertRaises(DraftError) as caught:cli.convert(args)
            self.assertEqual(caught.exception.code,'DRAFT_TARGET');self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
