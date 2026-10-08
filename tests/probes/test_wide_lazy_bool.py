"""Pure form lowering and source ranges; no source evaluation or native dispatch."""
from pathlib import Path
import json,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as f
import bagaev_record_wide_spans as spans
import bagaev_record_json_form as old
class LazyBooleanForms(unittest.TestCase):
    def test_frozen_graph_and_canonical_form(self):
        for case in json.loads((T/'examples/probes/wide-lazy-bool/cases.json').read_bytes()):
            source='bagaev record-form/5; program { fn main() -> Bool = '+case['expression']+'; entry main; }'
            graph=f.decode(source);self.assertEqual(graph['functions']['main']['body'],case['body'])
            rendered=f.encode(graph);self.assertEqual(f.decode(rendered),graph);self.assertEqual(f.encode(f.decode(rendered)),rendered)
            self.assertNotIn(b'bool.and(',rendered);self.assertNotIn(b'bool.or(',rendered)
    def test_synthetic_literal_range(self):
        for name,index in [('and',3),('or',2)]:
            expr='bool.'+name+'(false, true)';source='bagaev record-form/5; program { fn main() -> Bool = '+expr+'; entry main; }'
            rows=spans.source_map(source)['locations'];row=next(x for x in rows if x['program_pointer']=='/program/functions/main/body/'+str(index))
            self.assertEqual(row['precision'],'enclosing-expression');self.assertEqual(source.encode()[row['start_byte']:row['end_byte']].decode(),expr)
    def test_arity_and_old_profile(self):
        for expr in ['bool.and(true)','bool.or(false)','bool.and(true,false,true)','bool.or(false,true,false)']:
            with self.assertRaises(f.FormError):f.decode('bagaev record-form/5; program { fn main() -> Bool = '+expr+'; entry main; }')
        for name in ['and','or']:
            with self.assertRaises(old.FormError):old.decode('bagaev record-form/4; program { fn main() -> Bool = bool.'+name+'(false,true); entry main; }')
if __name__=='__main__':unittest.main()
