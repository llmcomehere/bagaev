"""Portable data checks for captured JSON application observations; no execution."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_json_bool_form import decode,encode,encode_named
from active_total_reference import total
D=ROOT/'examples/probes/json-active-total'
class JsonActiveTotal(unittest.TestCase):
 def test_frozen_cases_and_baseline(self):
  pins={'cases.json':'79abf0571eb3eca545f8cadd7f77fc6bf0b4f53e253979638511cac9ac1a17dd','lexical-cases.json':'5e94b544309160114598c170033102f5c2f280c24a417d9d148d49575ac58973'}
  cases=[]
  for name,pin in pins.items():
   raw=(D/name).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),pin);cases.extend(json.loads(raw))
  self.assertEqual(len(cases),23)
  for c in cases:
   x=json.loads(c['raw_input']) if 'raw_input' in c else c['input'];before=copy.deepcopy(x)
   try:r=total(x,active_only=True);r={k:r[k] for k in ('status','value')}
   except ValueError:r={'status':'invalid-input','value':None}
   self.assertEqual(r,c['expected'],c['name']);self.assertEqual(x,before)
 def test_source_and_observation_bindings(self):
  source=(D/'ActiveJson.bagaev').read_bytes();p=decode(source);s=json.loads((D/'observations.json').read_text())
  self.assertEqual(s['source_sha256'],hashlib.sha256(source).hexdigest())
  self.assertEqual(decode(encode(p)),p);self.assertEqual(decode(encode_named(p)),p)
  self.assertEqual(s['reference_calls'],23);self.assertEqual(s['native_calls'],0);self.assertEqual(s['status'],'PASS')
  cases=json.loads((D/'cases.json').read_text())+json.loads((D/'lexical-cases.json').read_text())
  self.assertEqual([c['name'] for c in cases],[r['case'] for r in s['rows']])
  for c,row in zip(cases,s['rows']):
   self.assertTrue(row['business_match']);self.assertEqual(row['baseline'],c['expected']);r=row['result']
   self.assertEqual(r['schema'],'bagaev-typed-record-result/12');self.assertIs(type(r['work']),int)
   if c['expected']['status']=='integer-overflow':
    self.assertEqual(r['status'],'integer-overflow');self.assertEqual(r['reason'],'RR_OVERFLOW');self.assertIsNone(r['value'])
   else:
    self.assertEqual(r['status'],'success');self.assertEqual(r['value_type'],'Record:Outcome');v=r['value']
    self.assertIs(type(v['valid']),bool);self.assertIs(type(v['total']),int)
    self.assertEqual(v,{'valid':c['expected']['status']=='success','total':c['expected']['value'] if c['expected']['status']=='success' else 0})
if __name__=='__main__':unittest.main()
