"""Reviewed serial old-decline/new-source trace with actual checker and evaluator."""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-outcomes/context'
sys.path.insert(0,str(P/'src'))
import bagaev_component_outcome_context as context2
import bagaev_component_outcome_edit as edit2
import component_change as changes
import bagaev_component_owner as base
from bagaev_component_outcome_programmes import ProgrammeManager,RunError,restore_pending
from outcome_qualification import load
from bagaev_component_outcome_owner import OutcomeOwner
from outcome_host import configure
enc=edit2.canonical;sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
s=json.loads((D/'connected.json').read_bytes())
args=configure(reference=True,matcher=True,qualification=True);R=args.output;reader=args.reader;ref=args.reference
qualified,graph,binding,observations,prior=load(args.qualification_directory,{'producer-before.json':args.producer_sha256,'good-qualification.json':args.good_sha256,'bad-qualification.json':args.bad_sha256},[reader,ref,args.matcher])
assert qualified['source1']==s['source1'] and qualified['good']==s['source2'] and qualified['policy']==s['policy']
R.mkdir(exist_ok=False);calls=[];apps=0;changes.R=R
matcher=changes.Matcher(args.matcher,args.matcher_sha256)
def invoke(binary,args,inputs):
 n=len(calls)+1;paths=[]
 for suffix,data in inputs:
  p=R/f'{n:03d}.{suffix}';p.write_bytes(data);paths.append(p)
 q=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20)
 (R/f'{n:03d}.stdout').write_bytes(q.stdout);(R/f'{n:03d}.stderr').write_bytes(q.stderr)
 assert q.returncode==0 and not q.stderr and all(p.read_bytes()==data for p,(_,data) in zip(paths,inputs))
 calls.append({'binary':binary.name,'inputs':[sha(d) for _,d in inputs],'output':sha(q.stdout)})
 return json.loads(q.stdout)
def checker(source,policy):return invoke(reader,['policy'],[('source.json',source),('policy.json',policy)])
def evaluator(program,args):
 global apps
 result=invoke(ref,['run','--input'],[('input.json',enc({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':args}))])
 if program['functions'][program['entry']]['body'][0]!='arg':apps+=1
 return result
conditions=clone(s['conditions']);owner=OutcomeOwner(policy=s['policy'],sources=[s['source1']],state=s['initial'],revision=7,resource='stock/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions))
manager=ProgrammeManager(owner,initial=sha(enc(s['source1'])),policy=s['policy'],checker=checker,graph=graph,binding=binding,matcher=matcher,authority=lambda:True)
manager.start('original')
a,b,_=s['case']['actions'];outputs=[]
try:owner.submit(enc(b['packet']));raise AssertionError('source available before admission')
except base.OwnerInputError as e:assert e.code=='OWNER_SOURCE'
conditions['observe']=False;outputs.append(manager.submit('original',enc(a['packet'])))
assert owner.snapshot()['revision']==7 and owner.snapshot()['mutations']==0
admitted=manager.admit(s['source2'],expected_base=sha(enc(s['source1'])),observations=observations)
assert admitted=={'decision':'accepted','reason':'all-obligations'}
assert manager.start('new')==sha(enc(s['source2'])) and manager.runs['original']==sha(enc(s['source1']))
try:manager.start('original');raise AssertionError('run repinned')
except RunError as e:assert e.code=='RUN_DUPLICATE'
try:manager.submit('original',enc(b['packet']));raise AssertionError('old run accepted new source')
except RunError as e:assert e.code=='RUN_SOURCE'
conditions['observe']=True;outputs.append(manager.submit('new',enc(b['packet'])))
conditions['observe']=False;before=owner.snapshot();before_apps=apps
def context_checker(program):
 try:edit2.checked(program,enc(s['policy']),checker,'context')
 except edit2.ComponentRefused as e:raise context2.ComponentRefusal(e.reason,'') from None
 except edit2.CheckerUnavailable as e:raise context2.ContextUnavailable(str(e)) from None
 return enc(program)
restored=restore_pending(manager,enc(s['context']),enc(s['expectation']),pending_sha256=sha(enc(s['pending'])),component_checker=context_checker)
inspection=restored['inspection']
assert inspection==s['inspection'] and owner.snapshot()==before and apps==before_apps
raw=next(row['text'] for row in s['context']['sources'] if row['id']=='pending-operation')
pending=json.loads(raw)
# Independent caller/run expectations, never rights or owner-ledger deserialization.
assert enc(pending)==enc(s['pending']) and pending['schema']=='owned-outcome-pending/2'
assert pending['run_id']=='original' and pending['programme_source']=='old-programme'
assert pending['programme_pin']=='sha256:'+sha(enc(s['source1']))
assert pending['packet']==a['packet']
assert restored['run_id']=='original' and restored['packet']==pending['packet']
outputs.append(manager.observe(restored['run_id'],enc(restored['packet'])))
assert owner.snapshot()==before and apps==before_apps
conditions['observe']=True;outputs.append(manager.observe(restored['run_id'],enc(restored['packet'])))
actual={'outputs':outputs,**owner.snapshot(),'application_evaluations':apps}
assert actual==s['case']['expected'],actual
assert apps==before_apps==2
guards=[]
for fault,wanted in [('pin','CONTINUATION_PIN'),('head','CONTINUATION_HEAD'),('run','CONTINUATION_SOURCE')]:
 old_head=manager.head;old_run=manager.runs['original'];pending_pin=sha(enc(s['pending']))
 if fault=='pin':pending_pin='0'*64
 elif fault=='head':manager.head='0'*64
 else:manager.runs['original']=manager.head
 try:restore_pending(manager,enc(s['context']),enc(s['expectation']),pending_sha256=pending_pin,component_checker=context_checker);raise AssertionError('bad restore accepted')
 except RunError as e:assert e.code==wanted;guards.append(e.code)
 finally:manager.head=old_head;manager.runs['original']=old_run
 assert owner.snapshot()==before and apps==2
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED','actual':actual,'inspection':inspection,'calls':calls,'qualification':prior,'admission':admitted,'matcher_calls':matcher.calls,'restore_guards':guards,'scope':'S1-only live serial simulation consumes exact prior fresh qualification. No production authority, durable recovery, authentication or concurrency proof.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'PASSED','calls':len(calls),'application_evaluations':apps,'old_decline_revision':outputs[-1]['revision'],'current_revision':actual['revision']}))
