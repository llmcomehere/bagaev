"""Literal outside-body preservation and refusal controls; no runtime calls."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
T=Path(__file__).resolve().parents[2];sys.path[:0]=[str(T/'src'),str(T/'tools')]
import bagaev_record_json_bool_change as c
import record_export as cli
PREFIX='bagaev record-form/6;\r\n// keep é\r\nprogram { entry main; fn helper() -> Bool = false;\r\n fn main(x: Json) -> Bool = '
SUFFIX='; // retained tail\r\n}\r\n'
SOURCE=(PREFIX+'json.bool_or( x, false)'+SUFFIX).encode()
FRAGMENT='bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = json.bool_or(x, true); }'
class Layout(unittest.TestCase):
 def setUp(self):
  p=c.form.decode(SOURCE);self.base=c.digest(p);self.packet=c.replace(SOURCE,FRAGMENT,base_sha256=self.base,function_sha256=c.digest(p['functions']['main']))
  self.kw=dict(base_sha256=self.base,target_sha256=self.packet['target'],source_sha256=hashlib.sha256(SOURCE).hexdigest())
 def test_exact_preservation(self):
  result=c.export_source_preserving_layout(SOURCE,self.packet,**self.kw)
  self.assertTrue(result.startswith(PREFIX.encode()));self.assertTrue(result.endswith(SUFFIX.encode()))
  self.assertEqual(c.form.decode(result),self.packet['program']);self.assertEqual(c.form.decode(SOURCE)['functions']['main']['body'][-1],['bool',False])
 def test_layout_and_packet_refusals(self):
  for original,packet,kw,code in [(SOURCE+b' ',self.packet,self.kw,'EXPORT_SOURCE'),(SOURCE,self.packet,dict(self.kw,source_sha256='bad'),'EXPORT_PIN'),(SOURCE,dict(self.packet,execution_admission=0),self.kw,'EXPORT_PACKET'),(SOURCE,self.packet,dict(self.kw,target_sha256='0'*64),'EXPORT_TARGET')]:
   with self.assertRaises(c.DraftError) as e:c.export_source_preserving_layout(original,packet,**kw)
   self.assertEqual(e.exception.code,code)
 def test_inside_body_comment_may_be_replaced(self):
  source=SOURCE.replace(b'json.bool_or( x, false)',b'json.bool_or( // body comment\n x, false)')
  result=c.export_source_preserving_layout(source,self.packet,**dict(self.kw,source_sha256=hashlib.sha256(source).hexdigest()))
  self.assertTrue(result.startswith(PREFIX.encode()));self.assertTrue(result.endswith(SUFFIX.encode()))
  self.assertNotIn(b'body comment',result);self.assertEqual(c.form.decode(result),self.packet['program'])
 def test_cli_and_exclusive_output(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);s=d/'source';p=d/'packet';o=d/'output';s.write_bytes(SOURCE);p.write_text(json.dumps(self.packet))
   args=[str(s),'--form','6','--draft',str(p),'--base',self.base,'--target',self.packet['target'],'--preserve-layout','--source-sha256',self.kw['source_sha256'],'--output',str(o)]
   def call(a):
    out=io.StringIO()
    with contextlib.redirect_stdout(out):status=cli.main(a)
    return status,json.loads(out.getvalue())
   status,receipt=call(args);self.assertEqual(status,0);self.assertEqual(receipt['preservation_scope'],'outside-changed-function-body')
   saved=o.read_bytes();self.assertEqual(call(args)[1]['error']['code'],'RECORD_PATH');self.assertEqual(o.read_bytes(),saved);self.assertEqual(s.read_bytes(),SOURCE)
   for extra in [['--replacement-source','absent'],['--callee-context']]:self.assertEqual(call(args+extra)[1]['error']['code'],'TOOL_USAGE')
if __name__=='__main__':unittest.main()
