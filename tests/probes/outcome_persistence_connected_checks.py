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
args=configure(reference=True,matcher=True,qualification=True);R=args.output;select(args)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
inputs,graph,binding,observations,prior=load(args.qualification_directory,{n+'-qualification.json':getattr(args,n+'_sha256') for n in ('good','bad')}|{'producer-before.json':args.producer_sha256},[args.reader,args.reference,args.matcher]);s=json.loads((D/'bridge.json').read_bytes());cfg=s['config'];S1=s['packets']['A']['source'];S2=s['packets']['B']['source']
assert inputs['source1']==cfg['sources'][0] and inputs['good']==cfg['sources'][1] and inputs['policy']==cfg['policy']
R.mkdir(exist_ok=False);changes.R=R;matcher=changes.Matcher(args.matcher,args.matcher_sha256)
n=Native(R/'native');conditions=clone(s['conditions']);authority=True;calls=[]
p={'expected':{'generation':0,'source':S1},'target':S2,'policy':binding['policy'],'assertions':binding['assertions'],'producer':binding['producer'],'qualification':binding['qualification']}
def qualifier(proposal,source):
 # Proposal comparison includes H, while the existing qualification graph binds
 # immutable source bytes and its five independently fixed obligations.
 if proposal!=p or image_codec.pin(source)!=binding['component']:return {'decision':'invalid'}
 result=changes.decide(graph,graph,binding,observations,matcher,proposal['expected']['source'],authority);calls.append(result)
 if result!={'decision':'accepted','reason':'all-obligations'}:return {'decision':'invalid'}
 return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
m=DurableProgrammes(cfg,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(conditions),authority=lambda:authority,qualifier=qualifier);db=R/'owner.sqlite';m.create(db);m.start(db,'old')
before=storage.read(db)
try:m.call(db,'old','submit',envelope.encode(s['packets']['B']));raise AssertionError('inventory bypassed managed run')
except envelope.ProgrammeError as e:assert e.code=='PROGRAMME_RUN_SOURCE'
assert storage.read(db)==before
conditions['observe']=False;assert m.call(db,'old','submit',envelope.encode(s['packets']['A']))=={'status':'OutcomeUnknown'}
admitted=m.admit(db,'M1',p);assert admitted=={'kind':'Admitted','head':{'generation':1,'source':S2}};m.start(db,'new')
conditions.update(observe=True,tick=2);b=m.call(db,'new','submit',envelope.encode(s['packets']['B']));assert b['kind']=='Applied' and b['revision']==8
before=storage.read(db);apps=n.apps;conditions.update(observe=False,tick=3);assert m.call(db,'old','observe',envelope.encode(s['packets']['A']))=={'status':'AccessDenied'}
conditions['observe']=True;a=m.call(db,'old','observe',envelope.encode(s['packets']['A']));assert a['kind']=='Declined' and a['revision']==7 and storage.read(db)==before and n.apps==apps==2
authority=False;assert m.admit(db,'M1',p)==admitted and len(calls)==1 and storage.read(db)==before
v,owner=envelope.restore(before['image'],selected_digest=before['digest'],bootstrap=S1,config=cfg,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(conditions));assert before['generation']==5 and v['head']==admitted['head'] and owner._revision==8 and owner._mutations==1
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED','G':5,'H':1,'R':8,'old_receipt_revision':7,'native_calls':len(n.calls),'application_evaluations':n.apps,'matcher_calls':matcher.calls,'qualification':prior,'admission_decisions':calls,'scope':'New actual live typed execution and durable whole-image commits; exact retained qualification and its 42 prior raw calls verified, not reexecuted. Current observe rights rechecked. No production durability/authentication or benchmark claim.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
