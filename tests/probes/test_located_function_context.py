"""Optional original-layout context data; no programme execution."""
from pathlib import Path
import contextlib,hashlib,io,json,sys,tempfile,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/located-function-context'
sys.path.insert(0,str(T/'src'));sys.path.insert(0,str(T/'tools'))
import bagaev_record_wide_function as edit
import record_function as cli


class LocatedContext(unittest.TestCase):
    def test_default_bytes_and_signatures(self):
        for source,name,pin in [(D/'example.bagaev','foo','c45a81388226ab4044966593f78cf0589dc9c4a9e91eb95b6e43eb4c706bb262'),(T/'examples/probes/inventory-batch/Batch.bagaev','batch_apply','a5ed6e0d1fa605eab18146889c872d79aff83ec52c0e4818b545f119420ea543')]:
            raw=source.read_bytes();old=edit.context(raw,name)
            data=json.dumps(old,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
            self.assertEqual(hashlib.sha256(data).hexdigest(),pin)
            value=edit.located_context(raw,name)
            self.assertEqual(value['schema'],'bagaev-function-context/3')
            for k in ('fragment','callees','callers','scope','semantic_check','execution_admission'):self.assertEqual(value[k],old[k])
            self.assertEqual(value['source_locations']['program_pin'],'sha256:'+old['fragment']['base'])
            self.assertEqual(value['source_locations']['source_sha256'],hashlib.sha256(raw).hexdigest())

    def test_exact_function_and_original_layout(self):
        source=(D/'example.bagaev').read_bytes();value=edit.located_context(source,'foo')
        locations=value['source_locations']['locations'];self.assertEqual(len(locations),2)
        self.assertEqual([x['program_pointer'] for x in locations],['/program/functions/foo/body','/program/functions/foo/body/1'])
        self.assertEqual([source[x['start_byte']:x['end_byte']].decode() for x in locations],['text.bytes("ёж")','"ёж"'])
        self.assertTrue(all(x['start_line']==4 for x in locations))
        self.assertEqual(value['location_source'],'original-full-input; not fragment.source')
        changed=source.replace(b' fn foo()',b'\n fn foo()');other=edit.located_context(changed,'foo')
        self.assertEqual(value['fragment'],other['fragment'])
        self.assertNotEqual(value['source_locations']['source_sha256'],other['source_locations']['source_sha256'])
        self.assertEqual(other['source_locations']['locations'][0]['start_line'],5)

    def test_invalid_combinations_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            for operation,form in [('extract','5'),('replace','5'),('context','4')]:
                with contextlib.redirect_stdout(io.StringIO()) as buffer:
                    code=cli.main([operation,str(D/'example.bagaev'),'--form',form,'--locations','--name','foo','--output',str(out)])
                self.assertEqual(code,2);self.assertEqual(json.loads(buffer.getvalue())['error']['code'],'TOOL_USAGE');self.assertFalse(out.exists())
        with self.assertRaises(edit.DraftError) as error:edit.located_context((D/'example.bagaev').read_bytes(),'absent')
        self.assertEqual(error.exception.code,'FUNCTION_NAME')


if __name__=='__main__':unittest.main()
