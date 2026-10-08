"""Original body context is layout-bound data; no program execution."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
T=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tools'))
import bagaev_record_wide_function as edit
import record_function as cli
from unittest.mock import patch

class SourceBodyContext(unittest.TestCase):
    def test_frozen_old_packets(self):
        expected = {'small': {'context2': 'c45a81388226ab4044966593f78cf0589dc9c4a9e91eb95b6e43eb4c706bb262', 'context3': '5b0aa100aea341da21dd00c63e45045e15d28b2856326a33bbcf08d75306cefb'}, 'small-crlf': {'context2': 'c45a81388226ab4044966593f78cf0589dc9c4a9e91eb95b6e43eb4c706bb262', 'context3': '264cb6003d6be479899ed643ea3a1ad4f44cacb38b160d78711b2eb24414b396'}, 'batch': {'context2': 'a5ed6e0d1fa605eab18146889c872d79aff83ec52c0e4818b545f119420ea543', 'context3': '0e66fd67c573bd36c89b6639cdad07a6b6289c62fe377a2d624c0cdf313ed4c0'}, 'batch-crlf': {'context2': 'a5ed6e0d1fa605eab18146889c872d79aff83ec52c0e4818b545f119420ea543', 'context3': 'aa8364f1737b0603d0f1a4cda4d1f4de21d7e86be9b7e8bc6758ca99e2be4e4a'}, 'annotated': {'context2': 'a5ed6e0d1fa605eab18146889c872d79aff83ec52c0e4818b545f119420ea543', 'context3': '75a426eba2827e1949746c619c8b00c14861d580d33ff24ac44a19a755e71d2f'}, 'annotated-crlf': {'context2': 'a5ed6e0d1fa605eab18146889c872d79aff83ec52c0e4818b545f119420ea543', 'context3': 'e8c500932181183ff3754e697f7076c62b851f596896101b01d0c1fea941b610'}}
        cases = [('small','examples/probes/located-function-context/example.bagaev','foo'),('batch','examples/probes/inventory-batch/Batch.bagaev','batch_apply'),('annotated','examples/probes/annotated-change/Batch.annotated.bagaev','batch_apply')]
        for label,path,name in cases:
            raw=(T/path).read_bytes()
            for suffix,source in [('',raw),('-crlf',raw.replace(b'\n',b'\r\n'))]:
                for k,fn in [('context2',edit.context),('context3',edit.located_context)]:
                    data=json.dumps(fn(source,name),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
                    self.assertEqual(hashlib.sha256(data).hexdigest(),expected[label+suffix][k])
    def test_exact_text_and_old_fields(self):
        for path,name in [('examples/probes/located-function-context/example.bagaev','foo'),('examples/probes/annotated-change/Batch.annotated.bagaev','batch_apply')]:
            raw=(T/path).read_bytes()
            for source in (raw,raw.replace(b'\n',b'\r\n')):
                value=edit.source_context(source,name);old=edit.located_context(source,name)
                self.assertEqual(value['schema'],'bagaev-function-context/4')
                for k in old:
                    if k!='schema':self.assertEqual(value[k],old[k])
                b=value['original_body'];loc=b['location'];part=source[loc['start_byte']:loc['end_byte']]
                self.assertEqual(b['text'].encode(),part);self.assertEqual(b['sha256'],hashlib.sha256(part).hexdigest());self.assertEqual(b['source_sha256'],hashlib.sha256(source).hexdigest())
                self.assertEqual(edit.source_context(source.decode(),name),value)
                if name=='batch_apply':
                    self.assertIn('// Original body note;',b['text']);self.assertNotIn('// Only this function',b['text'])
                else:self.assertEqual(b['text'],'text.bytes("ёж")')
                self.assertFalse(value['semantic_check']);self.assertFalse(value['execution_admission'])
    def test_named_spelling(self):
        source=b'bagaev record-form/5; program { entry main; fn diff(a: Int64,b: Int64) -> Int64 = a-b; fn main() -> Int64 = diff(b:2,a:9); }'
        value=edit.source_context(source,'main');self.assertEqual(value['original_body']['text'],'diff(b:2,a:9)');self.assertIn('diff(9, 2)',value['fragment']['source'])
    def test_cli_and_exclusive_output(self):
        source=T/'examples/probes/annotated-change/Batch.annotated.bagaev'
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json';args=['context',str(source),'--form','5','--source-body','--name','batch_apply','--output',str(out)]
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cli.main(args),0)
            raw=out.read_bytes();self.assertEqual(json.loads(raw),edit.source_context(source.read_bytes(),'batch_apply'))
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cli.main(args),2)
            self.assertEqual(out.read_bytes(),raw)
            other=Path(directory)/'other.json'
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(cli.main(args[:-1]+[str(other),'--locations']),0)
            self.assertEqual(other.read_bytes(),raw)
    def test_output_bound_before_write(self):
        source=T/'examples/probes/located-function-context/example.bagaev'
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            with patch.object(cli.transport,'LIMIT',1), contextlib.redirect_stdout(io.StringIO()) as buf:
                # Bypass only the input transport in this isolated output-bound test.
                with patch.object(cli.transport,'read_input',return_value=source.read_bytes()):
                    code=cli.main(['context',str(source),'--form','5','--source-body','--name','foo','--output',str(out)])
            self.assertEqual(code,2);self.assertEqual(json.loads(buf.getvalue())['error']['code'],'RECORD_BOUNDS');self.assertFalse(out.exists())
    def test_invalid_before_input(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            for operation,form in [('extract','5'),('replace','5'),('context','4')]:
                with contextlib.redirect_stdout(io.StringIO()) as buf:
                    code=cli.main([operation,'missing-input','--form',form,'--source-body','--name','foo','--output',str(out)])
                self.assertEqual(code,2);self.assertEqual(json.loads(buf.getvalue())['error']['code'],'TOOL_USAGE');self.assertFalse(out.exists())
        with self.assertRaises(edit.DraftError) as err:edit.source_context(b'bagaev record-form/5; program { entry foo; fn foo() -> Int64 = 1; }','absent')
        self.assertEqual(err.exception.code,'FUNCTION_NAME')
if __name__=='__main__':unittest.main()
