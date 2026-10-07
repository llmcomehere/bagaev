"""Actual checker harness. Refuses absent or different binary; never uses cached passes."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-outcomes/context'
sha=lambda b:hashlib.sha256(b).hexdigest()
sys.path.insert(0,str(P/'src'))
import bagaev_component_outcome_context as context
import bagaev_probe_context as legacy
import bagaev_component_outcome_edit as edit
from outcome_host import configure
args=configure();reader=args.reader;R=args.output
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
suite=json.loads((D/'cases.json').read_bytes());policy=edit.canonical(suite['policy'])
R.mkdir(exist_ok=False);calls=[];rows=[]
def wire_checker(source,policy_bytes):
 n=len(calls)+1;f=R/f'{n:03d}.source.json';p=R/f'{n:03d}.policy.json'
 f.write_bytes(source);p.write_bytes(policy_bytes)
 q=subprocess.run([str(reader),'policy',str(f),str(p)],capture_output=True,timeout=10)
 (R/f'{n:03d}.stdout').write_bytes(q.stdout);(R/f'{n:03d}.stderr').write_bytes(q.stderr)
 assert q.returncode==0 and not q.stderr and f.read_bytes()==source and p.read_bytes()==policy_bytes
 calls.append({'source_sha256':sha(source),'output_sha256':sha(q.stdout)})
 return json.loads(q.stdout)
def checker(programme):
 try:edit.checked(programme,policy,wire_checker,'context')
 except edit.ComponentRefused as e:raise context.ComponentRefusal(e.reason,'') from None
 except edit.CheckerUnavailable as e:raise context.ContextUnavailable(str(e)) from None
 return edit.canonical(programme)
def substitute(programme):
 checker(programme)
 return b'{}'
for c in suite['cases']:
 selected={'actual':checker,'missing':None,'substitute':substitute}[c['checker']];before=len(calls)
 try:
  if c['legacy']:actual=legacy.inspect(edit.canonical(c['context']),edit.canonical(c['expectation']),kernel_checker=selected)
  else:actual=context.inspect(edit.canonical(c['context']),edit.canonical(c['expectation']),component_checker=selected)
 except context.ContextError as e:actual={'error':e.code,'location':e.location}
 except context.ContextUnavailable:actual={'error':'ContextUnavailable'}
 except context.ComponentRefusal as e:actual={'error':'ComponentRefusal','code':e.code,'location':e.location}
 except edit.form.FormError as e:actual={'error':e.code}
 rows.append({'id':c['id'],'actual':actual,'expected':c['expected'],'matched':actual==c['expected'],'checker_calls':len(calls)-before})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':rows,'calls':calls,'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','scope':'Actual source/policy checker. No application execution, rights restoration, durable recovery or live admission.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'cases':len(rows),'calls':len(calls)}))
assert result['status']=='PASSED'
