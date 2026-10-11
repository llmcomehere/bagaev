"""Explicit data-only form6 authoring; legacy preparation remains unchanged."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import record_text as tool

SOURCE = ('bagaev record-form/6; program { entry main; '
          'fn project(value: Json, fallback: Bool) -> Bool = json.bool_or(value, fallback); '
          'fn main(x: Json) -> Bool = project(x, false); }')

class Form6Authoring(unittest.TestCase):
    def test_roundtrip_named_inspection_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as folder:
            d = Path(folder); source = d/'source'; source.write_text(SOURCE)
            graph = d/'graph'
            report = tool.convert(['decode', str(source), '--form', '6', '--output', str(graph)])
            self.assertEqual(report['source_schema'], 'bagaev-typed-record/12')
            self.assertEqual(report['output_sha256'], hashlib.sha256(graph.read_bytes()).hexdigest())
            self.assertFalse(report['execution_admission']); self.assertFalse(report['semantic_check'])
            expected = json.loads(graph.read_bytes())
            self.assertEqual(expected['schema'], 'bagaev-typed-record/12')
            for named in (False, True):
                encoded = d/('encoded'+str(named)); decoded = d/('decoded'+str(named))
                tool.convert(['encode', str(graph), '--form', '6', '--output', str(encoded)] + (['--named-calls'] if named else []))
                tool.convert(['decode', str(encoded), '--form', '6', '--output', str(decoded)])
                self.assertEqual(json.loads(decoded.read_bytes()), expected)
                if named: self.assertIn('value:', encoded.read_text())
            info = d/'info'
            tool.convert(['inspect', str(source), '--form', '6', '--output', str(info)])
            inspection = json.loads(info.read_bytes())
            self.assertEqual(inspection['program_sha256'], report['output_sha256'])
            self.assertEqual(inspection['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertFalse(inspection['semantic_check']); self.assertFalse(inspection['execution_admission'])
            self.assertNotIn('work_bound', inspection)
            before = graph.read_bytes()
            with self.assertRaises(tool.Refusal) as caught:
                tool.convert(['decode', str(source), '--form', '6', '--output', str(graph)])
            self.assertEqual(caught.exception.code, 'RECORD_PATH'); self.assertEqual(graph.read_bytes(), before)

    def test_unsupported_operations_refuse_before_io(self):
        with tempfile.TemporaryDirectory() as folder:
            d = Path(folder); out = d/'out'; missing = str(d/'missing')
            for argv in ([ 'prepare', missing, '--arguments', missing],
                         [ 'inspect', missing, '--bounds', missing],
                         [ 'decode', missing, '--named-calls']):
                with self.assertRaises(tool.Refusal) as caught:
                    tool.convert(argv + ['--form', '6', '--output', str(out)])
                self.assertEqual(caught.exception.code, 'TOOL_USAGE'); self.assertFalse(out.exists())

    def test_explicit_version_and_legacy_prepare(self):
        with tempfile.TemporaryDirectory() as folder:
            d = Path(folder); src = d/'source'; out = d/'out'; args = d/'args'; args.write_text('[true]')
            for declared, selected in [('6', '5'), ('5', '6')]:
                src.write_text('bagaev record-form/'+declared+'; program { entry main; fn main(x: Bool) -> Bool = x; }')
                with self.assertRaises(tool.form.FormError) as caught:
                    tool.convert(['decode', str(src), '--form', selected, '--output', str(out)])
                self.assertEqual(caught.exception.code, 'FORM_VERSION'); self.assertFalse(out.exists())
            report = tool.convert(['prepare', str(src), '--form', '5', '--arguments', str(args), '--output', str(out)])
            self.assertEqual(report['source_schema'], 'bagaev-typed-record/11')
            self.assertEqual(json.loads(out.read_bytes())['schema'], 'bagaev-typed-record-invocation/11')
            self.assertEqual(json.loads(out.read_bytes())['arguments'], [True])

if __name__ == '__main__':
    unittest.main()
