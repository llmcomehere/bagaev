"""Literal occurrence/layout expectations for explicit form6."""
from pathlib import Path
import hashlib, json, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
import bagaev_record_json_bool_spans as spans
import bagaev_record_wide_spans as old
import record_source_map as cli
from bagaev_record_draft import digest
SOURCE='bagaev record-form/6; program { // é\n entry main; fn main(x: Json) -> Bool = json.bool_or(x, false); }'
class JsonBoolSpans(unittest.TestCase):
 def test_equal_literals_keep_distinct_occurrences(self):
  source=SOURCE.replace('json.bool_or(x, false)','if true then false else false')
  rows=spans.source_map(source)['locations']
  literals=[row for row in rows if row['program_pointer'].endswith(('/2','/3'))]
  self.assertEqual(len(literals),2)
  self.assertNotEqual(literals[0]['start_byte'],literals[1]['start_byte'])
  for row in literals:self.assertEqual(source.encode()[row['start_byte']:row['end_byte']],b'false')
 def test_exact_literals_and_layout_identity(self):
  result=spans.source_map(SOURCE);raw=SOURCE.encode()
  self.assertEqual(result['form'],'record-form/6')
  self.assertEqual(result['program_pin'],'sha256:'+digest(spans.form.decode(SOURCE)))
  self.assertEqual(result['source_sha256'],hashlib.sha256(raw).hexdigest())
  self.assertFalse(result['semantic_check']);self.assertFalse(result['execution_admission'])
  expected={'':'json.bool_or(x, false)','/1':'x','/2':'false'}
  rows={x['program_pointer'].removeprefix('/program/functions/main/body'):x for x in result['locations']}
  self.assertEqual(set(rows),set(expected));start=SOURCE.index(' = ')+3
  for key,fragment in expected.items():
   position=SOURCE.index(fragment,start);row=rows[key]
   self.assertEqual(row['start_byte'],len(SOURCE[:position].encode()))
   self.assertEqual(row['end_byte'],len(SOURCE[:position+len(fragment)].encode()))
   self.assertEqual(row['precision'],'exact-expression');self.assertEqual(row['start_line'],2)
   self.assertEqual(row['start_column'],position-SOURCE.rfind('\n',0,position))
  changed=spans.source_map(SOURCE.replace('// é','// 😀changed'))
  self.assertEqual(result['program_pin'],changed['program_pin']);self.assertNotEqual(result['source_sha256'],changed['source_sha256'])
 def test_old_profile_refusal_and_real_application(self):
  with self.assertRaises(spans.form.FormError):old.source_map(SOURCE)
  with self.assertRaises(spans.form.FormError):spans.source_map(SOURCE.replace('/6;','/5;'))
  source=(ROOT/'examples/probes/json-active-total/ActiveJson.bagaev').read_bytes()
  result=spans.source_map(source);rows=result['locations']
  self.assertEqual(len(rows),len({x['program_pointer'] for x in rows}));self.assertGreater(len(rows),20)
  self.assertIn('json.bool_or',{x['operation'] for x in rows})
  for row in rows:self.assertTrue(source[row['start_byte']:row['end_byte']].decode())
 def test_cli_pins_and_refusals_without_output(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);source=d/'source';source.write_text(SOURCE);out=d/'out'
   m=spans.source_map(SOURCE);base=[str(source),'--form','6','--program-pin',m['program_pin']]
   receipt=cli.create([*base,'--source-sha256',m['source_sha256'],'--pointer','/program/functions/main/body/2','--output',str(out)])
   self.assertEqual(receipt['location_count'],1);self.assertEqual(json.loads(out.read_bytes())['locations'][0]['operation'],'bool')
   for label,args in [('pin',[str(source),'--form','6','--program-pin','sha256:'+'0'*64]),('layout',base+['--source-sha256','0'*64]),('pointer',base+['--pointer','/absent'])]:
    target=d/label
    with self.assertRaises(cli.transport.Refusal):cli.create([*args,'--output',str(target)])
    self.assertFalse(target.exists())
if __name__=='__main__':unittest.main()
