"""Frozen independent cases, actual predecessor chains and detached outputs."""
import copy,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from catalog_manual_tags_reference import evaluate
def exact(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b
def containers(x):
    if type(x) is dict:return {id(x)}.union(*(containers(v) for v in x.values()))
    if type(x) is list:return {id(x)}.union(*(containers(v) for v in x))
    return set()
def oracle():
    raw=(ROOT/'examples/probes/catalog-manual-tags/cases.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='3d56bf381cacfba3f6a672aee6db7a598d16f30489c26dc500d10d831b7e82e2'
    return json.loads(raw)
class ManualTags(unittest.TestCase):
    def check_case(self,request,expected):
        before=copy.deepcopy(request);result=evaluate(request)
        self.assertTrue(exact(result,expected),(result,expected));self.assertTrue(exact(request,before))
        self.assertFalse(containers(request)&containers(result));return result
    def test_cases(self):
        cases=oracle()['cases'];self.assertEqual(len(cases),37)
        for c in cases:
            with self.subTest(case=c['name']):self.check_case(copy.deepcopy(c['request']),c['expected'])
    def test_actual_predecessor_chains(self):
        data=oracle();cases={c['name']:c for c in data['cases']}
        for chain in data['chains']:
            first=cases[chain['first']];second=cases[chain['next']]
            actual=self.check_case(copy.deepcopy(first['request']),first['expected'])
            self.assertTrue(exact(actual['state'],second['request']['state']))
            request=copy.deepcopy(second['request']);request['state']=actual['state']
            self.check_case(request,second['expected'])
if __name__=='__main__':unittest.main()
