"""Actual pure inspect/diff CLI routes; no evaluator, compiler or Store."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import bagaev_filter_workflow as cli

BASE = ROOT / 'examples/l2-filter/queue.json'
AFTER = ROOT / 'examples/l2-filter/store/queue-refactor.json'
BASE_SHA = 'd08da50bd3d9b80eead8f2b018c7961696c037e1840dfd90701d8588be83d4fa'
AFTER_SHA = 'a1bd8fdf7c23e8cf9d1329a15c5862d82a7db114dd8fe6b9948875189bdb2018'


class InspectionRoute(unittest.TestCase):
    def invoke(self, args):
        output = io.StringIO()
        with mock.patch.object(cli.L2, 'evaluate', side_effect=AssertionError('evaluation forbidden')), \
             mock.patch.object(cli.backend, 'compile_program', side_effect=AssertionError('compile forbidden')), \
             contextlib.redirect_stdout(output):
            code = cli.main([str(arg) for arg in args])
        self.assertNotIn('src.bagaev_filter_store', sys.modules)
        return code, json.loads(output.getvalue())

    def test_inspect_literal_structure(self):
        raw = BASE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), BASE_SHA)
        code, envelope = self.invoke(['inspect', BASE])
        self.assertEqual(code, 0)
        self.assertTrue(envelope['ok'])
        result = envelope['result']
        self.assertEqual(result['source'], 'sha256:' + BASE_SHA)
        self.assertEqual(result['entry'], 'main')
        definitions = result['definitions']
        self.assertEqual([row['id'] for row in definitions], ['identifier', 'job-valid', 'key', 'main', 'valid'])
        self.assertEqual([[d['id'] for d in row['dependencies']] for row in definitions],
                         [[], ['identifier'], [], ['key', 'valid'], ['job-valid']])
        self.assertEqual(definitions[3]['params'], ['q'])
        pins = json.loads(raw)['pins']
        for row in definitions:
            self.assertEqual(row['pin'], pins[row['id']])
            for dependency in row['dependencies']:
                self.assertEqual(dependency['pin'], pins[dependency['id']])
        self.assertEqual(BASE.read_bytes(), raw)

    def test_diff_and_same_source(self):
        before, after = BASE.read_bytes(), AFTER.read_bytes()
        self.assertEqual(hashlib.sha256(after).hexdigest(), AFTER_SHA)
        code, envelope = self.invoke(['diff', BASE, AFTER])
        self.assertEqual(code, 0)
        self.assertEqual(envelope['result'], dict(before='sha256:' + BASE_SHA, after='sha256:' + AFTER_SHA,
            entry_changed=False, added=[], removed=[], changed=['main'], pins_changed=['main']))
        code, envelope = self.invoke(['diff', BASE, BASE])
        self.assertEqual(code, 0)
        self.assertEqual(envelope['result'], dict(before='sha256:' + BASE_SHA, after='sha256:' + BASE_SHA,
            entry_changed=False, added=[], removed=[], changed=[], pins_changed=[]))
        self.assertEqual((BASE.read_bytes(), AFTER.read_bytes()), (before, after))

    def test_foreign_and_malformed_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            foreign = root / 'foreign.json'
            value = json.loads(BASE.read_bytes())
            value['schema'] = 'bagaev-l2/1'
            foreign.write_text(json.dumps(value), encoding='utf8')
            broken = root / 'broken.json'
            broken.write_bytes(b'{')
            for source, expected in ((foreign, 'L2_PROGRAM'), (broken, 'L2_JSON')):
                original = source.read_bytes()
                code, envelope = self.invoke(['inspect', source])
                self.assertEqual(code, 2)
                self.assertFalse(envelope['ok'])
                self.assertEqual(envelope['error']['code'], expected)
                self.assertEqual(source.read_bytes(), original)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['broken.json', 'foreign.json'])


if __name__ == '__main__':
    unittest.main()
