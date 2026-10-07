"""Detached match-bearing source changes with the reviewed actual checker."""
from pathlib import Path
import json,sys,hashlib,subprocess,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-match/edit'
from outcome_host import configure
args=configure(reference=True);R=args.output;reader=args.reader;ref=args.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_match_edit as edit
import bagaev_component_arithmetic_edit as prior
suite=json.loads((D/'cases.json').read_bytes());rows=[];calls=[];drafts={}
def invoke(binary,args,inputs):
 paths=[]
 for suffix,raw in inputs:
  f=R/f'{len(calls):02d}.{suffix}';f.write_bytes(raw);paths.append(f)
 q=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20);(R/f'{len(calls):02d}.stdout').write_bytes(q.stdout);(R/f'{len(calls):02d}.stderr').write_bytes(q.stderr)
 assert q.returncode==0 and not q.stderr and all(f.read_bytes()==b for f,(_,b) in zip(paths,inputs));v=json.loads(q.stdout);calls.append(v);return v
def checker(a,b):return invoke(reader,['policy'],[('source.json',a),('policy.json',b)])
def substitute(a,b):
 v=checker(a,b);v['source_sha256']='0'*64;return v
for c in suite['cases']:
 before=edit.canonical(c)
 try:v=edit.draft(suite['original'],edit.canonical(c['frame']),edit.canonical(suite['policy']),{'actual':checker,'missing':None,'substitute':substitute}[c['checker']])
 except edit.EditError as e:v={'error':e.code}
 except edit.CheckerUnavailable:v={'error':'CheckerUnavailable'}
 except edit.ComponentRefused as e:v={'error':'ComponentRefused','stage':e.stage,'reason':e.reason}
 assert v==c['expected'],(c['id'],v,c['expected']);assert edit.canonical(c)==before;rows.append(c['id'])
 if v.get('status')=='draft':drafts[c['id']]=v
try:prior.frame(edit.canonical(suite['cases'][0]['frame']))
except prior.EditError as e:assert e.code=='EDIT_VERSION'
else:raise AssertionError('prior accepted')
for name in ['helper','business-wrong']:
 program=copy.deepcopy(drafts[name]['component']['program']);program['entry']='quantity'
 v=invoke(ref,['run','--input'],[('invocation.json',edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':[suite['argument']]}))]);assert v['status']=='success' and v['value_type']=='Int64' and type(v['value'])is int;assert (v['value']==suite['expected_quantity']) is (name=='helper'),v
result={'status':'PASSED','cases':len(rows),'native_calls':len(calls),'pure_reference_invocations':2,'prior_edit3_refuses':True,'scope':'Detached source2/draft2 only, zero external effects; structural compatibility is not business refinement.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
