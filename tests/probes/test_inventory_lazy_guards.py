"""Equivalent readable view only, no fresh runtime or native observations."""
from pathlib import Path
import json,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as form
import bagaev_record_wide_spans as spans
from bagaev_record_draft import digest
D=T/'examples/probes/inventory-batch'
class InventoryLazyGuards(unittest.TestCase):
    def test_full_graph_pin_and_canonical_bytes(self):
        original=form.decode((D/'Batch.bagaev').read_bytes());alternate=form.decode((D/'Batch.lazy.bagaev').read_bytes());frozen=json.loads((D/'program.json').read_bytes())
        self.assertEqual(original,alternate);self.assertEqual(alternate,frozen)
        self.assertEqual(digest(alternate),'d6b56f365d222f52d015ac336cd2f85bf2626c0148ce7f3fadf2bd243a2f4f66')
        self.assertEqual(form.encode(original),form.encode(alternate))
    def test_generated_literal_ranges(self):
        raw=(D/'Batch.lazy.bagaev').read_bytes();mapping=spans.source_map(raw);self.assertEqual(mapping['program_pin'],'sha256:d6b56f365d222f52d015ac336cd2f85bf2626c0148ce7f3fadf2bd243a2f4f66')
        for pointer in ['/program/functions/sku_ok/body/3','/program/functions/item_shape/body/3','/program/functions/item_shape/body/2/3','/program/functions/item_shape/body/2/2/3']:
            row=next(x for x in mapping['locations'] if x['program_pointer']==pointer)
            self.assertEqual(row['precision'],'enclosing-expression');self.assertTrue(raw[row['start_byte']:row['end_byte']].startswith(b'bool.and('))
if __name__=='__main__':unittest.main()
