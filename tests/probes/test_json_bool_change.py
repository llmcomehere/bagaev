"""Frozen focused-change data expectations, no runtime calls."""
from pathlib import Path
import contextlib,copy,io,json,sys,tempfile,unittest
P=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(P/'src'))
sys.path.insert(0,str(P/'tools'))
import bagaev_record_json_bool_change as change
import record_function as function_cli
import record_export as export_cli
SOURCE='bagaev record-form/6; program { entry main; fn helper() -> Bool = false; fn main(x: Json) -> Bool = json.bool_or(x, false); }'
REPLACEMENT='bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = json.bool_or(x, true); }'
class FocusedChange(unittest.TestCase):
 def setUp(self):
  self.before=change.form.decode(SOURCE);self.base=change.digest(self.before);self.pin=change.digest(self.before['functions']['main'])
 def packet(self):return change.replace(SOURCE,REPLACEMENT,base_sha256=self.base,function_sha256=self.pin)
 def test_literal_delta_and_canonical_export(self):
  expected=copy.deepcopy(self.before);expected['functions']['main']['body']=['json.bool_or',['arg','x'],['bool',True]]
  packet=self.packet()
  self.assertEqual(packet,{'schema':'bagaev-record-draft/2','status':'draft','base':self.base,'target':change.digest(expected),'program':expected,'delta':{'add':[],'replace':['main']},'semantic_check':False,'execution_admission':False})
  out=change.export_source(SOURCE,packet,base_sha256=self.base,target_sha256=packet['target'])
  self.assertEqual(change.form.decode(out),expected);self.assertEqual(change.form.decode(SOURCE),self.before)
 def test_base_pin_scope_signature_and_noop(self):
  cases=[(REPLACEMENT,'0'*64,self.pin,'FUNCTION_BASE'),(REPLACEMENT,self.base,'0'*64,'FUNCTION_PIN'),
   (REPLACEMENT.replace('true','false'),self.base,self.pin,'FUNCTION_NO_CHANGE'),
   (REPLACEMENT.replace('x: Json','x: Bool'),self.base,self.pin,'FUNCTION_SIGNATURE'),
   (REPLACEMENT.replace('entry main;','entry main; fn extra() -> Bool = false;'),self.base,self.pin,'FUNCTION_SCOPE')]
  for source,base,pin,code in cases:
   with self.assertRaises(change.DraftError) as e:change.replace(SOURCE,source,base_sha256=base,function_sha256=pin)
   self.assertEqual(e.exception.code,code)
 def test_forged_packets_and_pin_refusals(self):
  for key,value in [('schema','bagaev-record-draft/1'),('execution_admission',0),('semantic_check',True),('extra',True),('delta',{'add':['helper'],'replace':[]})]:
   p=self.packet();p[key]=value
   with self.assertRaises(change.DraftError) as e:change.export_source(SOURCE,p,base_sha256=self.base,target_sha256=p['target'])
   self.assertEqual(e.exception.code,'EXPORT_PACKET')
  p=self.packet()
  for base,target,code in [('bad',p['target'],'EXPORT_PIN'),('0'*64,p['target'],'EXPORT_BASE'),(self.base,'0'*64,'EXPORT_TARGET')]:
   with self.assertRaises(change.DraftError) as e:change.export_source(SOURCE,p,base_sha256=base,target_sha256=target)
   self.assertEqual(e.exception.code,code)
 def test_multi_body_and_signature_refuse(self):
  for mutation,code in [('body','EXPORT_SCOPE'),('signature','FUNCTION_SIGNATURE')]:
   p=self.packet()
   if mutation=='body':p['program']['functions']['helper']['body']=['bool',True]
   else:p['program']['functions']['main']['params']=[['x','Bool']]
   p['target']=change.digest(p['program'])
   with self.assertRaises(change.DraftError) as e:change.export_source(SOURCE,p,base_sha256=self.base,target_sha256=p['target'])
   self.assertEqual(e.exception.code,code)
 def test_two_tool_path_and_output_exclusivity(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);original=d/'original';fragment=d/'fragment';packet=d/'packet';out=d/'out'
   original.write_text(SOURCE);fragment.write_text(REPLACEMENT)
   def call(tool,args):
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):code=tool.main(args)
    return code,json.loads(capture.getvalue())
   args=['replace',str(original),'--form','6','--replacement',str(fragment),'--base',self.base,'--function-pin',self.pin,'--output',str(packet)]
   self.assertEqual(call(function_cli,args)[0],0);expected=self.packet();self.assertEqual(json.loads(packet.read_bytes()),expected)
   export=[str(original),'--form','6','--draft',str(packet),'--base',self.base,'--target',expected['target'],'--output',str(out)]
   code,receipt=call(export_cli,export);self.assertEqual(code,0);self.assertEqual(receipt['form'],'record-form/6')
   self.assertEqual(change.form.decode(out.read_bytes()),expected['program']);saved=out.read_bytes()
   self.assertEqual(call(function_cli,args)[1]['error']['code'],'RECORD_PATH')
   self.assertEqual(call(export_cli,export)[1]['error']['code'],'RECORD_PATH');self.assertEqual(out.read_bytes(),saved)
   self.assertEqual(original.read_text(),SOURCE);self.assertEqual(fragment.read_text(),REPLACEMENT)
   target=d/'layout';bad=[str(d/'missing'),'--form','6','--draft',str(d/'missing'),'--base',self.base,'--target',expected['target'],'--preserve-layout','--source-sha256','0'*64,'--output',str(target)]
   # Canonical-body layout export is now supported; authored replacement is not.
   bad.extend(['--replacement-source',str(d/'missing')])
   self.assertEqual(call(export_cli,bad)[1]['error']['code'],'TOOL_USAGE');self.assertFalse(target.exists())
if __name__=='__main__':unittest.main()
