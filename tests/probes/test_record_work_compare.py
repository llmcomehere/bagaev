"""Pinned comparison checks, without executing source programs."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from bagaev_record_work_compare import compare,form
from bagaev_record_draft import digest,DraftError

OLD='bagaev record-form/5; program { entry main; fn main(x: Int64) -> Int64 = x + 1; }'
NEW='bagaev record-form/5; program { entry main; fn one() -> Int64 = 1; fn main(x: Int64) -> Int64 = x + one(); }'
B={'x':{'type':'Int64'}}

def pair(old=OLD,new=NEW,bounds=None):
    return compare(old,new,B if bounds is None else bounds,
                   base_sha256=digest(form.decode(old)),target_sha256=digest(form.decode(new)))

class Compare(unittest.TestCase):
    def test_charge_delta_and_no_equivalence(self):
        r=pair()
        self.assertEqual((r['before']['upper_work'],r['after']['upper_work'],r['upper_work_delta']),(3,4,1))
        self.assertEqual(r['delta'],{'add':['one'],'replace':['main']})
        for k in ('semantic_check','execution_admission','equivalence_check'):self.assertFalse(r[k])
        r=pair(new=OLD.replace('x + 1','x - 1'))
        self.assertEqual(r['upper_work_delta'],0);self.assertFalse(r['equivalence_check'])

    def test_pins_and_immutability(self):
        old=OLD.replace('entry main;','// Пример\nentry main;').encode()
        b=copy.deepcopy(B);r=pair(old,NEW.encode(),b)
        self.assertEqual(r['original_source_sha256'],hashlib.sha256(old).hexdigest())
        self.assertEqual(r['candidate_source_sha256'],hashlib.sha256(NEW.encode()).hexdigest())
        raw=json.dumps(b,sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(r['argument_bounds_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(b,B)
        r['delta']['add'].append('other');self.assertEqual(pair()['delta']['add'],['one'])

    def test_unknown_omits_numeric_delta(self):
        new=OLD.replace('x + 1','text.bytes("x")')
        r=pair(new=new)
        self.assertEqual(r['after']['status'],'UNKNOWN')
        self.assertNotIn('upper_work_delta',r)
        self.assertEqual(r['after']['location'],{'function':'main','pointer':''})

    def test_wrong_contracts_refuse(self):
        for b in ({},{'x':{'type':'Bool'}},{'x':None},{'x':{'type':'Int64'},'y':{'type':'Int64'}}):
            with self.assertRaises(DraftError):pair(bounds=b)
        for base,target in [('0'*64,digest(form.decode(NEW))),(digest(form.decode(OLD)),'0'*64)]:
            with self.assertRaises(DraftError):compare(OLD,NEW,B,base_sha256=base,target_sha256=target)
        with self.assertRaises(DraftError):pair(new=OLD)
        with self.assertRaises(DraftError):pair(new=NEW.replace('x: Int64','x: Bool'))

    def test_existing_paired_examples(self):
        d=ROOT/'examples/probes/record-work-edit'
        r=pair((d/'Repeated.bagaev').read_bytes(),(d/'Reuse.bagaev').read_bytes(),{'xs':{'type':'TextList','items':64,'bytes':256}})
        self.assertEqual((r['before']['upper_work'],r['after']['upper_work'],r['upper_work_delta']),(73739,36874,-36865))
        d=ROOT/'examples/probes/record-work-helper-edit'
        r=pair((d/'Direct.bagaev').read_bytes(),(d/'Extracted.bagaev').read_bytes(),{'items':{'type':'Items','items':16}})
        self.assertEqual((r['before']['upper_work'],r['after']['upper_work'],r['upper_work_delta']),(178,210,32))

    def test_bound_shape_unknown_and_order(self):
        d=ROOT/'examples/probes/record-work-edit'
        old=(d/'Repeated.bagaev').read_bytes();new=(d/'Reuse.bagaev').read_bytes()
        a={'xs':{'type':'TextList','items':64,'bytes':256}}
        b={'xs':{'bytes':256,'items':64,'type':'TextList'}}
        self.assertEqual(pair(old,new,a)['argument_bounds_sha256'],pair(old,new,b)['argument_bounds_sha256'])
        a['xs']['items']=True
        r=pair(old,new,a)
        self.assertEqual(r['before']['status'],'UNKNOWN');self.assertEqual(r['after']['status'],'UNKNOWN')
        self.assertNotIn('upper_work_delta',r)
        a['xs']['items']=float('nan')
        with self.assertRaises(DraftError):pair(old,new,a)

    def test_missing_entry(self):
        old=OLD.replace('entry main;','entry missing;')
        new=NEW.replace('entry main;','entry missing;')
        with self.assertRaises(DraftError) as caught:pair(old,new)
        self.assertEqual(caught.exception.code,'WORK_ARGUMENTS')

if __name__=='__main__':unittest.main()
