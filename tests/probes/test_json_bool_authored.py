"""Literal authored-expression bytes and contradiction refusals, data only."""
from pathlib import Path
import hashlib,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_json_bool_authored as a
PREFIX='bagaev record-form/6;\r\n// сохраняем\r\nprogram { entry main; fn helper(a: Json, fallback: Bool) -> Bool = json.bool_or(a, fallback); fn main(x: Json) -> Bool = '
SUFFIX='; }\r\n'
EXPRESSION='helper(\n // authored body: helper(x, false); }\n fallback: true, a: x)'
SOURCE=PREFIX+'helper(x, false)'+SUFFIX
FRAGMENT='bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = '+EXPRESSION+'; }'
class Authored(unittest.TestCase):
 def setUp(self):
  self.before=a.form.decode(SOURCE)
  self.kw=dict(base_sha256=a.digest(self.before),source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest())
  self.pin=a.digest(self.before['functions']['main'])
  self.packet=a.replace_in_context(SOURCE,FRAGMENT,base_sha256=self.kw['base_sha256'],function_sha256=self.pin)
  self.kw['target_sha256']=self.packet['target']
 def test_literal_bytes_and_graph(self):
  result=a.export_authored(SOURCE,self.packet,FRAGMENT,**self.kw)
  self.assertEqual(result,(PREFIX+EXPRESSION+SUFFIX).encode())
  self.assertEqual(a.form.decode(result)['functions']['main']['body'],['call','helper',['arg','x'],['bool',True]])
  self.assertEqual(a.form.decode(result)['functions']['helper'],self.before['functions']['helper'])
  self.assertEqual(a.export_authored(SOURCE.encode(),self.packet,FRAGMENT.encode(),**self.kw),result)
 def test_pins(self):
  for key,code in [('base_sha256','EXPORT_BASE'),('target_sha256','EXPORT_TARGET'),('source_sha256','EXPORT_SOURCE')]:
   with self.assertRaises(a.DraftError) as e:a.export_authored(SOURCE,self.packet,FRAGMENT,**dict(self.kw,**{key:'0'*64}))
   self.assertEqual(e.exception.code,code)
 def test_changed_contradictory_fragment(self):
  fragment='bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = true; }'
  other=a.replace_in_context(SOURCE,fragment,base_sha256=self.kw['base_sha256'],function_sha256=self.pin)
  self.assertNotEqual(other['target'],self.packet['target'])
  with self.assertRaises(a.DraftError) as e:a.export_authored(SOURCE,self.packet,fragment,**self.kw)
  self.assertEqual(e.exception.code,'EXPORT_FRAGMENT')
 def test_fragment_refusals(self):
  changes=[(FRAGMENT.replace('fallback: true','fallback: false'),'FUNCTION_NO_CHANGE'),(FRAGMENT.replace('fn main(x: Json)','fn main(x: Bool)'),'FUNCTION_SIGNATURE'),(FRAGMENT.replace('entry main;','entry main; fn extra() -> Bool = true;'),'FUNCTION_SCOPE'),(FRAGMENT.replace('fallback: true, a: x','a: x, a: x'),'FORM_DUPLICATE')]
  for fragment,code in changes:
   with self.assertRaises((a.DraftError,a.form.FormError)) as e:a.export_authored(SOURCE,self.packet,fragment,**self.kw)
   self.assertEqual(e.exception.code,code)
 def test_composed_output_byte_boundary(self):
  limit=a.form.prior.old.BYTE_LIMIT
  prefix=PREFIX.replace('// сохраняем','// '+'o'*(limit//2))
  expression='helper(// '+ '\n fallback: true, a: x)'
  count=limit-len((prefix+expression+SUFFIX).encode())
  self.assertGreater(count,0)
  source=prefix+'helper(x, false)'+SUFFIX
  kw=dict(self.kw,source_sha256=hashlib.sha256(source.encode()).hexdigest())
  for extra in [0,1]:
   body=expression.replace('// ','// '+'a'*(count+extra),1)
   fragment='bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = '+body+'; }'
   expected=(prefix+body+SUFFIX).encode()
   self.assertLess(len(source.encode()),limit);self.assertLess(len(fragment.encode()),limit)
   self.assertEqual(len(expected),limit+extra)
   if extra:
    with self.assertRaises(a.DraftError) as e:a.export_authored(source,self.packet,fragment,**kw)
    self.assertEqual(e.exception.code,'EXPORT_BOUNDS')
   else:self.assertEqual(a.export_authored(source,self.packet,fragment,**kw),expected)
if __name__=='__main__':unittest.main()
