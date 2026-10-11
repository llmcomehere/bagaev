"""Frozen focused named-callee expectations; data only, no execution."""
from pathlib import Path
import copy,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_json_bool_callee as c
from bagaev_record_draft import DraftError
SOURCE='bagaev record-form/6; program { entry main; fn helper(a: Json, fallback: Bool) -> Bool = json.bool_or(a, fallback); fn main(x: Json) -> Bool = helper(x, false); }'
REPLACEMENT='bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = helper(fallback: true, a: x); }'
class Context(unittest.TestCase):
 def setUp(self):
  self.before=c.form.decode(SOURCE);self.kw=dict(base_sha256=c.digest(self.before),function_sha256=c.digest(self.before['functions']['main']))
 def test_exact_declaration_order_and_detached_scope(self):
  expected=copy.deepcopy(self.before);expected['functions']['main']['body']=['call','helper',['arg','x'],['bool',True]]
  packet=c.replace_in_context(SOURCE,REPLACEMENT,**self.kw)
  self.assertEqual(packet['program'],expected);self.assertEqual(packet['delta'],{'add':[],'replace':['main']})
  self.assertEqual(packet['target'],c.digest(expected));self.assertFalse(packet['semantic_check']);self.assertFalse(packet['execution_admission'])
  self.assertEqual(c.form.decode(SOURCE),self.before)
  with self.assertRaises(c.form.FormError):c.replace(SOURCE,REPLACEMENT,**self.kw)
 def test_pins_scope_and_noop(self):
  cases=[(SOURCE,REPLACEMENT,dict(self.kw,base_sha256='0'*64),'FUNCTION_BASE'),
   (SOURCE.replace('a: Json, fallback: Bool','fallback: Bool, a: Json'),REPLACEMENT,self.kw,'FUNCTION_BASE'),
   (SOURCE,REPLACEMENT,dict(self.kw,function_sha256='0'*64),'FUNCTION_PIN'),
   (SOURCE,REPLACEMENT.replace('true','false'),self.kw,'FUNCTION_NO_CHANGE'),
   (SOURCE,REPLACEMENT.replace('x: Json','x: Bool'),self.kw,'FUNCTION_SIGNATURE'),
   (SOURCE,REPLACEMENT.replace('entry main;','entry main; fn extra() -> Bool = false;'),self.kw,'FUNCTION_SCOPE')]
  for original,part,kw,code in cases:
   with self.assertRaises(DraftError) as e:c.replace_in_context(original,part,**kw)
   self.assertEqual(e.exception.code,code)
 def test_named_argument_refusals(self):
  for body in ['helper(fallback: true, x)','helper(missing: true, a: x)','helper(a: x, a: x)','helper(a: x)','unknown(a: x, fallback: true)']:
   source=REPLACEMENT.replace('helper(fallback: true, a: x)',body)
   with self.assertRaises(c.form.FormError):c.replace_in_context(SOURCE,source,**self.kw)
if __name__=='__main__':unittest.main()
