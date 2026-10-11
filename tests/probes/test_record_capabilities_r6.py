"""Explicit profile12 discovery: literal route oracle, no runtime execution."""
from pathlib import Path
import hashlib,json,subprocess,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_capabilities as c
class Profile12Discovery(unittest.TestCase):
 def cli(self,*args):
  return subprocess.run([sys.executable,'-B',str(T/'tools/record_capabilities.py'),*args],capture_output=True,timeout=10)
 def test_explicit_identity_and_limits(self):
  v=c.describe_v6('6')
  self.assertEqual([v[x] for x in ['schema','form','program_schema','invocation_schema','result_schema']],
   ['bagaev-record-capabilities/6','record-form/6','bagaev-typed-record/12','bagaev-typed-record-invocation/12','bagaev-typed-record-result/12'])
  self.assertEqual(v['reference_bounds']['record_list_capacity'],16)
  self.assertIn({'name':'json.bool_or','arity':2},v['intrinsic_spellings'])
  self.assertNotIn('prepare',v['data_tools']['record_text.py'])
  self.assertEqual(v['unsupported_options'],['record_text.py prepare','record_text.py inspect --bounds','record_function.py --callee-context','record_export.py --preserve-layout'])
  self.assertFalse(v['readable_editing']['layout_export']['supported'])
  self.assertFalse(v['semantic_check']);self.assertFalse(v['execution_admission'])
 def test_exact_selected_routes(self):
  v=c.describe_v6('6');e=v['profile12_extensions'];n=v['native_preparation']
  self.assertEqual(n['binding_schema'],'bagaev-json-view12-llvm-binding/1');self.assertEqual(n['success_wire'],'BCMPRES4')
  self.assertEqual(e['prepared_reference']['evaluate'],'evaluate_prepared_json_v12')
  self.assertEqual(e['success_json_reader']['result_schema'],'bagaev-native-result/12')
  self.assertEqual(e['success_json_reader']['unbound_failure_packets'],'refused')
  self.assertFalse(e['success_json_reader']['origin_authenticated'])
  self.assertTrue(e['prepared_native']['separate_exact_kernel_admission_required'])
  self.assertNotIn('profile11_extensions',v)
  def walk(x):
   if isinstance(x,dict):
    for k,z in x.items():
     if k in ['guide','source','library','tool','emitter_source','map_tool']:self.assertTrue((T/z).is_file(),z)
     walk(z)
   elif isinstance(x,list):
    for z in x:walk(z)
  walk(v)
 def test_cli_determinism_and_detachment(self):
  a=self.cli('--form','6','--revision','6');b=self.cli('--form','6','--revision','6')
  self.assertEqual(a.returncode,0);self.assertEqual(a.stderr,b'');self.assertEqual(a.stdout,b.stdout)
  self.assertEqual(json.loads(a.stdout),c.describe_v6('6'))
  v=c.describe_v6('6');v['profile12_extensions']['prepared_native']['source']='mutated'
  self.assertNotEqual(c.describe_v6('6')['profile12_extensions']['prepared_native']['source'],'mutated')
 def test_newest_legacy_bytes_and_refusals(self):
  for f,h in [('4','ce1517a49877714311e45f3d5562c021484098ecba035de68a85b5faa40ecf8d'),('5','36fbbb732367b9e9f660ff466f0d1d6204ba3e4d0dbc280eb490be20e3c5e435')]:
   p=self.cli('--form',f,'--revision','5');self.assertEqual(p.returncode,0);self.assertEqual(hashlib.sha256(p.stdout).hexdigest(),h)
  for args in [('--form','6'),('--form','6','--revision','5'),('--form','5','--revision','6'),('--form','4','--revision','6'),('--form','6','--revision','6','--output','x')]:
   p=self.cli(*args);self.assertEqual(p.returncode,2);self.assertEqual(p.stderr,b'');self.assertEqual(json.loads(p.stdout)['error']['code'],'TOOL_USAGE')
  for f in ['4','5',6,None,True]:
   with self.assertRaises(c.narrow.FormError) as e:c.describe_v6(f)
   self.assertEqual(e.exception.code,'FORM_VERSION')
if __name__=='__main__':unittest.main()
