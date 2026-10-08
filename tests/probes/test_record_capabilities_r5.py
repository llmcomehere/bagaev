"""Data-only discovery compatibility and implementation links."""
from pathlib import Path
import hashlib,json,subprocess,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_capabilities as c
class ReadableDiscovery(unittest.TestCase):
    def cli(self,args):
        return subprocess.run([sys.executable,'-B',str(T/'tools/record_capabilities.py')]+args,capture_output=True,timeout=10)
    def test_frozen_legacy_cli(self):
        for key,digest in {'4/default': '8a121083b2414276e63bcd41027c2cfe58d4c697f66e2abd8c405f2687f5dff7', '4/1': '8a121083b2414276e63bcd41027c2cfe58d4c697f66e2abd8c405f2687f5dff7', '4/2': 'c5d19dc8970245f54f6a573519c9fc4717c63c3197ca7e9c34950a43a7b5d04b', '4/3': '1440e3a1812eae88276665853070588e94713bbad03187768826fa841bbe48d4', '4/4': '14fa18c5ad601cbdc2c13d0b5c70b7fa6c33012e494b42c80b2e0520cb4f8a3c', '5/default': '0dacb0410fba589b37f51b5b21d78966b4fc667881631a121298da00d8147fce', '5/1': '0dacb0410fba589b37f51b5b21d78966b4fc667881631a121298da00d8147fce', '5/2': '9eea24256dc88d9c80b20f727b62774583e0aad342744742bd0002cbc4b018c5', '5/3': '6757d1be102a60b39d60f20c945db55e8fa1a63e76f1eccb2c13585ff8ec1fc3', '5/4': '1af0d235434f86ad88c16ca76478128704daaae55b1e96f763ecc3c91f599b36'}.items():
            form,rev=key.split('/');p=self.cli(['--form',form]+([] if rev=='default' else ['--revision',rev]))
            self.assertEqual(p.returncode,0);self.assertEqual(p.stderr,b'');self.assertEqual(hashlib.sha256(p.stdout).hexdigest(),digest)
    def test_new_data_and_detachment(self):
        for form in ['4','5']:
            v=c.describe_v5(form);self.assertEqual(v['schema'],'bagaev-record-capabilities/5');self.assertFalse(v['execution_admission']);self.assertEqual(v['readable_editing']['supported'],form=='5')
            p=self.cli(['--form',form,'--revision','5']);q=self.cli(['--form',form,'--revision','5'])
            self.assertEqual(p.returncode,0);self.assertEqual(p.stderr,b'');self.assertEqual(p.stdout,q.stdout);self.assertEqual(json.loads(p.stdout),v)
            v['readable_editing']['supported']='changed';self.assertEqual(c.describe_v5(form)['readable_editing']['supported'],form=='5')
        self.assertEqual(c.describe_v5('4')['program_schema'],'bagaev-typed-record/10');self.assertNotIn('layout_export',c.describe_v5('4')['readable_editing'])
    def test_accepted_routes(self):
        e=c.describe_v5('5')['readable_editing']
        def walk(v):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k in ('guide','tool','library','manifest'):self.assertTrue((T/x).is_file(),x)
                    walk(x)
            elif isinstance(v,list):
                for x in v:walk(x)
        walk(e)
        for route in ['function_context','layout_export']:
            r=e[route];source=(T/r['tool']).read_text()
            for flag in r['required_flags']:self.assertIn("'"+flag+"'",source)
        source=(T/e['function_context']['tool']).read_text()
        for mode in ['locations','source_body']:self.assertIn("'"+e['function_context'][mode]['flag']+"'",source)
        self.assertTrue(e['line_comments']['comments_are_untrusted_data']);self.assertFalse(e['semantic_check']);self.assertFalse(e['execution_admission']);self.assertFalse(e['performance_claim'])
    def test_refusals(self):
        for args in [[],['--form','3','--revision','5'],['--form','5','--revision','6'],['--form','5','--revision','5','--output','out']]:
            p=self.cli(args);self.assertEqual(p.returncode,2);self.assertEqual(p.stderr,b'');self.assertEqual(json.loads(p.stdout)['error']['code'],'TOOL_USAGE')
if __name__=='__main__':unittest.main()
