"""Reproduce the public synthetic application through two data CLI routes."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_json_bool_change as c
import bagaev_record_json_bool_spans as spans
E=T/'examples/probes/json-active-authoring'
class ApplicationAuthoring(unittest.TestCase):
 def test_cli_chain_and_refusals(self):
  pins=json.loads((E/'pins.json').read_bytes())
  source=T/'examples/probes/json-active-total/ActiveJson.bagaev';fragment=E/'Main.fragment.bagaev'
  original=source.read_bytes();part=fragment.read_bytes();before=c.form.decode(original)
  self.assertEqual(c.digest(before),pins['base']);self.assertEqual(hashlib.sha256(original).hexdigest(),pins['original_source_sha256'])
  def call(tool,args):
   r=subprocess.run([sys.executable,'-B',str(T/'tools'/tool),*args],capture_output=True,timeout=30)
   self.assertEqual(r.stderr,b'');return r.returncode,json.loads(r.stdout)
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);draft=d/'draft';output=d/'output'
   replace=['replace',str(source),'--form','6','--callee-context','--replacement',str(fragment),'--base',pins['base'],'--function-pin',c.digest(before['functions']['main']),'--output',str(draft)]
   status,r=call('record_function.py',replace);self.assertEqual(status,0);self.assertFalse(r['execution_admission']);self.assertFalse(r['semantic_check'])
   packet=json.loads(draft.read_bytes());self.assertEqual(packet['target'],pins['target']);self.assertEqual(packet['delta'],{'add':[],'replace':['main']})
   export=[str(source),'--form','6','--draft',str(draft),'--base',pins['base'],'--target',pins['target'],'--preserve-layout','--source-sha256',pins['original_source_sha256'],'--replacement-source',str(fragment),'--callee-context','--output',str(output)]
   status,r=call('record_export.py',export);self.assertEqual(status,0);self.assertFalse(r['execution_admission']);self.assertFalse(r['semantic_check'])
   saved=output.read_bytes();self.assertEqual(hashlib.sha256(saved).hexdigest(),pins['authored_successor_sha256'])
   after=c.form.decode(saved);self.assertEqual(c.digest(after),pins['target'])
   for name in before['functions']:
    if name!='main':self.assertEqual(after['functions'][name],before['functions'][name])
   row=[x for x in spans.source_map(original)['locations'] if x['program_pointer']=='/program/functions/main/body'][0]
   expression=part[part.index(b'if (true)'):part.rindex(b';')]
   self.assertEqual(saved,original[:row['start_byte']]+expression+original[row['end_byte']:])
   self.assertEqual(saved.count(b'input_shape(x: x)'),2);self.assertEqual(saved.count(b'active_sum(x: x)'),2)
   self.assertEqual(saved.count(b'// retained authored comment'),1)
   self.assertEqual(call('record_export.py',export)[1]['error']['code'],'RECORD_PATH');self.assertEqual(output.read_bytes(),saved)
   for tool,args,flag,code in [('record_function.py',replace,'--base','FUNCTION_BASE'),('record_export.py',export,'--source-sha256','EXPORT_SOURCE')]:
    bad=list(args);bad[bad.index(flag)+1]='0'*64;bad[bad.index('--output')+1]=str(d/'refused')
    status,r=call(tool,bad);self.assertEqual(status,2);self.assertEqual(r['error']['code'],code);self.assertFalse((d/'refused').exists())
  self.assertEqual(source.read_bytes(),original);self.assertEqual(fragment.read_bytes(),part)
if __name__=='__main__':unittest.main()
