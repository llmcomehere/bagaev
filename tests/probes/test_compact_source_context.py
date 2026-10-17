"""Opt-in original-body projection; data only, no application execution."""
from pathlib import Path
import contextlib, hashlib, io, json, sys, tempfile, unittest
from unittest.mock import patch
T = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(T/'src')); sys.path.insert(0, str(T/'tools'))
import bagaev_record_wide_function as edit
import record_function as cli

def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()

class CompactSourceContext(unittest.TestCase):
    def test_projection_and_original_bytes(self):
        for path, name in [('located-function-context/example.bagaev','foo'),
                           ('annotated-change/Batch.annotated.bagaev','batch_apply'),
                           ('inventory-batch-change/BatchLimited.bagaev','batch_apply')]:
            raw = (T/'examples/probes'/path).read_bytes()
            for source in (raw, raw.replace(b'\n', b'\r\n')):
                full = edit.source_context(source, name)
                compact = edit.compact_source_context(source, name)
                expected = {k:v for k,v in full.items() if k not in ('schema','source_locations')}
                expected.update(schema='bagaev-function-context/5',
                                location_scope='original-body-root-only; descendant locations omitted')
                self.assertEqual(compact, expected)
                self.assertNotIn('source_locations', compact)
                body = compact['original_body']; root = body['location']
                self.assertEqual(root['program_pointer'], '/program/functions/'+name+'/body')
                self.assertEqual(root['precision'], 'exact-expression')
                selected = source[root['start_byte']:root['end_byte']]
                self.assertEqual(body['text'].encode(), selected)
                self.assertEqual(body['sha256'], hashlib.sha256(selected).hexdigest())
                self.assertEqual(body['source_sha256'], hashlib.sha256(source).hexdigest())
                self.assertFalse(compact['semantic_check']); self.assertFalse(compact['execution_admission'])
                if name=='foo': self.assertEqual(body['text'], 'text.bytes("ёж")')
                if 'annotated' in path: self.assertIn('// Original body note;', body['text'])
                self.assertEqual(edit.compact_source_context(source.decode(), name), compact)

    def test_frozen_journey_context_and_detachment(self):
        source = (T/'examples/probes/inventory-batch-change/BatchLimited.bagaev').read_bytes()
        full = edit.source_context(source, 'batch_apply')
        self.assertEqual(hashlib.sha256(wire(full)).hexdigest(),
                         '7f2999c0c3a201f5b7664e58b3d436844490545f9c49304c4fa55be6babeea7c')
        compact = edit.compact_source_context(source, 'batch_apply')
        self.assertLess(len(wire(compact)), len(wire(full)))
        compact['original_body']['text']='changed'
        compact['callees'][0]['params'].append(['extra','Int64'])
        fresh = edit.compact_source_context(source, 'batch_apply')
        self.assertEqual(fresh['original_body'], full['original_body'])
        self.assertEqual(fresh['callees'], full['callees'])

    def test_cli_and_exclusive_output(self):
        source = T/'examples/probes/located-function-context/example.bagaev'
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            args=['context',str(source),'--form','5','--name','foo','--source-body','--compact','--output',str(out)]
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(cli.main(args),0)
            raw=out.read_bytes(); self.assertEqual(raw,wire(edit.compact_source_context(source.read_bytes(),'foo')))
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(cli.main(args),2)
            self.assertEqual(out.read_bytes(),raw)

    def test_invalid_flags_before_input(self):
        variants=[['extract','--form','5','--source-body'],['replace','--form','5','--source-body'],
                  ['context','--form','4','--source-body'],['context','--form','6','--source-body'],
                  ['context','--source-body'],['context','--form','5'],
                  ['context','--form','5','--source-body','--locations'],
                  ['context','--form','5','--source-body','--callee-context']]
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            for args in variants:
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    code=cli.main([args[0],'missing-input',*args[1:],'--name','foo','--compact','--output',str(out)])
                self.assertEqual(code,2); self.assertEqual(json.loads(stream.getvalue())['error']['code'],'TOOL_USAGE')
                self.assertFalse(out.exists())

    def test_unknown_function(self):
        source=(T/'examples/probes/located-function-context/example.bagaev').read_bytes()
        with self.assertRaises(edit.DraftError) as error: edit.compact_source_context(source,'absent')
        self.assertEqual(error.exception.code,'FUNCTION_NAME')

    def test_output_limit_seam(self):
        source=T/'examples/probes/located-function-context/example.bagaev'
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.json'
            with patch.object(cli.transport,'LIMIT',1), patch.object(cli.transport,'read_input',return_value=source.read_bytes()):
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    code=cli.main(['context',str(source),'--form','5','--source-body','--compact','--name','foo','--output',str(out)])
            self.assertEqual(code,2); self.assertEqual(json.loads(stream.getvalue())['error']['code'],'RECORD_BOUNDS')
            self.assertFalse(out.exists())

if __name__=='__main__': unittest.main()
