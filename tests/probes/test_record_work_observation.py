"""Source-pinned independent facts; no source-program execution."""
from pathlib import Path
import copy,hashlib,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work_observation import observe_source,form
from bagaev_record_draft import digest,DraftError
S='bagaev record-form/5; program { entry main; fn main(x: Text, y: Text) -> Bool = text.eq(x,y); }'

def run(source=S,bounds=None,args=None):
    return observe_source(source,{'x':{'type':'Text','bytes':2},'y':{'type':'Text','bytes':2}} if bounds is None else bounds,
                          ['é','é'] if args is None else args,program_sha256=digest(form.decode(source)))

class Observation(unittest.TestCase):
    def test_applicable_and_violated(self):
        for maximum,upper,status in [(0,3,'EXCEEDS'),(2,7,'WITHIN')]:
            r=run(bounds={n:{'type':'Text','bytes':maximum} for n in ('x','y')})
            self.assertEqual(r['work_bound']['upper_work'],upper)
            self.assertEqual(r['argument_dimensions']['status'],status)
            self.assertFalse(r['semantic_check']);self.assertFalse(r['execution_admission']);self.assertTrue(r['requires_checked_program'])
    def test_parameter_order(self):
        s=S.replace('x: Text, y: Text','y: Text, x: Text')
        r=run(s,args=['abc','é'],bounds={'x':{'type':'Text','bytes':2},'y':{'type':'Text','bytes':3}})
        self.assertEqual(r['argument_dimensions']['status'],'WITHIN')
        self.assertEqual([(v['name'],v['bytes']) for v in r['argument_dimensions']['dimensions']],[('x',2),('y',3)])
    def test_invalid_or_unknown_does_not_disappear(self):
        self.assertEqual(run(args=[False,'é'])['argument_dimensions']['status'],'INVALID_ARGUMENT')
        s=S.replace('text.eq(x,y)','int.eq(text.bytes(x), text.bytes(y))')
        r=run(s);self.assertEqual(r['work_bound']['status'],'UNKNOWN');self.assertEqual(r['argument_dimensions']['status'],'WITHIN')
        self.assertEqual(r['work_bound']['location']['function'],'main')
    def test_wrong_binding_and_pin(self):
        for bounds,args in [({},['é','é']),({'x':{'type':'Bool'},'y':{'type':'Text','bytes':2}},['é','é']),({'x':{'type':'Text','bytes':2},'y':{'type':'Text','bytes':2}},['é'])]:
            with self.assertRaises(DraftError):run(bounds=bounds,args=args)
        for pin in ['bad','0'*64]:
            with self.assertRaises(DraftError):observe_source(S,{},[],program_sha256=pin)
    def test_identity_and_immutability(self):
        b={'x':{'type':'Text','bytes':2},'y':{'type':'Text','bytes':2}};a=['é','é'];old=copy.deepcopy((b,a))
        r=run(bounds=b,args=a);s=S.replace('entry main;','// note\nentry main;');q=run(s)
        self.assertEqual(r['program_sha256'],q['program_sha256']);self.assertNotEqual(r['source_sha256'],q['source_sha256'])
        self.assertEqual(q['source_sha256'],hashlib.sha256(s.encode()).hexdigest());self.assertEqual((b,a),old)

    def test_nominal_dimensions_are_unknown(self):
        d=ROOT/'examples/probes/record-work-helper-edit/Direct.bagaev'
        r=run(d.read_bytes(),{'items':{'type':'Items','items':16}},[[]])
        self.assertEqual(r['work_bound']['status'],'SUPPORTED')
        self.assertEqual(r['argument_dimensions']['status'],'UNKNOWN')
        self.assertFalse(r['execution_admission'])
    def test_missing_entry(self):
        s=S.replace('entry main;','entry missing;')
        with self.assertRaises(DraftError) as caught:run(s)
        self.assertEqual(caught.exception.code,'WORK_ARGUMENTS')

if __name__=='__main__':unittest.main()
