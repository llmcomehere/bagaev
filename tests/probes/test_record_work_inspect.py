"""Data-only inspect integration; no evaluator dispatch."""
from pathlib import Path
import hashlib,json,sys,tempfile,unittest
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
import record_text
SOURCE='bagaev record-form/5; program { record Report { values: TextList, had_duplicates: Bool }; entry summarize; fn marker() -> Int64 = 42; fn summarize(xs: TextList) -> Report = let ys = list.unique(xs) in Report { values: ys, had_duplicates: list.len(ys) < list.len(xs) }; }'

class Inspect(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.d=Path(self.temp.name);self.source=self.d/'source';self.source.write_text(SOURCE)
        self.bounds=self.d/'bounds';self.out=self.d/'out'
        self.bounds.write_text('{"xs":{"type":"TextList","items":64,"bytes":479}}')

    def command(self):
        return ['inspect',str(self.source),'--form','5','--output',str(self.out)]

    def test_default_bytes_unchanged(self):
        record_text.convert(self.command())
        self.assertEqual(hashlib.sha256(self.out.read_bytes()).hexdigest(),'b5aaf10520ee07d5c39d1b3201ee0c6f21ca07254efd7984443d7a2f4e66586c')
        self.assertNotIn('work_bound',json.loads(self.out.read_bytes()))

    def test_bound_and_identity(self):
        record_text.convert(self.command()+['--bounds',str(self.bounds)])
        r=json.loads(self.out.read_bytes());self.assertEqual(r['work_bound']['upper_work'],65418)
        self.assertTrue(r['work_bound']['fits_work_budget']);self.assertFalse(r['execution_admission'])
        self.assertEqual(r['argument_bounds_sha256'],hashlib.sha256(self.bounds.read_bytes()).hexdigest())
        self.assertEqual(r['source_sha256'],hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.out.unlink();self.bounds.write_text('{"xs":{"type":"TextList","items":64,"bytes":480}}')
        record_text.convert(self.command()+['--bounds',str(self.bounds)])
        self.assertEqual(json.loads(self.out.read_bytes())['work_bound']['upper_work'],65546)

    def test_refused_shapes_usage_and_no_overwrite(self):
        for data in ('{}','{"xs":{"type":"Bool"}}','{"xs":{},"extra":{}}','{"xs":{},"xs":{}}'):
            self.bounds.write_text(data)
            with self.assertRaises(record_text.Refusal):record_text.convert(self.command()+['--bounds',str(self.bounds)])
            self.assertFalse(self.out.exists())
        with self.assertRaises(record_text.Refusal):
            record_text.convert(['inspect',str(self.source),'--output',str(self.out),'--bounds',str(self.bounds)])
        self.bounds.write_text('{"xs":{"type":"TextList","items":64,"bytes":479}}')
        self.out.write_bytes(b'keep')
        with self.assertRaises(record_text.Refusal):record_text.convert(self.command()+['--bounds',str(self.bounds)])
        self.assertEqual(self.out.read_bytes(),b'keep')

    def test_unknown_is_data_not_numeric_success(self):
        self.bounds.write_text('{"xs":{"type":"TextList","items":true,"bytes":0}}')
        record_text.convert(self.command()+['--bounds',str(self.bounds)])
        r=json.loads(self.out.read_bytes())['work_bound']
        self.assertEqual(r['status'],'UNKNOWN');self.assertNotIn('upper_work',r)

    def test_missing_entry_refuses_without_output(self):
        self.source.write_text(SOURCE.replace('entry summarize;', 'entry missing;'))
        with self.assertRaises(record_text.Refusal) as caught:
            record_text.convert(self.command()+['--bounds',str(self.bounds)])
        self.assertEqual(caught.exception.code,'RECORD_ARGUMENTS')
        self.assertFalse(self.out.exists())

    def test_helper_definitions_are_used(self):
        source='bagaev record-form/5; program { entry main; fn helper(x: TextList) -> TextList = list.unique(x); fn main(xs: TextList) -> TextList = helper(xs); }'
        self.source.write_text(source)
        self.bounds.write_text('{"xs":{"type":"TextList","items":3,"bytes":5}}')
        record_text.convert(self.command()+['--bounds',str(self.bounds)])
        r=json.loads(self.out.read_bytes())['work_bound']
        self.assertEqual(r['upper_work'],43);self.assertFalse(r['execution_admission'])

if __name__=='__main__':unittest.main()
