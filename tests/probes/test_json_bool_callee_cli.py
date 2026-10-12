"""Explicit form6 CLI transport around the pinned-callee pure API."""
from pathlib import Path
import contextlib,io,json,sys,tempfile,unittest
from unittest.mock import patch
T=Path(__file__).resolve().parents[2];sys.path[:0]=[str(T/'src'),str(T/'tools')]
import bagaev_record_json_bool_callee as c
import record_function as cli
from test_json_bool_callee import SOURCE,REPLACEMENT
class ContextCli(unittest.TestCase):
 def call(self,args):
  out=io.StringIO()
  with contextlib.redirect_stdout(out):status=cli.main(args)
  return status,json.loads(out.getvalue())
 def test_packet_receipt_and_exclusive_output(self):
  p=c.form.decode(SOURCE);base=c.digest(p);pin=c.digest(p['functions']['main'])
  wanted=c.replace_in_context(SOURCE,REPLACEMENT,base_sha256=base,function_sha256=pin)
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);source=d/'original';replacement=d/'fragment';output=d/'draft';source.write_text(SOURCE);replacement.write_text(REPLACEMENT)
   args=['replace',str(source),'--form','6','--callee-context','--replacement',str(replacement),'--base',base,'--function-pin',pin,'--output',str(output)]
   status,receipt=self.call(args);self.assertEqual(status,0);self.assertEqual(receipt['callee_context_base'],base);self.assertFalse(receipt['execution_admission']);self.assertFalse(receipt['semantic_check'])
   self.assertEqual(json.loads(output.read_bytes()),wanted);saved=output.read_bytes()
   self.assertEqual(self.call(args)[1]['error']['code'],'RECORD_PATH');self.assertEqual(output.read_bytes(),saved)
   self.assertEqual(source.read_text(),SOURCE);self.assertEqual(replacement.read_text(),REPLACEMENT)
 def test_invalid_modes_before_input(self):
  with patch.object(cli.transport,'read_input',side_effect=AssertionError('must not read')):
   for operation,form in [('context','6'),('extract','6'),('replace','4')]:
    status,receipt=self.call([operation,'missing','--form',form,'--callee-context','--output','unused'])
    self.assertEqual(status,2);self.assertEqual(receipt['error']['code'],'TOOL_USAGE')
 def test_pin_refusals_without_output(self):
  p=c.form.decode(SOURCE);base=c.digest(p);pin=c.digest(p['functions']['main'])
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);s=d/'s';r=d/'r';o=d/'o';s.write_text(SOURCE);r.write_text(REPLACEMENT)
   for b,f,code in [('0'*64,pin,'FUNCTION_BASE'),(base,'0'*64,'FUNCTION_PIN')]:
    status,receipt=self.call(['replace',str(s),'--form','6','--callee-context','--replacement',str(r),'--base',b,'--function-pin',f,'--output',str(o)])
    self.assertEqual(status,2);self.assertEqual(receipt['error']['code'],code);self.assertFalse(o.exists())
if __name__=='__main__':unittest.main()
