"""Synthetic offline bundles. All reference dispatch is prohibited."""
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import record_run_verify as v
def cases():
    raw=(ROOT/'examples/probes/run-verify/cases.json').read_bytes()
    assert v.sha(raw)=='d00a89e0bf601c1fc2185e3c4bb9a260a2204cd7e47023b7e423cb90dc81e20a'
    return json.loads(raw)['cases']
class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.guard=patch.object(v.run.capture_tools,'capture',side_effect=AssertionError('dispatch forbidden'))
        self.guard.start();self.addCleanup(self.guard.stop)
    def bundle(self,base,case=None):
        case=case or cases()[0];root=base/'bundle';root.mkdir()
        for name,raw in case['files'].items():(root/name).write_bytes(raw.encode())
        return root,v.sha((root/'receipt.json').read_bytes())
    def error(self,root,pin,code):
        with self.assertRaises(v.VerifyError) as caught:v.verify(root,pin)
        self.assertEqual(caught.exception.code,code)
    def repin(self,root,receipt):
        raw=v.canonical(receipt);(root/'receipt.json').write_bytes(raw);return v.sha(raw)
    def test_literal_bundles(self):
        for case in cases():
            with self.subTest(case=case['name']),tempfile.TemporaryDirectory() as d:
                root,pin=self.bundle(Path(d),case);before={p.name:p.read_bytes() for p in root.iterdir()}
                self.assertTrue(v.exact(v.verify(root,pin),case['expected']))
                self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
    def test_raw_receipt_and_forgery(self):
        with tempfile.TemporaryDirectory() as d:
            root,pin=self.bundle(Path(d));receipt=json.loads((root/'receipt.json').read_bytes())
            receipt['reference_sha256']='f'*64
            raw=json.dumps(receipt,indent=3).encode();(root/'receipt.json').write_bytes(raw)
            actual=v.verify(root,v.sha(raw));self.assertEqual(actual['claimed_reference_sha256'],'f'*64)
            for flag in ('fresh_run','reference_invoked','result_authentication','execution_admission','application_expectation_checked'):
                self.assertIs(actual[flag],False)
    def test_pins_and_member_tampering(self):
        for name,code in [('source.bagaev','SOURCE'),('arguments.json','ARGUMENTS'),('program.json','SOURCE'),
                          ('invocation.json','INVOCATION'),('reference.stdout','RESULT'),('reference.stderr','RESULT')]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                root,pin=self.bundle(Path(d));p=root/name;p.write_bytes(p.read_bytes()+b' ')
                self.error(root,pin,'RUN_VERIFY_'+code)
        with tempfile.TemporaryDirectory() as d:
            root,pin=self.bundle(Path(d))
            for bad in ('x','A'*64,'0'*64):self.error(root,bad,'RUN_VERIFY_PIN')
    def test_receipt_fields(self):
        original=json.loads(cases()[0]['files']['receipt.json'])
        for key in original:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as d:
                root,pin=self.bundle(Path(d));receipt=dict(original);receipt[key]=[]
                pin=self.repin(root,receipt);self.error(root,pin,'RUN_VERIFY_RECEIPT')
        for key,value in [('work',True),('work',2),('runtime_status','invalid-ir'),('reason','RR_TYPE'),('location','/x')]:
            with self.subTest(key=key,value=value),tempfile.TemporaryDirectory() as d:
                root,pin=self.bundle(Path(d));receipt=dict(original);receipt[key]=value;pin=self.repin(root,receipt)
                self.error(root,pin,'RUN_VERIFY_RECEIPT' if key=='work' and value is True else 'RUN_VERIFY_RESULT')
    def test_paths_and_sizes(self):
        names=list(cases()[0]['files'])
        for name in names:
            for fault in ('missing','symlink','directory','oversized'):
                with self.subTest(name=name,fault=fault),tempfile.TemporaryDirectory() as d:
                    base=Path(d);root,pin=self.bundle(base);p=root/name;p.unlink()
                    if fault=='symlink':p.symlink_to(base/'absent')
                    elif fault=='directory':p.mkdir()
                    elif fault=='oversized':p.write_bytes(b'x'*(4097 if name=='reference.stderr' else 1048577))
                    self.error(root,pin,'RUN_VERIFY_BOUNDS' if fault=='oversized' else 'RUN_VERIFY_PATH')
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root,pin=self.bundle(base);alias=base/'alias';alias.symlink_to(root,target_is_directory=True)
            self.error(alias,pin,'RUN_VERIFY_PATH');(root/'extra').write_text('x');self.error(root,pin,'RUN_VERIFY_PATH')
    def test_rebound_invalid_data(self):
        for field,name,raw,code in [('arguments_sha256','arguments.json',b'[NaN]','ARGUMENTS'),
             ('result_sha256','reference.stdout',b'{}','RESULT')]:
            with tempfile.TemporaryDirectory() as d:
                root,pin=self.bundle(Path(d));(root/name).write_bytes(raw)
                receipt=json.loads((root/'receipt.json').read_bytes());receipt[field]=v.sha(raw);pin=self.repin(root,receipt)
                self.error(root,pin,'RUN_VERIFY_'+code)
        with tempfile.TemporaryDirectory() as d:
            root,pin=self.bundle(Path(d));raw=(root/'receipt.json').read_bytes();raw=b'{"work":1,'+raw[1:]
            (root/'receipt.json').write_bytes(raw);self.error(root,v.sha(raw),'RUN_VERIFY_RECEIPT')
    def test_output_paths(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root,pin=self.bundle(base);alias=base/'alias';alias.symlink_to(root,target_is_directory=True)
            occupied=base/'occupied';occupied.write_bytes(b'keep');dangling=base/'dangling';dangling.symlink_to(base/'absent')
            for output in (root/'report',root/'../bundle/report',alias/'report',occupied,dangling):
                with contextlib.redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(v.main([str(root),'--receipt-sha256',pin,'--output',str(output)]),1)
                self.assertEqual(errors.getvalue().strip(),'RUN_VERIFY_OUTPUT')
            self.assertEqual(occupied.read_bytes(),b'keep');self.assertFalse((root/'report').exists())
            out=base/'verified.json';self.assertEqual(v.main([str(root),'--receipt-sha256',pin,'--output',str(out)]),0)
            self.assertTrue(v.exact(json.loads(out.read_bytes()),cases()[0]['expected']))
    def test_output_size_and_coherent_invalid_source(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root,pin=self.bundle(base,cases()[5])
            receipt=json.loads((root/'receipt.json').read_bytes())
            # A coherent fabricated success does not turn this illtyped source into admission.
            result={'schema':'bagaev-typed-record-result/11','status':'success','value_type':'Bool',
                    'value':True,'work':1,'reason':None,'location':None}
            stdout=v.canonical(result);(root/'reference.stdout').write_bytes(stdout)
            receipt.update(result_sha256=v.sha(stdout),runtime_status='success',work=1,reason=None,location=None)
            pin=self.repin(root,receipt);self.assertIs(v.verify(root,pin)['execution_admission'],False)
            # Construct a real near-limit receipt whose expanded verification report exceeds the cap.
            result.update(status='invalid-ir',value_type=None,value=None,work=0,reason='RR_TYPE',location='/')
            receipt.update(runtime_status='invalid-ir',work=0,reason='RR_TYPE',location='/')
            count=1048576-len(v.canonical(receipt))
            location='/'+'x'*count;result['location']=location;receipt['location']=location
            stdout=v.canonical(result);receipt['result_sha256']=v.sha(stdout)
            (root/'reference.stdout').write_bytes(stdout);pin=self.repin(root,receipt)
            self.assertEqual((root/'receipt.json').stat().st_size,1048576)
            self.assertGreater(len(v.canonical(v.verify(root,pin))),1048576)
            out=base/'oversized.json'
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(v.main([str(root),'--receipt-sha256',pin,'--output',str(out)]),1)
            self.assertEqual(errors.getvalue().strip(),'RUN_VERIFY_BOUNDS');self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
