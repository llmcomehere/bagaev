"""Frozen metadata delta for explicit contextual replacement."""
from pathlib import Path
import json,sys,subprocess,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_capabilities as c
class Discovery(unittest.TestCase):
 def test_exact_delta(self):
  old=c.describe_v7('6');new=c.describe_v8('6')
  self.assertEqual(new.pop('schema'),'bagaev-record-capabilities/8');old.pop('schema')
  route=new['readable_editing'].pop('contextual_replacement')
  self.assertEqual(route['operation'],'replace');self.assertEqual(route['form_flag_value'],'6')
  self.assertEqual(route['required_flags'],['--form','--callee-context','--replacement','--base','--function-pin','--output'])
  self.assertFalse(route['semantic_check']);self.assertFalse(route['execution_admission'])
  self.assertEqual(route['argument_order'],'parameter declaration order')
  old['unsupported_options'].remove('record_function.py --callee-context')
  old['unsupported_options'].extend(['record_function.py extract/context --callee-context','record_export.py --callee-context'])
  self.assertEqual(new,old)
 def test_cli_and_detachment(self):
  for form in ['4','5','6']:
   p=subprocess.run([sys.executable,'-B',str(T/'tools/record_capabilities.py'),'--form',form,'--revision','8'],capture_output=True,timeout=10)
   self.assertEqual(p.stderr,b'');value=json.loads(p.stdout)
   if form=='6':self.assertEqual(p.returncode,0);self.assertEqual(value,c.describe_v8('6'))
   else:self.assertEqual(p.returncode,2);self.assertEqual(value['error']['code'],'TOOL_USAGE')
  value=c.describe_v8('6');value['readable_editing']['contextual_replacement']['supported']=False
  self.assertTrue(c.describe_v8('6')['readable_editing']['contextual_replacement']['supported'])
  self.assertNotIn('contextual_replacement',c.describe_v7('6')['readable_editing'])
if __name__=='__main__':unittest.main()
