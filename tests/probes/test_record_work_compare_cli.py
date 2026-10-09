"""Data-only CLI transport; no source-program execution."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
import record_work_compare as cli
from bagaev_record_draft import digest
from bagaev_record_wide_form import decode

OLD='bagaev record-form/5; program { entry main; fn main(x: Int64) -> Int64 = x + 1; }'
NEW=OLD.replace('x + 1','x + one()').replace('entry main;','entry main; fn one() -> Int64 = 1;')

class CLI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.d=Path(self.temp.name)
        for n,t in [('old',OLD),('new',NEW),('bounds','{ "x": {"type":"Int64"} }')]:
            (self.d/n).write_text(t)
    def args(self):
        return [str(self.d/'old'),str(self.d/'new'),'--form','5','--bounds',str(self.d/'bounds'),'--base',digest(decode(OLD)),'--target',digest(decode(NEW)),'--output',str(self.d/'out')]
    def run_cli(self,args):
        s=io.StringIO()
        with contextlib.redirect_stdout(s):code=cli.main(args)
        return code,json.loads(s.getvalue())
    def test_success_receipt(self):
        code,r=self.run_cli(self.args());self.assertEqual(code,0)
        raw=(self.d/'out').read_bytes();data=json.loads(raw)
        self.assertEqual(data['upper_work_delta'],1)
        self.assertEqual(r['result']['output_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(data['argument_bounds_file_sha256'],hashlib.sha256((self.d/'bounds').read_bytes()).hexdigest())
        self.assertNotEqual(data['argument_bounds_file_sha256'],data['argument_bounds_sha256'])
        self.assertFalse(data['execution_admission']);self.assertFalse(data['equivalence_check'])
    def test_usage_and_pins(self):
        args=self.args()
        for bad in (args[:2]+args[4:],args[:3]+['4']+args[4:],args+['--run'],args[:7]+['0'*64]+args[8:]):
            code,r=self.run_cli(bad);self.assertEqual(code,2);self.assertFalse(r['ok']);self.assertFalse((self.d/'out').exists())
    def test_bounds_refusals(self):
        for text in ('{}','{"x":{"type":"Bool"}}','{"x":{},"x":{}}','[]','{'):
            (self.d/'bounds').write_text(text)
            code,r=self.run_cli(self.args());self.assertEqual(code,2);self.assertFalse((self.d/'out').exists())
    def test_existing_and_symlink(self):
        (self.d/'out').write_bytes(b'keep')
        code,r=self.run_cli(self.args());self.assertEqual(code,2);self.assertEqual((self.d/'out').read_bytes(),b'keep')
        (self.d/'out').unlink();(self.d/'old').unlink();(self.d/'old').symlink_to(self.d/'new')
        code,r=self.run_cli(self.args());self.assertEqual(code,2);self.assertFalse((self.d/'out').exists())
    def test_unknown_is_successful_analysis(self):
        new=OLD.replace('x + 1','text.bytes("x")');(self.d/'new').write_text(new)
        args=self.args();args[9]=digest(decode(new))
        code,r=self.run_cli(args);self.assertEqual(code,0)
        data=json.loads((self.d/'out').read_bytes());self.assertEqual(data['after']['status'],'UNKNOWN');self.assertNotIn('upper_work_delta',data)

if __name__=='__main__':unittest.main()
