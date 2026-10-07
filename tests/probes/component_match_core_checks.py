"""Actual reviewed reference for frozen match values and refusal reasons."""
from pathlib import Path
import json,hashlib,subprocess,sys,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-match'
from outcome_host import configure
args=configure(reference=True);R=args.output;ref=args.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_match_form as form

s=json.loads((D/'cases.json').read_bytes());rows=[]
propose={'case':'Propose','value':{'key':{'code':'sku1'},'note':'kept','quantity':7}};decline={'case':'Decline','value':{'reason':'negative'}}
def run(source,arg,name,expected):
 program=copy.deepcopy(form.decode(source)['program']);program['entry']='quantity';raw=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':[arg]},sort_keys=True,separators=(',',':')).encode();f=R/(name+'.json');f.write_bytes(raw)
 q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);(R/(name+'.stdout')).write_bytes(q.stdout);(R/(name+'.stderr')).write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw
 v=json.loads(q.stdout)
 if type(expected)is int:assert v['status']=='success' and type(v['value'])is int and v['value']==expected,(name,v)
 else:assert v['reason']==expected,(name,v)
 rows.append({'id':name,'matched':True,'observation':v})
for c in s['positive']:
 run(c['source'],propose,c['id']+'-propose',9 if c['id']=='local' else 7)
 run(c['source'],decline,c['id']+'-decline','RR_OVERFLOW' if c['id']=='lazy' else -1)
base=s['positive'][0]['source']
for name,a,b,reason in [('missing','Decline(error): -1;','', 'RR_SHAPE'),('unknown','Decline(error)','Unknown(error)','RR_REFERENCE'),('type','Decline(error): -1','Decline(error): true','RR_TYPE'),('scope','Decline(error): -1','Decline(error): stock.quantity','RR_REFERENCE')]:run(base.replace(a,b),propose,name,reason)
source=R/'checked-source.json';raw=json.dumps(form.decode(s['positive'][0]['source']),sort_keys=True,separators=(',',':')).encode();source.write_bytes(raw)
policy=T/'examples/probes/component-arithmetic/policy.json';pb=policy.read_bytes()
q=subprocess.run([str(args.reader),'policy',str(source),str(policy)],capture_output=True,timeout=20);(R/'source-policy.stdout').write_bytes(q.stdout)
assert q.returncode==0 and not q.stderr and source.read_bytes()==raw and policy.read_bytes()==pb
check=json.loads(q.stdout);assert check['status']=='checked' and check['policy_compatible'] is True and check['execution_admission'] is False
result={'status':'PASSED','source_policy_checks':1,'reference_invocations':len(rows),'rows':rows,'scope':'Frozen values/reasons only; work/location retained as observations; unchanged typed-record/10.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
