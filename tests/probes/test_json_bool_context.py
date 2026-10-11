"""Finite read-only function context and original-body ownership checks."""
from pathlib import Path
import contextlib, hashlib, io, json, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
import bagaev_record_json_bool_context as context
import record_function as cli
SOURCE='bagaev record-form/6; program { entry main; fn project(x: Json, fallback: Bool) -> Bool = json.bool_or(x, fallback); fn main(x: Json) -> Bool = project(fallback: false, // comment é\n x: x); }'
class JsonBoolContext(unittest.TestCase):
 def test_fragment_and_direct_signatures(self):
  packet=context.context(SOURCE,'main');part=context.form.decode(packet['fragment']['source'])
  self.assertEqual(part['schema'],'bagaev-typed-record/12');self.assertEqual(set(part['functions']),{'main'})
  self.assertEqual(part['functions']['main']['body'],['call','project',['arg','x'],['bool',False]])
  self.assertEqual(packet['callees'],[{'name':'project','declared':True,'params':[['x','Json'],['fallback','Bool']],'result':'Bool','function_sha256':context.digest(context.form.decode(SOURCE)['functions']['project'])}])
  self.assertEqual(packet['callers'],[])
  self.assertEqual([c['name'] for c in context.context(SOURCE,'project')['callers']],['main'])
  self.assertFalse(packet['semantic_check']);self.assertFalse(packet['execution_admission'])
 def test_original_body_exact_bytes_and_detached_results(self):
  packet=context.source_context(SOURCE,'main');body='project(fallback: false, // comment é\n x: x)'
  self.assertEqual(packet['schema'],'bagaev-function-context/4');self.assertEqual(packet['original_body']['text'],body)
  self.assertEqual(packet['original_body']['sha256'],hashlib.sha256(body.encode()).hexdigest())
  loc=packet['original_body']['location'];self.assertEqual(SOURCE.encode()[loc['start_byte']:loc['end_byte']],body.encode())
  self.assertEqual(packet['original_body']['source_sha256'],hashlib.sha256(SOURCE.encode()).hexdigest())
  packet['callees'][0]['params'][0][0]='changed'
  self.assertEqual(context.context(SOURCE,'main')['callees'][0]['params'][0][0],'x')
 def test_missing_and_version_refusal(self):
  with self.assertRaises(context.DraftError) as e:context.fragment(SOURCE,'missing')
  self.assertEqual(e.exception.code,'FUNCTION_NAME')
  with self.assertRaises(context.form.FormError):context.context(SOURCE.replace('/6;','/5;'),'main')
 def test_cli_context_and_unsupported_replace(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);source=d/'source';source.write_text(SOURCE)
   for i,extra in enumerate([[],['--locations'],['--source-body']]):
    out=d/str(i);capture=io.StringIO()
    with contextlib.redirect_stdout(capture):code=cli.main(['context',str(source),'--form','6','--name','main','--output',str(out),*extra])
    self.assertEqual(code,0);self.assertTrue(json.loads(capture.getvalue())['ok'])
    self.assertEqual(json.loads(out.read_bytes())['fragment']['form'],'record-form/6')
   missing=str(d/'missing');out=d/'replace';capture=io.StringIO()
   with contextlib.redirect_stdout(capture):code=cli.main(['replace',missing,'--form','6','--callee-context','--replacement',missing,'--base','0'*64,'--function-pin','0'*64,'--output',str(out)])
   self.assertEqual(code,2);self.assertEqual(json.loads(capture.getvalue())['error']['code'],'TOOL_USAGE');self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
