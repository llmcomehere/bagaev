from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys
P=Path(__file__).resolve().parents[2];O=Path(__file__).parent;D=P/'examples/probes/outcome-persistence'
sys.path.insert(0,str(P/'src'))
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_durable_programmes import DurableProgrammes
from persistence_host import Native,select
from outcome_host import configure
import component_change as changes
from outcome_qualification import load
from bagaev_outcome_durable_context import inspect_pending
import bagaev_component_outcome_edit as edit2
import bagaev_component_outcome_context as context2
args=configure(reference=True,matcher=True,qualification=True);R=args.output;select(args)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy;enc=envelope.encode
s=json.loads((D/'bridge.json').read_bytes());ctx=json.loads((P/'examples/probes/component-outcomes/context/connected.json').read_bytes());cfg=s['config'];S1=s['packets']['A']['source'];S2=s['packets']['B']['source'];inputs,graph,binding,obs,prior=load(args.qualification_directory,{n+'-qualification.json':getattr(args,n+'_sha256') for n in ('good','bad')}|{'producer-before.json':args.producer_sha256},[args.reader,args.reference,args.matcher]);assert inputs['source1']==cfg['sources'][0] and inputs['good']==cfg['sources'][1]
p={'expected':{'generation':0,'source':S1},'target':S2,'policy':binding['policy'],'assertions':binding['assertions'],'producer':binding['producer'],'qualification':binding['qualification']};R.mkdir(exist_ok=False);rows=[]
for name,wanted in json.loads((D/'continuation.json').read_bytes())['cases']:
 folder=R/name;folder.mkdir();db=folder/'owner.sqlite';n=Native(folder/'native');conditions=clone(s['conditions']);changes.R=folder;matcher=changes.Matcher(args.matcher,args.matcher_sha256)
 def qualifier(proposal,source):
  assert proposal==p and image_codec.pin(source)==S2
  assert changes.decide(graph,graph,binding,obs,matcher,S1,True)=={'decision':'accepted','reason':'all-obligations'}
  return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
 def fresh(checker):return DurableProgrammes(cfg,bootstrap=S1,checker=checker,evaluator=n.evaluator,conditions=lambda:clone(conditions),authority=lambda:True,qualifier=qualifier)
 m=fresh(n.checker);m.create(db);m.start(db,'original');conditions['observe']=False;assert m.call(db,'original','submit',enc(s['packets']['A']))=={'status':'OutcomeUnknown'};m.admit(db,'M1',p);m.start(db,'new');conditions.update(observe=True,tick=2);assert m.call(db,'new','submit',enc(s['packets']['B']))['kind']=='Applied';assert storage.read(db)['generation']==5
 # A fresh dispatcher has no copied Python owner or ledger from the first one.
 m=fresh(n.checker);context=clone(ctx['context']);expectation=clone(ctx['expectation']);pending=clone(ctx['pending']);pending_pin=sha(enc(pending));expected_head={'generation':1,'source':S2}
 if name=='current-observe-denied':conditions['observe']=False
 elif name=='wrong-pending-pin':pending_pin='0'*64
 elif name=='wrong-head-generation':expected_head['generation']=3
 elif name=='wrong-head-source':expected_head['source']=S1
 elif name in ('unknown-run','rebound-run'):
  before=storage.read(db);v=json.loads(before['image'])
  original=next(r for r in v['runs'] if r['id']=='original')
  if name=='unknown-run':original['id']='other'
  else:original['head']={'generation':1,'source':S2};v['runs'].append({'id':'retained-old','head':{'generation':0,'source':S1}})
  v['runs'].sort(key=lambda r:r['id']);storage.compare_and_swap(db,before['generation'],before['digest'],enc(v))
 elif name=='caller-owner-state':
  pending['receiver']=s['images']['initial'];text=enc(pending).decode();pin='sha256:'+sha(text.encode());pending_pin=sha(enc(pending))
  for row in context['sources']:
   if row['id']=='pending-operation':row.update(text=text,pin=pin)
  for row in expectation['sources']:
   if row['id']=='pending-operation':row['pin']=pin
  for group in ('obligations','unknowns','open_effects'):
   for row in context[group]:
    changed=False
    for ref in row['refs']:
     if ref['source']=='pending-operation':ref.update(pin=pin,end=len(text.encode()));changed=True
    if changed:
     if group=='obligations':row['pin']='sha256:'+sha(enc({k:v for k,v in row.items() if k!='pin'}))
     for expected in expectation[group]:
      if expected['id']==row['id']:expected['pin']=row['pin'] if group=='obligations' else 'sha256:'+sha(enc(row))
 elif name=='callback-store-change':
  trigger=[True]
  def checker(source,policy):
   result=n.checker(source,policy)
   if trigger[0]:trigger[0]=False;m.start(db,'nested')
   return result
  m=fresh(checker)
 def component_checker(source):
  try:edit2.checked(source,enc(cfg['policy']),n.checker,'context')
  except edit2.ComponentRefused as e:raise context2.ComponentRefusal(e.reason,'') from None
  except edit2.CheckerUnavailable as e:raise context2.ContextUnavailable(str(e)) from None
  return enc(source)
 (folder/'context.json').write_bytes(enc(context));(folder/'expectation.json').write_bytes(enc(expectation));before=storage.read(db);apps=n.apps
 try:
  result=inspect_pending(m,db,enc(context),enc(expectation),pending_sha256=pending_pin,expected_head=expected_head,component_checker=component_checker)
  assert result['run_id']=='original' and result['packet']==ctx['pending']['packet'] and result['inspection']==ctx['inspection']
  received=m.call(db,result['run_id'],'observe',enc(result['packet']))
  if name=='current-observe-denied':actual=received['status']
  else:assert received['kind']=='Declined' and received['revision']==7;actual='PASS'
 except envelope.ProgrammeError as e:actual=e.code
 after=storage.read(db);assert n.apps==apps==2
 if name=='callback-store-change':assert after['generation']==before['generation']+1 and len(json.loads(after['image'])['runs'])==3
 else:assert after==before
 rows.append({'id':name,'expected':wanted,'actual':actual,'matched':actual==wanted,'native_calls':len(n.calls),'new_application_evaluations_after_reopen':n.apps-apps,'setup_application_evaluations':apps,'matcher_calls':matcher.calls})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'qualification':prior,'scope':'Fresh durable dispatcher per case. Actual owned typed reconstruction and existing caller context checker; no new execution on continuation. Prior42 qualification calls verified, not reexecuted. Store mutation only setup or explicit nested test operation.'};(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'cases':len(rows),'native_calls':sum(r['native_calls'] for r in rows),'matcher_calls':sum(len(r['matcher_calls']) for r in rows),'failures':[r for r in rows if not r['matched']]}));assert out['status']=='PASSED'
