"""Exact pre-frozen control-operand graphs; no programme execution."""
from pathlib import Path
import hashlib,json,sys,unittest
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/wide-control-operands'
sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as form
import bagaev_record_wide_function as edit
import bagaev_record_wide_format as formatting


class ControlOperands(unittest.TestCase):
    def test_frozen_graph_roundtrips(self):
        rows=json.loads((D/'cases.json').read_bytes());self.assertEqual(len(rows),6)
        for row in rows:
            with self.subTest(case=row['id']):
                self.assertIn(row['before_fix'],['FORM_PROFILE','FORM_SYNTAX'])
                raw=form.encode(row['program'])
                self.assertEqual(form.decode(raw),row['program'])
                self.assertEqual(form.encode(form.decode(raw)),raw)
                pretty=formatting.format_source(raw)
                self.assertEqual(form.decode(pretty),row['program'])
                self.assertEqual(formatting.format_source(pretty),pretty)

    def test_existing_context_bytes(self):
        example='bagaev record-form/5;\nprogram {\n entry main;\n fn foo() -> Int64 = text.bytes("ёж");\n fn foo_more() -> Int64 = 1;\n fn main() -> Int64 = foo() + foo_more();\n}\n'
        batch=(T/'examples/probes/inventory-batch/Batch.bagaev').read_bytes()
        for source,name,pin in [(example,'foo','c45a81388226ab4044966593f78cf0589dc9c4a9e91eb95b6e43eb4c706bb262'),(batch,'batch_apply','a5ed6e0d1fa605eab18146889c872d79aff83ec52c0e4818b545f119420ea543')]:
            raw=json.dumps(edit.context(source,name),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),pin)


if __name__=='__main__':unittest.main()
