"""Pure opt-in source view, graph identity and unchanged default encoding."""
from pathlib import Path
import json,sys,unittest,hashlib,copy
T=Path(__file__).resolve().parents[2];sys.path.insert(0,str(T/'src'))
import bagaev_record_wide_form as f
from bagaev_record_draft import digest

def program(body):
    return dict(schema='bagaev-typed-record/11',records={},lists={},variants={},entry='main',functions={'diff':{'params':[['a','Int64'],['b','Int64']],'result':'Int64','body':['sub',['arg','a'],['arg','b']]},'main':{'params':[],'result':'Int64','body':body}})
class NamedEncoding(unittest.TestCase):
    def test_exact_default_and_named_views(self):
        observations=json.loads((T/'examples/probes/wide-named-encode/observations.json').read_bytes())['observations'];rows={x['id']:x for x in observations}
        graphs={name:json.loads((T/'examples/probes'/name/'program.json').read_bytes()) for name in ['inventory-batch','inventory-batch-change']}
        graphs.update({x['id']:program(x['body']) for x in json.loads((T/'examples/probes/wide-named-calls/cases.json').read_bytes())})
        for name,p in graphs.items():
            raw=f.encode_named(p);self.assertEqual(f.decode(raw),p);self.assertEqual(f.encode_named(f.decode(raw)),raw)
            self.assertEqual(hashlib.sha256(f.encode(p)).hexdigest(),rows[name]['default_sha256']);self.assertEqual(hashlib.sha256(raw).hexdigest(),rows[name]['named_sha256']);self.assertEqual('sha256:'+digest(p),rows[name]['program_pin'])
    def test_unsupported_callee_contracts(self):
        base=program(['call','diff',['int',9],['int',2]])
        for kind in ['unknown','arity','duplicate']:
            p=copy.deepcopy(base)
            if kind=='unknown':p['functions']['main']['body'][1]='missing'
            elif kind=='arity':p['functions']['main']['body'].pop()
            else:p['functions']['diff']['params'][1][0]='a'
            with self.assertRaises(f.FormError):f.encode_named(p)
    def test_zero_argument_call(self):
        p=program(['call','diff']);p['functions']['diff']={'params':[],'result':'Int64','body':['int',1]}
        self.assertEqual(f.encode_named(p),f.encode(p));self.assertEqual(f.decode(f.encode_named(p)),p)
if __name__=='__main__':unittest.main()
