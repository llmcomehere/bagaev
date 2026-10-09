"""Capture comparison transport boundaries, no source or kernel calls."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
import record_capture_compare as cli
from bagaev_record_draft import digest
CASES=json.loads((ROOT/'examples/probes/record-branch-edit/cases.json').read_bytes())
class CLI(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name);self.select(0)
    def select(self,i):
        a,b=CASES[i:i+2];self.base=digest(a['program']);self.target=digest(b['program']);self.pin=digest(a['arguments'])
        for name,c,pin in [('before',a,self.base),('after',b,self.target)]:
            (self.d/name).write_text(json.dumps({'program_sha256':pin,'arguments_sha256':self.pin,'result':c['expected']},indent=2))
    def args(self):return [str(self.d/'before'),str(self.d/'after'),'--base',self.base,'--target',self.target,'--arguments-sha256',self.pin,'--output',str(self.d/'out')]
    def call(self,args=None):
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):code=cli.main(self.args() if args is None else args)
        return code,json.loads(stream.getvalue())
    def test_equal_changed_and_failure_data(self):
        for i,same in [(0,True),(2,False),(4,True)]:
            self.select(i);code,receipt=self.call();self.assertEqual(code,0)
            raw=(self.d/'out').read_bytes();r=json.loads(raw);self.assertEqual(r['same_result'],same)
            self.assertEqual(receipt['result']['output_sha256'],hashlib.sha256(raw).hexdigest());self.assertFalse(r['capture_authentication']);self.assertFalse(receipt['result']['execution_admission'])
            (self.d/'out').unlink()
    def test_raw_file_identities(self):
        self.assertEqual(self.call()[0],0);r=json.loads((self.d/'out').read_bytes())
        for n in ('before','after'):self.assertEqual(r[n+'_file_sha256'],hashlib.sha256((self.d/n).read_bytes()).hexdigest())
        self.assertNotEqual(r['before_file_sha256'],r['before_result_sha256'])
    def test_stale_and_malformed_data(self):
        args=self.args();args[3]='0'*64;self.assertEqual(self.call(args)[0],2);self.assertFalse((self.d/'out').exists())
        value=json.loads((self.d/'before').read_bytes());value['extra']=0;(self.d/'before').write_text(json.dumps(value))
        self.assertEqual(self.call()[0],2);self.assertFalse((self.d/'out').exists())
        (self.d/'before').write_text('{');self.assertEqual(self.call()[0],2);self.assertFalse((self.d/'out').exists())
    def test_usage(self):
        for args in [self.args()+['--run'],self.args()[:-2],self.args()+['--form','5']]:
            self.assertEqual(self.call(args)[0],2);self.assertFalse((self.d/'out').exists())
    def test_existing_output_and_symlink(self):
        (self.d/'out').write_bytes(b'keep');self.assertEqual(self.call()[0],2);self.assertEqual((self.d/'out').read_bytes(),b'keep')
        (self.d/'out').unlink();(self.d/'before').unlink();(self.d/'before').symlink_to(self.d/'after')
        self.assertEqual(self.call()[0],2);self.assertFalse((self.d/'out').exists())

if __name__=='__main__':unittest.main()
