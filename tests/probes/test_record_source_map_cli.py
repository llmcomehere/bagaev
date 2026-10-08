"""Data-only file interface checks; no interpreter/kernel launch."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
T = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(T / 'tools'))
import record_source_map as cli


class MapCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.bagaev'
        self.raw = b'bagaev record-form/5; program { entry main; fn main() -> Int64 = 7 + 7; }'
        self.source.write_bytes(self.raw)
        self.map = cli.spans.source_map(self.raw)

    def invoke(self, name, extra=(), *, pin=None, form='5', source=None, error=None):
        out = self.root / (name + '.json')
        args = [str(source or self.source), '--program-pin', pin or self.map['program_pin'], '--output', str(out)]
        if form is not None:args += ['--form', form]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):code = cli.main(args + list(extra))
        receipt = json.loads(buffer.getvalue())
        if error:
            self.assertEqual(code, 2)
            self.assertEqual(receipt['error']['code'], error)
            self.assertFalse(out.exists())
            return
        self.assertEqual(code, 0)
        data = out.read_bytes()
        self.assertEqual(cli.hashlib.sha256(data).hexdigest(), receipt['output_sha256'])
        return json.loads(data)

    def test_complete_selected_and_layout(self):
        self.assertEqual(self.invoke('complete'), self.map)
        selected = self.invoke('selected', ['--pointer', '/program/functions/main/body/2'])
        self.assertEqual(selected['locations'], [self.map['locations'][2]])
        self.assertEqual(self.invoke('layout', ['--source-sha256', self.map['source_sha256']]), self.map)
        self.source.write_bytes(self.raw.replace(b'7 + 7', b'7\n+ 7'))
        changed = self.invoke('changed')
        self.assertEqual(changed['program_pin'], self.map['program_pin'])
        self.assertNotEqual(changed['source_sha256'], self.map['source_sha256'])
        self.invoke('stale-layout', ['--source-sha256', self.map['source_sha256']], error='SOURCE_MAP_LAYOUT')

    def test_pins_usage_and_pointer_refusals(self):
        self.invoke('bad-pin', pin='abc', error='SOURCE_MAP_PIN')
        self.invoke('old-pin', pin='sha256:' + '0' * 64, error='SOURCE_MAP_PIN')
        self.invoke('bad-layout', ['--source-sha256', 'abc'], error='SOURCE_MAP_LAYOUT')
        self.invoke('pointer', ['--pointer', '/missing'], error='SOURCE_MAP_POINTER')
        self.invoke('no-form', form=None, error='TOOL_USAGE')
        self.invoke('wrong-form', form='4', error='TOOL_USAGE')

    def test_transport_and_no_overwrite(self):
        link = self.root / 'link'
        link.symlink_to(self.source)
        self.invoke('link-out', source=link, error='RECORD_PATH')
        bad = self.root / 'bad'
        bad.write_bytes(b'\xff')
        self.invoke('bad-out', source=bad, error='FORM_SYNTAX')
        bad.write_bytes(b' ' * 1048577)
        self.invoke('big-out', source=bad, error='RECORD_BOUNDS')
        out = self.root / 'keep'
        out.write_bytes(b'keep')
        with self.assertRaises(cli.transport.Refusal) as error:
            cli.create([str(self.source), '--form', '5', '--program-pin', self.map['program_pin'], '--output', str(out)])
        self.assertEqual(error.exception.code, 'RECORD_PATH')
        self.assertEqual(out.read_bytes(), b'keep')
        self.assertEqual(self.source.read_bytes(), self.raw)


if __name__ == '__main__':unittest.main()
