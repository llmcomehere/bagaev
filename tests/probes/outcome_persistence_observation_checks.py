from pathlib import Path
import copy,datetime,hashlib,json,sqlite3,sys
P=Path(__file__).resolve().parents[2];O=Path(__file__).parent;D=P/'examples/probes/outcome-persistence'
sys.path.insert(0,str(P/'src'))
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_durable_programmes import DurableProgrammes
from bagaev_outcome_management_observation import observe_management
from persistence_host import Native,select
from outcome_host import configure
args=configure(reference=True);R=args.output;select(args)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
s=json.loads((D/'bridge.json').read_bytes());cfg=s['config'];S1=s['packets']['A']['source'];S2=s['packets']['B']['source'];R.mkdir(exist_ok=False);rows=[]
p={'expected':{'generation':0,'source':S1},'target':S2,'policy':image_codec.pin(cfg['policy']),'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64}
for name,wanted in json.loads((D/'observation.json').read_bytes())['cases']:
 folder=R/name;folder.mkdir();db=folder/'owner.sqlite';n=Native(folder/'native');permitted=[True];ocalls=[0]
 def qualifier(p,source):return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
 m=DurableProgrammes(cfg,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(s['conditions']),authority=lambda:True,qualifier=qualifier);m.create(db)
 if name=='lost-start-after-new-head':
  original=sqlite3.connect
  class LostResponse(sqlite3.Connection):
   dirty=False
   def execute(self,sql,*args,**kwargs):
    result=super().execute(sql,*args,**kwargs)
    if sql.startswith('UPDATE image SET'):self.dirty=True
    if sql=='COMMIT' and self.dirty:raise sqlite3.OperationalError('controlled committed response loss')
    return result
  def connect(*args,**kwargs):kwargs['factory']=LostResponse;return original(*args,**kwargs)
  sqlite3.connect=connect
  try:
   try:m.start(db,'old');raise AssertionError('expected unavailable response')
   except storage.StorageError as e:assert e.code=='STORAGE_UNAVAILABLE'
  finally:sqlite3.connect=original
 else:m.start(db,'old')
 m.admit(db,'M1',p);kind='run';identifier='old';before=storage.read(db);assert before['generation']==2
 if name in ('retained-admission','absent-admission'):kind='admission';identifier='M1'
 if name in ('absent-run','absent-admission','denied-absent'):identifier='missing'
 if name in ('denied-existing','denied-absent'):permitted[0]=False
 if name=='invalid-id':identifier='../other'
 if name=='invalid-kind':kind='restore'
 if name=='revoked-during-check':
  def checker(source,policy):result=n.checker(source,policy);permitted[0]=False;return result
  m.checker=checker
 def observer():
  ocalls[0]+=1
  if name=='changed-during-final-permission' and ocalls[0]==2:m.start(db,'nested')
  return permitted[0]
 calls_before=len(n.calls)
 try:answer=observe_management(m,db,kind,identifier,observer=observer);actual=answer['status']
 except envelope.ProgrammeError as e:actual=e.code;answer=None
 after=storage.read(db)
 if name=='changed-during-final-permission':assert after['generation']==3 and len(json.loads(after['image'])['runs'])==2
 else:assert after==before
 if name in ('denied-existing','denied-absent','invalid-id','invalid-kind'):assert len(n.calls)==calls_before
 if name=='lost-start-after-new-head':
  assert answer=={'status':'Known','binding':{'id':'old','head':{'generation':0,'source':S1}}};answer['binding']['head']['source']='corrupted-return';assert storage.read(db)==before
 elif name=='retained-admission':assert answer=={'status':'Known','receipt':{'kind':'Admitted','head':{'generation':1,'source':S2}}}
 assert n.apps==0
 rows.append({'id':name,'actual':actual,'expected':wanted,'matched':actual==wanted,'native_calls':len(n.calls),'observer_calls':ocalls[0]})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'native_calls':sum(r['native_calls'] for r in rows),'application_evaluations':0,'scope':'Read-only management recovery under explicit host callback; actual typed reconstruction, controlled admission receipts and response-loss fault. No system permission or production authorization claim.'};(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert out['status']=='PASSED'
