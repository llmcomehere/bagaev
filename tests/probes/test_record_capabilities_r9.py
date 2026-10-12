"""Exact authored-export discovery delta; no program execution."""
from pathlib import Path
import json,sys,subprocess,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_capabilities as c
class Discovery(unittest.TestCase):
 def test_exact_delta(self):
  old=c.describe_v8('6');new=c.describe_v9('6')
  self.assertEqual(new.pop('schema'),'bagaev-record-capabilities/9');old.pop('schema')
  self.assertEqual(new['readable_editing'].pop('authored_layout_export'),{
   'supported':True,'tool':'tools/record_export.py','form_flag_value':'6',
   'required_flags':['--form','--draft','--base','--target','--preserve-layout','--source-sha256','--replacement-source','--callee-context','--output'],
   'preservation':'exact authored expression and all outside-body bytes',
   'independent_draft_revalidated':True,'output':'fresh path only',
   'semantic_check':False,'execution_admission':False,'guide':'docs/form6-authored-layout.md'})
  for option in ['record_export.py --replacement-source','record_export.py --callee-context']:old['unsupported_options'].remove(option)
  self.assertEqual(new,old)
 def test_cli_and_detachment(self):
  for form in ['4','5','6']:
   r=subprocess.run([sys.executable,'-B',str(T/'tools/record_capabilities.py'),'--form',form,'--revision','9'],capture_output=True,timeout=10)
   self.assertEqual(r.stderr,b'');value=json.loads(r.stdout)
   if form=='6':self.assertEqual(r.returncode,0);self.assertEqual(value,c.describe_v9('6'))
   else:self.assertEqual(r.returncode,2);self.assertEqual(value['error']['code'],'TOOL_USAGE')
  value=c.describe_v9('6');value['readable_editing']['authored_layout_export']['required_flags'].clear()
  self.assertEqual(len(c.describe_v9('6')['readable_editing']['authored_layout_export']['required_flags']),9)
  self.assertNotIn('authored_layout_export',c.describe_v8('6')['readable_editing'])
if __name__=='__main__':unittest.main()
