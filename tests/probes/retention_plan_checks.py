"""Finite same-inventory functional controls; explicit separately reviewed reference."""
from pathlib import Path
import argparse,copy,hashlib,json,re,subprocess
from retention_plan_baseline import decide
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/retention-plan'
sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
p=argparse.ArgumentParser();p.add_argument('--reference',required=True,type=Path);p.add_argument('--reference-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
assert a.reference.is_absolute() and a.reference.is_file() and not a.reference.is_symlink() and re.fullmatch('[0-9a-f]{64}',a.reference_sha256) and sha(a.reference.read_bytes())==a.reference_sha256
R=a.output;assert R.is_absolute() and R.parent.is_dir() and not R.exists()
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
program=json.loads((D/'program.json').read_bytes());cases=json.loads((D/'cases.json').read_bytes())['cases'];R.mkdir();calls=[];rows=[]
def invoke(source,argument,label):
 raw=enc({'schema':'bagaev-typed-record-invocation/10','program':source,'arguments':[argument]});path=R/(label+'.input.json');path.write_bytes(raw)
 q=subprocess.run([str(a.reference),'run','--input',str(path)],capture_output=True,timeout=20);(R/(label+'.stdout')).write_bytes(q.stdout);(R/(label+'.stderr')).write_bytes(q.stderr)
 assert q.returncode==0 and not q.stderr and path.read_bytes()==raw
 wire=json.loads(q.stdout);assert wire['status']=='success' and wire['value_type']=='Record:Decision',wire
 calls.append({'label':label,'input_sha256':sha(raw),'output_sha256':sha(q.stdout),'logical_work':wire['work']});return wire['value']
for case in cases:
 before=copy.deepcopy(case['input']);ordinary=decide(case['input']);typed=invoke(program,case['input'],case['id']);assert case['input']==before and typed==ordinary==case['expected']
 rows.append({'id':case['id'],'value':typed})
by_id={c['id']:c for c in cases};controls=[]
for item in json.loads((D/'controls.json').read_bytes())['controls']:
 case=by_id[item['case']];baseline=invoke(program,case['input'],item['id']+'-baseline');assert baseline==case['expected']
 mutant=copy.deepcopy(program);mutant['functions'][item['function']]['body']=['bool',item['replacement']];wrong=invoke(mutant,case['input'],item['id']+'-mutant')
 assert wrong=={'decision':item['wrong_decision'],'reason':item['wrong_reason'],'execution_admission':False} and wrong!=case['expected']
 controls.append({'id':item['id'],'case':case['id'],'normal_wrong_value':wrong})
result={'status':'PASSED','literal_cases':rows,'controls':controls,'calls':calls,'scope':'Same finite inventory and independent literal expectations. No deletion, execution grant, new interpreter primitive, general graph completeness or comparative timing/cost claim.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASSED','literal_cases':len(rows),'controls':len(controls),'calls':len(calls)}))
