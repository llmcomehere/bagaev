"""Explicit contextual replacement/export CLI; no program execution."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
from unittest.mock import patch
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tools'))
import bagaev_record_export as e
import record_export as export_cli
import record_function as edit_cli
class ContextualWorkflow(unittest.TestCase):
    def setUp(self):
        d=T/'examples/probes/contextual-fragment';self.v=json.loads((d/'cases.json').read_bytes());self.pins=json.loads((d/'packets.json').read_bytes());self.raw=self.v['original'].encode();self.old=e.wide.form.decode(self.raw);self.base=e.digest(self.old);self.pin=e.digest(self.old['functions']['main'])
    def fragment(self,expr):return ('bagaev record-form/5; program { entry main; fn main(x: Int64) -> Int64 = '+expr+'; }').encode()
    def call(self,cli,args):
        with contextlib.redirect_stdout(io.StringIO()) as buf:code=cli.main(args)
        return code,json.loads(buf.getvalue())
    def test_four_literal_workflows(self):
        for case in self.v['cases']:
            with tempfile.TemporaryDirectory() as directory:
                d=Path(directory);src=d/'source';frag=d/'fragment';draft=d/'draft';out=d/'out';src.write_bytes(self.raw);frag.write_bytes(self.fragment(case['named']))
                a=['replace',str(src),'--form','5','--callee-context','--replacement',str(frag),'--base',self.base,'--function-pin',self.pin,'--output',str(draft)]
                code,r=self.call(edit_cli,a);self.assertEqual(code,0);self.assertEqual(r['callee_context_base'],self.base);self.assertEqual(hashlib.sha256(draft.read_bytes()).hexdigest(),self.pins[case['id']]);packet=json.loads(draft.read_bytes())
                b=[str(src),'--form','5','--draft',str(draft),'--base',self.base,'--target',packet['target'],'--preserve-layout','--source-sha256',hashlib.sha256(self.raw).hexdigest(),'--replacement-source',str(frag),'--callee-context','--output',str(out)]
                code,r=self.call(export_cli,b);self.assertEqual(code,0);self.assertEqual(r['callee_context_base'],self.base);self.assertEqual(out.read_bytes(),self.raw.replace(b'diff(x,2)',case['named'].encode()))
                self.assertEqual(e.wide.form.decode(out.read_bytes()),packet['program']);self.assertEqual(self.call(export_cli,b)[0],2);self.assertEqual(self.call(edit_cli,a)[0],2)
                self.assertEqual(src.read_bytes(),self.raw);self.assertEqual(frag.read_bytes(),self.fragment(case['named']))
    def test_unicode_crlf_interior(self):
        fragment=self.fragment('diff(b:4, // заметка\r\n a:9)');packet=e.wide.replace_in_context(self.raw,fragment,base_sha256=self.base,function_sha256=self.pin)
        args=dict(base_sha256=self.base,target_sha256=packet['target'],source_sha256=hashlib.sha256(self.raw).hexdigest())
        out=e.export_source_with_contextual_fragment_layout(self.raw,packet,fragment,**args)
        self.assertEqual(out,self.raw.replace(b'diff(x,2)','diff(b:4, // заметка\r\n a:9)'.encode()))
        with self.assertRaises(e.wide.form.FormError):e.export_source_with_fragment_layout(self.raw,packet,fragment,**args)
        for bad in [self.fragment('diff(b:5,a:9)'),self.fragment('diff(b:4,a:9)').replace(b'entry main;',b'entry main; fn extra() -> Int64 = 1;')]:
            with self.assertRaises(e.DraftError):e.export_source_with_contextual_fragment_layout(self.raw,packet,bad,**args)
        for key in args:
            with self.assertRaises(e.DraftError):e.export_source_with_contextual_fragment_layout(self.raw,packet,fragment,**{**args,key:'0'*64})
    def test_usage_before_read(self):
        with patch.object(edit_cli.transport,'read_input',side_effect=AssertionError('must not read')):
            for operation,form in [('context','5'),('extract','5'),('replace','4')]:
                c,r=self.call(edit_cli,[operation,'missing','--form',form,'--callee-context','--output','unused']);self.assertEqual(c,2);self.assertEqual(r['error']['code'],'TOOL_USAGE')
            base=['missing','--draft','missing','--base','0'*64,'--target','0'*64,'--callee-context','--output','unused']
            for flags in [[],['--form','5'],['--form','5','--preserve-layout','--source-sha256','0'*64],['--form','4','--preserve-layout','--source-sha256','0'*64,'--replacement-source','missing']]:
                c,r=self.call(export_cli,base+flags);self.assertEqual(c,2);self.assertEqual(r['error']['code'],'TOOL_USAGE')
    def test_complete_output_bound(self):
        raw=self.raw.replace(b'program {',b'program {\n//'+b'x'*2048+b'\n');fragment=self.fragment('diff(b:4, // '+ 'y'*100+'\n a:9)');fragment=fragment.replace(b'y'*100,b'y'*(e.wide.form.old.BYTE_LIMIT-len(fragment)))
        packet=e.wide.replace_in_context(raw,fragment,base_sha256=self.base,function_sha256=self.pin)
        with self.assertRaises(e.DraftError) as err:e.export_source_with_contextual_fragment_layout(raw,packet,fragment,base_sha256=self.base,target_sha256=packet['target'],source_sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(err.exception.code,'EXPORT_BOUNDS')
if __name__=='__main__':unittest.main()
