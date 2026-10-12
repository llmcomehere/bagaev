"""Frozen explicit authored export transport, no runtime execution."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
from unittest.mock import patch
T=Path(__file__).resolve().parents[2];sys.path[:0]=[str(T/'src'),str(T/'tools')]
import record_export as cli
from test_json_bool_authored import a,SOURCE,FRAGMENT,PREFIX,EXPRESSION,SUFFIX
class AuthoredCli(unittest.TestCase):
 def call(self,args):
  output=io.StringIO()
  with contextlib.redirect_stdout(output):status=cli.main(args)
  return status,json.loads(output.getvalue())
 def prepare(self,d):
  p=a.form.decode(SOURCE);base=a.digest(p)
  packet=a.replace_in_context(SOURCE,FRAGMENT,base_sha256=base,function_sha256=a.digest(p['functions']['main']))
  (d/'s').write_bytes(SOURCE.encode());(d/'f').write_bytes(FRAGMENT.encode());(d/'p').write_text(json.dumps(packet))
  return [str(d/'s'),'--draft',str(d/'p'),'--base',base,'--target',packet['target'],'--form','6','--output',str(d/'o'),'--preserve-layout','--source-sha256',hashlib.sha256(SOURCE.encode()).hexdigest(),'--replacement-source',str(d/'f'),'--callee-context']
 def test_exact_output_receipt_and_exclusive_path(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);args=self.prepare(d);inputs={n:(d/n).read_bytes() for n in ['s','f','p']}
   status,r=self.call(args);self.assertEqual(status,0)
   expected=(PREFIX+EXPRESSION+SUFFIX).encode();self.assertEqual((d/'o').read_bytes(),expected)
   self.assertEqual(r['source_sha256'],hashlib.sha256(expected).hexdigest())
   self.assertEqual(r['replacement_source_sha256'],hashlib.sha256(FRAGMENT.encode()).hexdigest())
   self.assertEqual(r['preservation_scope'],'outside-changed-function-body-and-authored-expression')
   self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission'])
   self.assertEqual(self.call(args)[1]['error']['code'],'RECORD_PATH');self.assertEqual((d/'o').read_bytes(),expected)
   self.assertEqual({n:(d/n).read_bytes() for n in inputs},inputs)
 def test_invalid_selectors_before_reads(self):
  common=['missing','--draft','missing','--base','0'*64,'--target','0'*64,'--output','unused']
  modes=[['--form','6','--callee-context'],['--form','6','--preserve-layout','--source-sha256','0'*64,'--replacement-source','missing'],['--form','6','--replacement-source','missing','--callee-context'],['--form','6','--preserve-layout','--replacement-source','missing','--callee-context'],['--form','4','--preserve-layout','--source-sha256','0'*64,'--replacement-source','missing','--callee-context']]
  with patch.object(cli.transport,'read_input',side_effect=AssertionError('must not read')):
   for mode in modes:
    status,r=self.call(common+mode);self.assertEqual(status,2);self.assertEqual(r['error']['code'],'TOOL_USAGE')
 def test_exact_refusals_without_output(self):
  for kind,code in [('source','EXPORT_SOURCE'),('contradiction','EXPORT_FRAGMENT'),('duplicate','FORM_DUPLICATE')]:
   with tempfile.TemporaryDirectory() as folder:
    d=Path(folder);args=self.prepare(d)
    if kind=='source':(d/'s').write_bytes(SOURCE.encode()+b' ')
    elif kind=='contradiction':(d/'f').write_text('bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = true; }')
    else:(d/'f').write_text(FRAGMENT.replace('fallback: true, a: x','a: x, a: x'))
    status,r=self.call(args);self.assertEqual(status,2);self.assertEqual(r['error']['code'],code);self.assertFalse((d/'o').exists())
if __name__=='__main__':unittest.main()
