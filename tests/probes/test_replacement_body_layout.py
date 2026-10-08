"""Data-only authored-body export; literal byte oracle precedes implementation."""
from pathlib import Path
import copy,contextlib,hashlib,io,json,sys,tempfile,unittest
from unittest.mock import patch
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tools'))
import bagaev_record_export as e
import record_export as cli
class ReplacementLayout(unittest.TestCase):
    def setUp(self):
        self.o=json.loads((T/'examples/probes/replacement-body-layout/oracle.json').read_bytes());self.raw=self.o['original'].encode();self.fragment=self.o['replacement'].encode()
        old=e.wide.form.decode(self.raw);new=e.wide.form.decode(self.fragment)
        self.assertEqual(old['functions']['main']['body'],self.o['old_body']);self.assertEqual(new['functions']['main']['body'],self.o['new_body'])
        self.base=e.digest(old);self.target=e.digest(new);self.packet=e.wide.replace(self.raw,self.fragment,base_sha256=self.base,function_sha256=e.digest(old['functions']['main']))
        self.args=dict(base_sha256=self.base,target_sha256=self.target,source_sha256=hashlib.sha256(self.raw).hexdigest())
    def test_literal_bytes_and_purity(self):
        saved=copy.deepcopy(self.packet)
        for raw,fragment in [(self.raw,self.fragment),(self.raw.decode(),self.fragment.decode())]:
            out=e.export_source_with_fragment_layout(raw,self.packet,fragment,**self.args);self.assertEqual(out,self.o['expected'].encode());self.assertEqual(hashlib.sha256(out).hexdigest(),'2d784ee0437428001e73daab9aedccc36e83244d2590d36a3c0046da17e07c0f')
        self.assertEqual(self.packet,saved)
    def test_refused_fragment_and_pins(self):
        variants=[self.fragment.replace(b'3 +',b'5 +'),self.fragment.replace(b'entry main;',b'entry main; fn other() -> Int64 = 0;'),self.fragment.replace(b'program {',b'program { record Extra { x: Int64 };'),self.fragment.replace(b'fn main()',b'fn main(x: Int64)'),b'invalid',self.raw]
        for fragment in variants:
            with self.assertRaises((e.DraftError,e.wide.form.FormError)):e.export_source_with_fragment_layout(self.raw,self.packet,fragment,**self.args)
        for key in self.args:
            args={**self.args,key:'0'*64}
            with self.assertRaises(e.DraftError):e.export_source_with_fragment_layout(self.raw,self.packet,self.fragment,**args)
        bad=copy.deepcopy(self.packet);bad['execution_admission']=True
        with self.assertRaises(e.DraftError):e.export_source_with_fragment_layout(self.raw,bad,self.fragment,**self.args)
    def test_named_body_spelling(self):
        raw=b'bagaev record-form/5; program { entry main; fn main(a: Int64,b: Int64) -> Int64 = a-b; }'
        replacement=b'bagaev record-form/5; program { entry main; fn main(a: Int64,b: Int64) -> Int64 = main(b:4,a:9); }'
        old=e.wide.form.decode(raw);packet=e.wide.replace(raw,replacement,base_sha256=e.digest(old),function_sha256=e.digest(old['functions']['main']))
        out=e.export_source_with_fragment_layout(raw,packet,replacement,base_sha256=e.digest(old),target_sha256=packet['target'],source_sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(out,raw.replace(b'a-b',b'main(b:4,a:9)'))
    def test_cli_and_unchanged_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);source=d/'original';fragment=d/'fragment';packet=d/'draft';out=d/'output';source.write_bytes(self.raw);fragment.write_bytes(self.fragment);packet.write_text(json.dumps(self.packet))
            args=[str(source),'--draft',str(packet),'--form','5','--base',self.base,'--target',self.target,'--source-sha256',self.args['source_sha256'],'--preserve-layout','--replacement-source',str(fragment),'--output',str(out)]
            with contextlib.redirect_stdout(io.StringIO()) as b:self.assertEqual(cli.main(args),0)
            receipt=json.loads(b.getvalue());self.assertEqual(receipt['replacement_source_sha256'],hashlib.sha256(self.fragment).hexdigest());self.assertEqual(receipt['replacement_scope'],'body-expression');self.assertEqual(out.read_bytes(),self.o['expected'].encode())
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cli.main(args),2)
            self.assertEqual(out.read_bytes(),self.o['expected'].encode());self.assertEqual(source.read_bytes(),self.raw);self.assertEqual(fragment.read_bytes(),self.fragment)
    def test_combined_output_bound(self):
        raw=self.raw.replace(b'// unchanged module',b'// '+b'x'*2048)
        fragment=self.fragment.replace('новый комментарий'.encode(),b'y'*(e.wide.form.old.BYTE_LIMIT-len(self.fragment)))
        args={**self.args,'source_sha256':hashlib.sha256(raw).hexdigest()}
        with self.assertRaises(e.DraftError) as err:e.export_source_with_fragment_layout(raw,self.packet,fragment,**args)
        self.assertEqual(err.exception.code,'EXPORT_BOUNDS')
    def test_usage_before_read(self):
        for flags in [[],['--form','4','--preserve-layout','--source-sha256','0'*64],['--form','5']]:
            args=['missing','--draft','missing','--base','0'*64,'--target','0'*64,'--replacement-source','missing','--output','unused']+flags
            with patch.object(cli.transport,'read_input',side_effect=AssertionError('must not read')),contextlib.redirect_stdout(io.StringIO()) as b:
                self.assertEqual(cli.main(args),2)
            self.assertEqual(json.loads(b.getvalue())['error']['code'],'TOOL_USAGE')
if __name__=='__main__':unittest.main()
