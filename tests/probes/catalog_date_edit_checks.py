"""Frozen full-output comparison through a separately admitted profile11 reference."""
from pathlib import Path
import argparse,copy,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--reference',type=Path,required=True)
parser.add_argument('--reference-sha256',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
reference=args.reference.resolve();out=args.output.resolve()
assert reference.is_file() and reference.stat().st_size<=33554432
assert re.fullmatch('[0-9a-f]{64}',args.reference_sha256) and sha(reference.read_bytes())==args.reference_sha256
out.mkdir(exist_ok=False)
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bagaev_record_wide_form as form
from catalog_date_edit_reference import evaluate
from test_catalog_date_edit_reference import exact,containers
data=ROOT/'examples/probes/catalog-date-edit'
oracle_raw=(data/'cases.json').read_bytes()
assert sha(oracle_raw)=='1b5f3b4cf3e1499cbf2d60c4e30a454086db27d2463dec9cf8968e2231ac13b6'
oracle=json.loads(oracle_raw);source=(data/'Catalog.bagaev').read_bytes();program=form.decode(source)
with (out/'program.json').open('x') as stream:json.dump(program,stream,sort_keys=True,separators=(',',':'))
rows=[]
for case in oracle['cases']:
    request=copy.deepcopy(case['request'] if 'request' in case else {
        'interface':'catalog-date-edit/1','state':oracle['states'][case['state']],
        'entry_id':case['target'],'action':case['action']})
    before=copy.deepcopy(request)
    expected=({'kind':'refusal','reason':case['reason']} if 'reason' in case else
              {'kind':'success','state':oracle['states'][case['output_state']],'entry_ids':case['view']})
    ordinary=evaluate(request)
    assert exact(ordinary,expected) and exact(request,before) and not(containers(request)&containers(ordinary))
    raw=json.dumps({'schema':'bagaev-typed-record-invocation/11','program':program,'arguments':[request]},
                   sort_keys=True,separators=(',',':')).encode()
    path=out/(case['id']+'.json')
    with path.open('xb') as stream:stream.write(raw)
    result=subprocess.run([str(reference),'run','--input',str(path)],capture_output=True,timeout=20)
    for suffix,value in [('stdout',result.stdout),('stderr',result.stderr)]:
        with (out/(case['id']+'.'+suffix)).open('xb') as stream:stream.write(value)
    assert result.returncode==0 and not result.stderr,(case['id'],result.stderr)
    actual=json.loads(result.stdout)
    assert actual['schema']=='bagaev-typed-record-result/11' and actual['status']=='success',(case['id'],actual)
    assert actual['reason'] is None and actual['location'] is None
    assert exact(actual['value'],{'case':'Ok' if expected['kind']=='success' else 'Error','value':expected}),(case['id'],actual,expected)
    assert path.read_bytes()==raw and sha(reference.read_bytes())==args.reference_sha256
    rows.append({'id':case['id'],'status':'PASS','work':actual['work']})
assert (data/'Catalog.bagaev').read_bytes()==source and (data/'cases.json').read_bytes()==oracle_raw
result={'status':'PASS','cases':rows,'ordinary_comparisons':len(rows),'reference_calls':len(rows),
        'source_sha256':sha(source),'oracle_sha256':sha(oracle_raw),'reference_sha256':args.reference_sha256,
        'scope':'pure date edit, no external state change or cost claim'}
with (out/'evidence.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
