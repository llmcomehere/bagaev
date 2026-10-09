"""Observation transport reports data outcomes without running source programs."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
import record_work_observe as cli
from bagaev_record_draft import digest
from bagaev_record_wide_form import decode
S='bagaev record-form/5; program { entry main; fn main(x: Text) -> Bool = text.eq(x,"é"); }'
class CLI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.d=Path(self.temp.name)
        for n,s in [('source',S),('bounds','{ "x": {"type":"Text","bytes":2} }'),('args','["é"]')]: (self.d/n).write_text(s)
    def args(self):return [str(self.d/'source'),'--form','5','--program',digest(decode((self.d/'source').read_bytes())),'--bounds',str(self.d/'bounds'),'--arguments',str(self.d/'args'),'--output',str(self.d/'out')]
    def run_cli(self,args=None):
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):code=cli.main(self.args() if args is None else args)
        return code,json.loads(stream.getvalue())
    def test_within_and_exceeds(self):
        for n,status in [(2,'WITHIN'),(0,'EXCEEDS')]:
            (self.d/'bounds').write_text(json.dumps({'x':{'type':'Text','bytes':n}}))
            code,r=self.run_cli();self.assertEqual(code,0)
            raw=(self.d/'out').read_bytes();data=json.loads(raw)
            self.assertEqual(data['argument_dimensions']['status'],status)
            self.assertEqual(r['result']['output_sha256'],hashlib.sha256(raw).hexdigest());self.assertFalse(data['execution_admission'])
            (self.d/'out').unlink()
    def test_negative_data_outcomes_still_write_observation(self):
        (self.d/'args').write_text('[false]');code,r=self.run_cli();self.assertEqual(code,0)
        self.assertEqual(json.loads((self.d/'out').read_bytes())['argument_dimensions']['status'],'INVALID_ARGUMENT')
        (self.d/'out').unlink();(self.d/'args').write_text('["é"]')
        (self.d/'source').write_text(S.replace('text.eq(x,"é")','int.eq(text.bytes(x),2)'))
        code,r=self.run_cli();self.assertEqual(code,0)
        self.assertEqual(json.loads((self.d/'out').read_bytes())['work_bound']['status'],'UNKNOWN')
    def test_usage_and_bad_transport(self):
        a=self.args()
        for bad in [a[:1]+a[3:],a[:2]+['4']+a[3:],a[:4]+['0'*64]+a[5:],a+['--run']]:
            code,r=self.run_cli(bad);self.assertEqual(code,2);self.assertFalse((self.d/'out').exists())
        (self.d/'args').write_text('[');self.assertEqual(self.run_cli()[0],2);self.assertFalse((self.d/'out').exists())
    def test_exclusive_output_and_symlink(self):
        (self.d/'out').write_bytes(b'keep');self.assertEqual(self.run_cli()[0],2);self.assertEqual((self.d/'out').read_bytes(),b'keep')
        (self.d/'out').unlink();(self.d/'bounds').unlink();(self.d/'bounds').symlink_to(self.d/'args')
        self.assertEqual(self.run_cli()[0],2);self.assertFalse((self.d/'out').exists())
    def test_raw_file_identities(self):
        self.assertEqual(self.run_cli()[0],0);r=json.loads((self.d/'out').read_bytes())
        self.assertEqual(r['arguments_file_sha256'],hashlib.sha256((self.d/'args').read_bytes()).hexdigest())
        self.assertEqual(r['argument_bounds_file_sha256'],hashlib.sha256((self.d/'bounds').read_bytes()).hexdigest())
        self.assertNotEqual(r['argument_bounds_file_sha256'],r['argument_dimensions']['argument_bounds_sha256'])

if __name__=='__main__':unittest.main()
