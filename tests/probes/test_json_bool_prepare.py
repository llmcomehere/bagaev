"""Explicit form6 preparation controls, no compiler or runtime launch."""
from pathlib import Path
import hashlib,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import record_json_prepare as q
class JsonBoolPreparation(unittest.TestCase):
 def test_form6_preserves_numeric_lexemes_and_boolean_values(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);src=d/'source';args=d/'args';out=d/'out'
   src.write_text('bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = json.bool_or(x, false); }')
   raw=b' \n[ {"true":true,"false":false,"fraction":1.00,"exponent":1e+3,"negativezero":-0,"large":9223372036854775808} ]\t';args.write_bytes(raw)
   report=q.prepare([str(src),'--form','6','--arguments',str(args),'--output',str(out)])
   wire=out.read_bytes();self.assertTrue(wire.endswith(b',"arguments":'+raw+b'}'))
   self.assertEqual(json.loads(wire)['schema'],'bagaev-typed-record-invocation/12')
   self.assertEqual(json.loads(wire)['program']['schema'],'bagaev-typed-record/12')
   self.assertEqual(report['arguments_sha256'],hashlib.sha256(raw).hexdigest())
   self.assertFalse(report['semantic_check']);self.assertFalse(report['execution_admission'])
   with self.assertRaises(q.transport.Refusal):q.prepare([str(src),'--form','6','--arguments',str(args),'--output',str(out)])
   self.assertEqual(out.read_bytes(),wire)
 def test_explicit_versions_and_typed_entry_refuse(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);src=d/'source';args=d/'args';args.write_text('[true]');out=d/'out'
   for declared,selected in [('5','6'),('6','5'),('4','6'),('6','4')]:
    src.write_text('bagaev record-form/'+declared+'; program { entry main; fn main(x: Json) -> Bool = true; }')
    with self.assertRaises(q.transport.form.FormError):q.prepare([str(src),'--form',selected,'--arguments',str(args),'--output',str(out)])
    self.assertFalse(out.exists())
   src.write_text('bagaev record-form/6; program { entry main; fn main(x: Bool) -> Bool = x; }')
   with self.assertRaises(q.transport.Refusal) as e:q.prepare([str(src),'--form','6','--arguments',str(args),'--output',str(out)])
   self.assertEqual(e.exception.code,'JSON_ENTRY');self.assertFalse(out.exists())
 def test_real_application_prepares_without_changing_inputs(self):
  source=ROOT/'examples/probes/json-active-total/ActiveJson.bagaev'
  cases=json.loads((source.parent/'cases.json').read_text())+json.loads((source.parent/'lexical-cases.json').read_text())
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder)
   for i,c in enumerate(cases):
    payload=c['raw_input'] if 'raw_input' in c else json.dumps(c['input'],separators=(',',':'))
    raw=('['+payload+']').encode();args=d/('args'+str(i));args.write_bytes(raw);out=d/('out'+str(i))
    q.prepare([str(source),'--form','6','--arguments',str(args),'--output',str(out)])
    self.assertTrue(out.read_bytes().endswith(b',"arguments":'+raw+b'}'));self.assertEqual(args.read_bytes(),raw)
if __name__=='__main__':unittest.main()
