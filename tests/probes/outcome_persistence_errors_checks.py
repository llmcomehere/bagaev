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
s=json.loads((D/'bridge.json').read_bytes());cfg=s['config'];S1=s['packets']['A']['source'];S2=s['packets']['B']['source'];R.mkdir(exist_ok=False);rows=[];original=sqlite3.connect
p={'expected':{'generation':0,'source':S1},'target':S2,'policy':image_codec.pin(cfg['policy']),'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64}
for case in json.loads((D/'errors.json').read_bytes())['cases']:
 folder=R/case['id'];folder.mkdir();db=folder/'owner.sqlite';n=Native(folder/'native');qc=[0];allowed=[True]
 def qualifier(p,source):qc[0]+=1;return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
 m=DurableProgrammes(cfg,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(s['conditions']),authority=lambda:allowed[0],qualifier=qualifier);m.create(db)
 if case['operation']=='admit':m.start(db,'old')
 before=storage.read(db);triggered=[False]
 class FaultConnection(sqlite3.Connection):
  dirty=False
  def execute(self,sql,*args,**kwargs):
   if sql.startswith('UPDATE image SET') and case['point']=='before':triggered[0]=True;raise sqlite3.OperationalError('controlled before update')
   result=super().execute(sql,*args,**kwargs)
   if sql.startswith('UPDATE image SET'):self.dirty=True
   if sql=='COMMIT' and self.dirty and case['point']=='after':triggered[0]=True;raise sqlite3.OperationalError('controlled committed response loss')
   return result
 def connect(*args,**kwargs):kwargs['factory']=FaultConnection;return original(*args,**kwargs)
 def call():return m.admit(db,'M1',p) if case['operation']=='admit' else m.start(db,'new')
 sqlite3.connect=connect
 try:
  try:call();raise AssertionError('injected failure did not occur')
  except storage.StorageError as e:error=e.code
 finally:sqlite3.connect=original
 assert triggered[0];after=storage.read(db);v=json.loads(after['image'])
 if case['point']=='before':assert after==before
 else:assert after['generation']==before['generation']+1
 if case['operation']=='admit' and case['point']=='after':allowed[0]=False
 try:
  answer=call();retry=answer['kind'] if case['operation']=='admit' else 'Started'
 except envelope.ProgrammeError as e:retry=e.code
 final=storage.read(db);f=json.loads(final['image']);assert f['receiver']==json.loads(before['image'])['receiver'] and n.apps==0
 if case['point']=='after':assert final==after
 if case['operation']=='admit':assert f['head']=={'generation':1,'source':S2} and len(f['admissions'])==1
 else:assert f['runs']==[{'id':'new','head':{'generation':0,'source':S1}}]
 actual={'id':case['id'],'operation':case['operation'],'point':case['point'],'error':error,'G_after_error':after['generation'],'H_after_error':v['head']['generation'],'retry':retry,'G_after_retry':final['generation'],'qualification_calls':qc[0]}
 rows.append({'actual':actual,'expected':case,'matched':actual==case,'native_calls':len(n.calls)})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'native_calls':sum(r['native_calls'] for r in rows),'applications':0,'scope':'Controlled SQLite errors, not real storage failure. Full envelope unchanged before UPDATE, retained after COMMIT. Explicit separate retries only.'};(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert out['status']=='PASSED'
