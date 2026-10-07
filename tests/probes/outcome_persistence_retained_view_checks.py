from pathlib import Path
import copy,datetime,hashlib,json,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/outcome-persistence'
sys.path.insert(0,str(P/'src'))
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec
import bagaev_outcome_programme_image as envelope
import bagaev_outcome_retained_view as retained_view
from bagaev_outcome_durable_programmes import DurableProgrammes
from persistence_host import Native,select
from outcome_host import configure
args=configure(reference=True);R=args.output;select(args)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
s=json.loads((D/'bridge.json').read_bytes());cfg=s['config'];S1=s['packets']['A']['source'];S2=s['packets']['B']['source'];R.mkdir(exist_ok=False);rows=[]
p={'expected':{'generation':0,'source':S1},'target':S2,'policy':image_codec.pin(cfg['policy']),'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64}
def qualifier(p,source):return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
for name,wanted in json.loads((D/'retained-view.json').read_bytes())['cases']:
 folder=R/name;folder.mkdir();db=folder/'owner.sqlite';n=Native(folder/'native');conditions=clone(s['conditions'])
 m=DurableProgrammes(cfg,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(conditions),authority=lambda:True,qualifier=qualifier);m.create(db);m.start(db,'old');a=m.call(db,'old','submit',envelope.encode(s['packets']['A']));m.admit(db,'M1',p);m.start(db,'new');conditions['tick']=2;b=m.call(db,'new','submit',envelope.encode(s['packets']['B']));before=storage.read(db);assert before['generation']==5
 # Ordinary activation under a newly selected clock remains refused.
 newclock=clone(cfg);newclock['clock_domain']=cfg['clock_domain']+'.new';conditions['tick']=0
 ordinary=DurableProgrammes(newclock,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(conditions),authority=lambda:True,qualifier=qualifier)
 try:ordinary.call(db,'old','observe',envelope.encode(s['packets']['A']));raise AssertionError('clock conversion occurred')
 except image_codec.ImageError as e:assert e.code=='IMAGE_CLOCK'
 packet=clone(s['packets']['B'] if name=='old-applied' else s['packets']['A']);run='new' if name=='old-applied' else 'old';original=clone(cfg);ocalls=[0];lcalls=[0]
 if name=='changed-intent':packet['request']['quantity']=0
 if name=='absent-row':packet['key']['id']='never-observed'
 if name=='wrong-run-source':run='new'
 if name=='wrong-original-clock':original=newclock
 def observer():ocalls[0]+=1;return name!='denied' and not(name=='late-denial' and ocalls[0]==2)
 def blocked():lcalls[0]+=1;raise AssertionError('retained view requested live clock/rights')
 retained_view._no_live_conditions=blocked;apps=n.apps;calls=len(n.calls)
 try:
  answer=retained_view.observe_retained(db,original,bootstrap=S1,run_id=run,packet=envelope.encode(packet),checker=n.checker,evaluator=n.evaluator,observer=observer);actual=answer.get('kind',answer.get('status'))
  if name=='old-decline':assert answer==a and answer['revision']==7
  if name=='old-applied':assert answer==b and answer['revision']==8
 except (envelope.ProgrammeError,image_codec.ImageError) as e:actual=e.code
 assert storage.read(db)==before and n.apps==apps==2 and lcalls[0]==0
 if name=='denied':assert len(n.calls)==calls
 rows.append({'id':name,'actual':actual,'expected':wanted,'matched':actual==wanted,'native_calls':len(n.calls),'new_application_evaluations':n.apps-apps,'live_condition_calls':lcalls[0],'observer_calls':ocalls[0]})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'native_calls':sum(r['native_calls'] for r in rows),'setup_application_evaluations':16,'read_application_evaluations':0,'scope':'Actual typed retained-fact reads with independently selected original clock binding; normal new-domain activation still refuses. No live clock conversion, effect retry, migration, system permission or production authentication claim.'};(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert out['status']=='PASSED'
