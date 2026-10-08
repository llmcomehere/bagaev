"""Pinned named-callee context produces the frozen positional draft data."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_function as e
D=T/'examples/probes/contextual-fragment'
class ContextualFragment(unittest.TestCase):
    def setUp(self):
        self.v=json.loads((D/'cases.json').read_bytes());self.old=e.form.decode(self.v['original']);self.base=e.digest(self.old);self.pin=e.digest(self.old['functions']['main'])
    def fragment(self,expr):return 'bagaev record-form/5; program { entry main; fn main(x: Int64) -> Int64 = '+expr+'; }'
    def apply(self,source,**kw):return e.replace_in_context(self.v['original'],source,**dict(base_sha256=kw.get('base',self.base),function_sha256=kw.get('pin',self.pin)))
    def test_frozen_graph_packets(self):
        pins=json.loads((D/'packets.json').read_bytes())
        for c in self.v['cases']:
            named=self.fragment(c['named']);packet=self.apply(named);ordinary=e.replace(self.v['original'],self.fragment(c['positional']),base_sha256=self.base,function_sha256=self.pin)
            self.assertEqual(packet,ordinary);self.assertEqual(packet['program']['functions']['main']['body'],c['body'])
            self.assertEqual(packet['program']['functions']['diff'],self.old['functions']['diff']);raw=json.dumps(packet,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode();self.assertEqual(hashlib.sha256(raw).hexdigest(),pins[c['id']])
            self.assertFalse(packet['semantic_check']);self.assertFalse(packet['execution_admission']);self.assertEqual(self.apply(named.encode()),packet)
    def test_old_mode_still_refuses(self):
        fragment=self.fragment('diff(b:4,a:9)')
        for f in [lambda:e.form.decode(fragment),lambda:e.replace(self.v['original'],fragment,base_sha256=self.base,function_sha256=self.pin)]:
            with self.assertRaises(e.form.FormError) as err:f()
            self.assertEqual(err.exception.code,'FORM_REFERENCE')
    def test_labels_scope_and_pins(self):
        for expr in ['diff(a:1)','diff(a:1,b:2,c:3)','diff(a:1,a:2)','missing(a:1,b:2)','diff(b:2,1)']:
            with self.assertRaises(e.form.FormError):self.apply(self.fragment(expr))
        for fragment in [self.fragment('diff(b:4,a:9)').replace('fn main(x: Int64)','fn main(y: Int64)'),self.fragment('diff(b:4,a:9)').replace('entry main;','entry main; record Extra { x: Int64 };'),self.fragment('diff(b:4,a:9)').replace('entry main;','entry main; fn diff(a: Int64,b: Int64) -> Int64 = a-b;')]:
            with self.assertRaises(e.DraftError):self.apply(fragment)
        with self.assertRaises(e.DraftError) as err:self.apply('invalid replacement',base='0'*64)
        self.assertEqual(err.exception.code,'FUNCTION_BASE')
        with self.assertRaises(e.DraftError) as err:self.apply(self.fragment('diff(b:4,a:9)'),pin='0'*64)
        self.assertEqual(err.exception.code,'FUNCTION_PIN')
    def test_declared_context_order_is_authoritative(self):
        original=self.v['original'].replace('diff(a: Int64,b: Int64)','diff(b: Int64,a: Int64)');program=e.form.decode(original)
        packet=e.replace_in_context(original,self.fragment('diff(b:4,a:9)'),base_sha256=e.digest(program),function_sha256=e.digest(program['functions']['main']))
        self.assertEqual(packet['program']['functions']['main']['body'],['call','diff',['int',4],['int',9]])
        with self.assertRaises(e.DraftError):e.replace_in_context(original,self.fragment('diff(b:4,a:9)'),base_sha256=self.base,function_sha256=self.pin)
if __name__=='__main__':unittest.main()
