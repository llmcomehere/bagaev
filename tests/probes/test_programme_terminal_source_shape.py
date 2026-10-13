"""Pure envelope association refuses every non-string source before membership."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import bagaev_outcome_programme_image as envelope

class SourceShapeTests(unittest.TestCase):
 def image(self):
  pin='a'*64
  return {'schema':'owned-programmes-image/1','bootstrap':pin,
   'head':{'generation':0,'source':pin},'admissions':[],
   'runs':[{'id':'run','head':{'generation':0,'source':pin}}],
   'receiver':{'terminal':[{'intent':{'source':pin}}]}}
 def validate(self,value):
  return envelope.validate(value,bootstrap='a'*64,policy='b'*64,sources={'a'*64})
 def test_bound_string_is_detached(self):
  value=self.image();original=copy.deepcopy(value);result=self.validate(value)
  self.assertEqual(result,value);self.assertIsNot(result,value)
  result['receiver']['terminal'][0]['intent']['source']='changed'
  self.assertEqual(value,original)
 def test_invalid_source_shapes(self):
  for name,source in [('list',[]),('object',{}),('null',None),('bool',True),('integer',1),('unknown','c'*64),('missing',None)]:
   with self.subTest(name=name):
    value=self.image();intent=value['receiver']['terminal'][0]['intent']
    if name=='missing':intent.pop('source')
    else:intent['source']=source
    original=copy.deepcopy(value)
    with self.assertRaises(envelope.ProgrammeError) as caught:self.validate(value)
    self.assertEqual(caught.exception.code,'PROGRAMME_TERMINAL_SOURCE')
    self.assertEqual(value,original)

if __name__=='__main__':unittest.main()
