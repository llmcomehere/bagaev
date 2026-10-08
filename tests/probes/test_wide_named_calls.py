"""Data-only named-call ordering, scope, bounds and source range checks."""
from pathlib import Path
import json,sys,unittest
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as f
import bagaev_record_wide_spans as spans
import bagaev_record_json_form as old
FUNCTION='fn diff(a: Int64,b: Int64) -> Int64 = a - b;'
def source(expr,forward=False):
    main='fn main() -> Int64 = '+expr+';'
    return 'bagaev record-form/5; program { '+(main+FUNCTION if forward else FUNCTION+main)+' entry main; }'
class NamedCalls(unittest.TestCase):
    def test_frozen_graphs_and_forward_declarations(self):
        for case in json.loads((T/'examples/probes/wide-named-calls/cases.json').read_bytes()):
            for forward in [False,True]:
                p=f.decode(source(case['expression'],forward));self.assertEqual(p['functions']['main']['body'],case['body'])
                canonical=f.encode(p);self.assertEqual(f.decode(canonical),p);self.assertEqual(f.encode(f.decode(canonical)),canonical)
    def test_argument_ranges_follow_values(self):
        raw=source('diff(b: 2, a: 9)');rows=spans.source_map(raw)['locations']
        for path,text in [('/program/functions/main/body/2','9'),('/program/functions/main/body/3','2')]:
            row=next(x for x in rows if x['program_pointer']==path);self.assertEqual(row['precision'],'exact-expression');self.assertEqual(raw.encode()[row['start_byte']:row['end_byte']].decode(),text)
    def test_refusals(self):
        for expr in ['diff(a:1)','diff(a:1,a:2)','diff(a:1,c:2)','missing(a:1,b:2)','diff(a:1,2)','diff(1,b:2)','bool.and(left:true,right:false)']:
            with self.assertRaises(f.FormError):f.decode(source(expr))
        with self.assertRaises(f.FormError):f.decode('bagaev record-form/5; program { fn f(a:Int64,a:Int64)->Int64=a; fn main()->Int64=f(a:1); entry main; }')
        with self.assertRaises(old.FormError):old.decode(source('diff(b:2,a:9)').replace('record-form/5','record-form/4'))
    def test_eight_arguments_and_ninth_refusal(self):
        for n in [8,9]:
            names=[chr(97+i) for i in range(n)];params=', '.join(k+': Int64' for k in names);args=', '.join(k+': '+str(i+1) for i,k in reversed(list(enumerate(names))))
            raw='bagaev record-form/5; program { fn f('+params+')->Int64=a; fn main()->Int64=f('+args+'); entry main; }'
            if n==9:
                with self.assertRaises(f.FormError):f.decode(raw)
            else:self.assertEqual(f.decode(raw)['functions']['main']['body'],['call','f']+[['int',i+1] for i in range(n)])
if __name__=='__main__':unittest.main()
