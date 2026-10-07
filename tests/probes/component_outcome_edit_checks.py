"""Qualify reconstructed adapter with real /2 source checker and zero counterexample."""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-outcomes/edit'
sys.path.insert(0,str(P/'src'))
import bagaev_component_outcome_edit as edit2
enc=edit2.canonical;sha=lambda b:hashlib.sha256(b).hexdigest()
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
s=json.loads((D/'cases.json').read_bytes())
from outcome_host import configure
args=configure(reference=True);R=args.output;reader=args.reader;ref=args.reference
R.mkdir(exist_ok=False);calls=[];rows=[];drafts={}
def invoke(binary,args,inputs):
 n=len(calls)+1;paths=[]
 for suffix,data in inputs:
  p=R/f'{n:03d}.{suffix}';p.write_bytes(data);paths.append(p)
 q=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20)
 (R/f'{n:03d}.stdout').write_bytes(q.stdout);(R/f'{n:03d}.stderr').write_bytes(q.stderr)
 assert q.returncode==0 and not q.stderr and all(p.read_bytes()==d for p,(_,d) in zip(paths,inputs))
 calls.append({'binary':binary.name,'inputs':[sha(d) for _,d in inputs],'output':sha(q.stdout)})
 return json.loads(q.stdout)
def checker(a,b):return invoke(reader,['policy'],[('source.json',a),('policy.json',b)])
def substitute(a,b):
 wire=checker(a,b);wire['source_sha256']='0'*64;return wire
def profile(a,b):
 wire=checker(a,b);wire['schema']='bagaev-component-check/1';return wire
def fails(a,b):raise RuntimeError('controlled host failure')
for c in s['cases']:
 before=len(calls)
 try:
  actual=edit2.draft(s['original'],enc(c['frame']),enc(s['policy']),{'actual':checker,'missing':None,'substitute':substitute,'fails':fails,'profile':profile}[c['checker']],candidate_map=c['map'])
  drafts[c['id']]=actual
 except edit2.EditError as e:actual={'error':e.code}
 except edit2.CheckerUnavailable:actual={'error':'CheckerUnavailable'}
 except edit2.ComponentRefused as e:actual={'error':'ComponentRefused','stage':e.stage,'reason':e.reason}
 rows.append({'id':c['id'],'matched':actual==c['expected'],'actual':actual,'expected':c['expected'],'calls':len(calls)-before})
pure=P/'examples/probes/component-outcomes/pure'
for n,h in json.loads((pure/'inputs.json').read_bytes())['sha256'].items():assert sha((pure/n).read_bytes())==h
zero=next(c for c in json.loads((pure/'corrected-cases.json').read_bytes())['cases'] if c['id']=='ZERO')
counter=[]
for name in ['EXTRACT-HELPER','BUSINESS-CHANGE-ONLY-DRAFT']:
 program=drafts[name]['component']['program'];wire=invoke(ref,['run','--input'],[('invocation.json',enc({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':zero['arguments']}))])
 assert wire['status']==zero['expected']['status']=='success'
 equivalent=wire['value']==zero['expected']['value']
 assert equivalent==(name=='EXTRACT-HELPER')
 counter.append({'draft':name,'matches_independent_zero_value':equivalent,'actual':wire,'expected_value':zero['expected']['value']})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'zero_counterexample':counter,'calls':calls,'scope':'Finite source-edit qualification; compatibility does not prove business refinement. No live admission.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'matched':sum(r['matched'] for r in rows),'cases':len(rows),'calls':len(calls),'failures':[r for r in rows if not r['matched']]}))
assert result['status']=='PASSED'
