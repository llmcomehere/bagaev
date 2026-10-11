"""Form6 syntax/layout data checks; no evaluator invocation."""
from pathlib import Path
import contextlib, hashlib, io, json, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
import bagaev_record_json_bool_form as form
import bagaev_record_json_bool_diagnostics as diag
import bagaev_record_json_bool_format as fmt
import record_diagnose, record_format

SOURCE='bagaev record-form/6; program { // retained é\n entry main; fn pick(x: Json, fallback: Bool) -> Bool = json.bool_or(x, fallback); fn main(x: Json) -> Bool = pick(fallback: false, x: x); }'
class JsonBoolAuthoring(unittest.TestCase):
 def test_literal_diagnostics_and_old_version_span(self):
  result=diag.diagnose(SOURCE)
  self.assertEqual(result,{'schema':'record-form-diagnostic/1','form':'record-form/6','valid_form':True,'source_sha256':hashlib.sha256(SOURCE.encode()).hexdigest(),'semantic_check':False,'execution_admission':False,'error':None})
  old=SOURCE.replace('record-form/6','record-form/5');bad=diag.diagnose(old)
  self.assertEqual(bad['error'],{'code':'FORM_VERSION','phase':'header','span':{'kind':'token','start_byte':19,'end_byte':20,'start_line':1,'start_column':20,'end_line':1,'end_column':21}})
  unsupported=diag.diagnose(SOURCE.replace('json.bool_or','json.unknown'))
  # Unknown dotted names parse as single-payload variants; the second argument
  # is rejected while parsing, before lowering.
  self.assertFalse(unsupported['valid_form']);self.assertEqual(unsupported['error']['phase'],'parsing')
  with self.assertRaises(form.FormError) as e:form.decode(SOURCE.replace('json.bool_or','json.unknown'))
  self.assertEqual(unsupported['error']['code'],e.exception.code)
  missing=diag.diagnose(SOURCE.replace('pick(fallback:', 'absent(fallback:'))
  self.assertEqual(missing['error']['phase'],'lowering');self.assertEqual(missing['error']['code'],'FORM_REFERENCE')
 def test_transport_refusal_precedence(self):
  for value in [None,b'\xff','\ud800',b' '*1048576+b'\xff',' '*1048576+'\ud800']:
   result=diag.diagnose(value);self.assertEqual(result['error']['phase'],'transport');self.assertEqual(result['error']['code'],'FORM_SYNTAX')
  self.assertEqual(diag.diagnose(b' '*1048577)['error']['code'],'FORM_BOUNDS')
 def test_format_graph_comments_idempotence_and_width(self):
  application=(ROOT/'examples/probes/json-active-total/ActiveJson.bagaev').read_bytes()
  for source in [SOURCE,application]:
   for width in [None,40,80,120]:
    def format_it(value):return fmt.format_source(value) if width is None else fmt.format_source_wrapped(value,width=width)
    out=format_it(source)
    self.assertEqual(form.decode(out),form.decode(source));self.assertEqual(format_it(out),out)
    self.assertTrue(out.startswith(b'bagaev record-form/6;\n'))
    if source==SOURCE:self.assertIn('// retained é',out.decode());self.assertIn('fallback:',out.decode())
  for width in [True,39,121,80.0,'80']:
   with self.assertRaises(form.FormError) as e:fmt.format_source_wrapped(SOURCE,width=width)
   self.assertEqual(e.exception.code,'FORM_WIDTH')
 def test_cli_selection_and_exclusive_outputs(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);source=d/'source';source.write_text(SOURCE)
   for name,tool,extra in [('diagnose',record_diagnose,[]),('format',record_format,['--width','40'])]:
    out=d/name;args=[str(source),'--form','6','--output',str(out),*extra]
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):self.assertEqual(tool.main(args),0)
    self.assertTrue(json.loads(capture.getvalue())['ok']);saved=out.read_bytes()
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):self.assertEqual(tool.main(args),2)
    self.assertEqual(json.loads(capture.getvalue())['error']['code'],'RECORD_PATH');self.assertEqual(out.read_bytes(),saved)
   self.assertEqual(source.read_text(),SOURCE)
if __name__=='__main__':unittest.main()
