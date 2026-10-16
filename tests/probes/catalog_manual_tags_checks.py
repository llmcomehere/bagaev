"""Frozen manual-tag application comparison with a separately admitted reference."""
import argparse,copy,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True)
p.add_argument('--reference-sha256',required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();reference=a.reference.resolve();out=a.output.resolve()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert reference.is_file() and reference.stat().st_size<=33554432
assert re.fullmatch('[0-9a-f]{64}',a.reference_sha256) and sha(reference.read_bytes())==a.reference_sha256
out.mkdir(exist_ok=False)
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import bagaev_record_wide_form as form
from catalog_manual_tags_reference import evaluate
from test_catalog_manual_tags_reference import exact,containers
data=ROOT/'examples/probes/catalog-manual-tags';oracle_raw=(data/'cases.json').read_bytes()
assert sha(oracle_raw)=='3d56bf381cacfba3f6a672aee6db7a598d16f30489c26dc500d10d831b7e82e2'
oracle=json.loads(oracle_raw);source=(data/'Catalog.bagaev').read_bytes();program=form.decode(source)
with (out/'program.json').open('x') as f:json.dump(program,f,sort_keys=True,separators=(',',':'))
rows=[];outputs={}
def run(name,request,expected):
    before=copy.deepcopy(request);ordinary=evaluate(request)
    assert exact(ordinary,expected) and exact(request,before) and not(containers(request)&containers(ordinary))
    raw=json.dumps({'schema':'bagaev-typed-record-invocation/11','program':program,'arguments':[request]},sort_keys=True,separators=(',',':')).encode()
    path=out/(name+'.json')
    with path.open('xb') as f:f.write(raw)
    result=subprocess.run([str(reference),'run','--input',str(path)],capture_output=True,timeout=20)
    for suffix,value in [('stdout',result.stdout),('stderr',result.stderr)]:
        with (out/(name+'.'+suffix)).open('xb') as f:f.write(value)
    assert result.returncode==0 and not result.stderr,(name,result.returncode,result.stderr)
    actual=json.loads(result.stdout)
    assert actual['schema']=='bagaev-typed-record-result/11' and actual['status']=='success',(name,actual)
    assert actual['reason'] is None and actual['location'] is None
    assert exact(actual['value'],{'case':'Ok' if expected['kind']=='success' else 'Error','value':expected}),(name,actual,expected)
    assert path.read_bytes()==raw and sha(reference.read_bytes())==a.reference_sha256
    rows.append({'case':name,'status':'PASS'});return actual['value']['value']
cases={c['name']:c for c in oracle['cases']}
assert len(cases)==37
for case in oracle['cases']:outputs[case['name']]=run(case['name'],copy.deepcopy(case['request']),case['expected'])
for i,chain in enumerate(oracle['chains']):
    first=outputs[chain['first']];second=cases[chain['next']]
    assert exact(first['state'],second['request']['state'])
    request=copy.deepcopy(second['request']);request['state']=first['state']
    run('chain-'+str(i),request,second['expected'])
assert (data/'Catalog.bagaev').read_bytes()==source and (data/'cases.json').read_bytes()==oracle_raw
evidence={'status':'PASS','frozen_cases':37,'actual_predecessor_chain_calls':2,'reference_calls':len(rows),
    'ordinary_comparisons':len(rows),'source_sha256':sha(source),'oracle_sha256':sha(oracle_raw),
    'reference_sha256':a.reference_sha256,'observations':rows,
    'scope':'pure manual-tag replacement, no external state or performance claim'}
with (out/'evidence.json').open('x') as f:json.dump(evidence,f,indent=2)
print(json.dumps(evidence))
