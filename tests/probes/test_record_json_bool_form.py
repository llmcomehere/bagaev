"""Explicit form6 data checks. Frozen runtime cases here are NOT_RUN."""
from pathlib import Path
import copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
import bagaev_record_json_bool_form as new
import bagaev_record_wide_form as old
RAW=(ROOT/'examples/probes/record-json-bool/cases.json').read_bytes();CASES=json.loads(RAW)
class JsonBoolForm(unittest.TestCase):
    def test_frozen_identity_and_roundtrips(self):
        self.assertEqual(hashlib.sha256(RAW).hexdigest(),'fb21fc6ce6286e144c1eba6d98069f0bc78d8115bbd0549630283d0bf5754bf6')
        self.assertEqual(len(CASES),20)
        for c in CASES:
            if c['profile']!=12:continue
            p=c['invocation']['program'];before=copy.deepcopy(p)
            for encoder in (new.encode,new.encode_named):self.assertEqual(new.decode(encoder(p)),p)
            self.assertEqual(p,before)
    def test_versions_do_not_fall_back(self):
        p=CASES[0]['invocation']['program'];s=new.encode(p)
        with self.assertRaises(old.FormError):old.decode(s)
        with self.assertRaises(new.FormError):new.decode(s.replace(b'record-form/6',b'record-form/5'))
        with self.assertRaises(old.FormError):old.decode(s.replace(b'record-form/6',b'record-form/5'))
        with self.assertRaises(old.FormError):old.encode(p)
        p=copy.deepcopy(p);p['schema']='bagaev-typed-record/11'
        with self.assertRaises(new.FormError):new.encode(p)
    def test_arity_and_preserved_literals(self):
        p=CASES[0]['invocation']['program'];s=new.encode(p)
        self.assertIn(b'json.bool_or(x, false)',s)
        for replacement in (b'json.bool_or(x)',b'json.bool_or(x, false, true)',b'json.unknown(x, false)'):
            with self.assertRaises(new.FormError):new.decode(s.replace(b'json.bool_or(x, false)',replacement))
        p=copy.deepcopy(p);p['functions']['main']['body']=['json.bool_or',['arg','x'],['text','json.bool_or(x, false)']]
        self.assertEqual(new.decode(new.encode(p)),p) # Syntax conversion does not type-check.
    def test_old_graphs_stay_in_old_form(self):
        path=ROOT/'examples/probes/record-active-total/cases.json'
        for c in json.loads(path.read_bytes()):
            self.assertEqual(old.decode(old.encode(c['program'])),c['program'])
            with self.assertRaises(new.FormError):new.decode(c['source'])
if __name__=='__main__':unittest.main()
