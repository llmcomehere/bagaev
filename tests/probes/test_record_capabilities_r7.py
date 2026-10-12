"""Explicit discovery delta for reviewed form6 layout and node tools."""
from pathlib import Path
import json,sys,subprocess,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_capabilities as c
class Discovery(unittest.TestCase):
 def test_only_declared_delta(self):
  old=c.describe_v6('6');new=c.describe_v7('6')
  self.assertEqual(new['schema'],'bagaev-record-capabilities/7')
  for key in old:
   if key not in ['schema','unsupported_options','readable_editing','source_debugging']:self.assertEqual(old[key],new[key])
  self.assertFalse(old['readable_editing']['layout_export']['supported']);self.assertTrue(new['readable_editing']['layout_export']['supported'])
  self.assertIn('record_export.py --replacement-source',new['unsupported_options'])
  self.assertNotIn('record_export.py --preserve-layout',new['unsupported_options'])
  self.assertEqual(new['source_debugging']['checked_inspector_source'],'examples/probes/backend/rust/json_source_locations12.rs')
  self.assertTrue((T/new['source_debugging']['checked_inspector_source']).is_file())
  self.assertFalse(new['source_debugging']['native_output_authenticated']);self.assertFalse(new['execution_admission'])
 def test_explicit_cli_and_detachment(self):
  def cli(form):return subprocess.run([sys.executable,'-B',str(T/'tools/record_capabilities.py'),'--form',form,'--revision','7'],capture_output=True,timeout=10)
  p=cli('6');self.assertEqual(p.returncode,0);self.assertEqual(p.stderr,b'');self.assertEqual(json.loads(p.stdout),c.describe_v7('6'))
  for form in ['4','5']:
   p=cli(form);self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout)['error']['code'],'TOOL_USAGE')
  v=c.describe_v7('6');v['readable_editing']['layout_export']['supported']=False
  self.assertTrue(c.describe_v7('6')['readable_editing']['layout_export']['supported'])
if __name__=='__main__':unittest.main()
