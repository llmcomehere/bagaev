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
args=configure(reference=True);R=args.output;select(args)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy;enc=envelope.encode
s=json.loads((D/'bridge.json').read_bytes());cfg=s['config'];expected=json.loads((D/'envelope.json').read_bytes());S1=s['packets']['A']['source'];S2=s['packets']['B']['source'];policy=image_codec.pin(cfg['policy']);R.mkdir(exist_ok=False)
def proposal(g=0,base=S1,target=S2):return {'expected':{'generation':g,'source':base},'target':target,'policy':policy,'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64}
def make(name):
 folder=R/name;folder.mkdir();n=Native(folder/'native');c=clone(s['conditions']);flags={'authority':True,'qualified':True,'callback':None};db=folder/'owner.sqlite'
 def qualifier(p,source):
  assert image_codec.pin(source)==p['target'];cb=flags['callback'];flags['callback']=None
  if cb:cb()
  return {'decision':'accepted' if flags['qualified'] else 'denied','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
 m=DurableProgrammes(cfg,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(c),authority=lambda:flags['authority'],qualifier=qualifier);m.create(db)
 return m,db,n,c,flags
def read(db):
 row=storage.read(db);return row,json.loads(row['image'])
def trace(db,action):
 row,v=read(db);return {'action':action,'G':row['generation'],'H':v['head']['generation'],'source':{S1:'S1',S2:'S2'}[v['head']['source']],'R':v['receiver']['revision'],'runs':len(v['runs']),'admissions':len(v['admissions'])}
m,db,n,c,flags=make('trace');actual=[trace(db,'create')];assert read(db)[1]['receiver']==s['images']['initial']
m.start(db,'old');actual.append(trace(db,'start-old'))
a=m.call(db,'old','submit',enc(s['packets']['A']));assert a['kind']=='Declined' and a['revision']==7;actual.append(trace(db,'decline-old'));assert read(db)[1]['receiver']==s['images']['declined']
first=m.admit(db,'M1',proposal());actual.append(trace(db,'admit-S2'))
m.start(db,'new');actual.append(trace(db,'start-new'));c['tick']=2
b=m.call(db,'new','submit',enc(s['packets']['B']));assert b['kind']=='Applied' and b['revision']==8;actual.append(trace(db,'apply-new'));assert read(db)[1]['receiver']==s['images']['applied']
c['tick']=3;apps=n.apps;before=read(db)[0];assert m.call(db,'old','observe',enc(s['packets']['A']))==a and n.apps==apps;assert read(db)[0]==before;actual.append(trace(db,'observe-old'))
m.admit(db,'M2',proposal(1,S2,S1));actual.append(trace(db,'admit-S1'));flags['authority']=False
assert m.admit(db,'M1',proposal())==first;actual.append(trace(db,'replay-first-admission'));assert n.apps==2
trace_match=actual==expected['trace'];(R/'trace.json').write_text(json.dumps({'actual':actual,'expected':expected['trace'],'matched':trace_match},indent=2)+'\n');assert trace_match
rows=[];native_calls=len(n.calls);applications=n.apps
for name,wanted in expected['refusals'].items():
 m,db,n,c,flags=make(name);m.start(db,'old');p=proposal();call=lambda:m.admit(db,'M1',p)
 if name=='ABA':m.admit(db,'M1',p);m.admit(db,'M2',proposal(1,S2,S1));call=lambda:m.admit(db,'M3',p)
 elif name=='changed-admission-intent':m.admit(db,'M1',p);p['qualification']='d'*64
 elif name=='duplicate-run':call=lambda:m.start(db,'old')
 elif name=='wrong-run-source':call=lambda:m.call(db,'old','submit',enc(s['packets']['B']))
 elif name=='unknown-run':call=lambda:m.call(db,'missing','submit',enc(s['packets']['A']))
 elif name=='denied-authority':flags['authority']=False
 elif name=='qualification-mismatch':flags['qualified']=False
 elif name=='late-head-change':flags['callback']=lambda:m.admit(db,'nested',p)
 elif name=='late-application-decline':flags['callback']=lambda:m.call(db,'old','submit',enc(s['packets']['A']))
 elif name=='run-capacity':
  before,v=read(db);v['runs']=[{'id':f'r{i:02d}','head':clone(v['head'])} for i in range(64)];storage.compare_and_swap(db,before['generation'],before['digest'],enc(v));call=lambda:m.start(db,'extra')
 elif name=='admission-capacity':
  before,v=read(db);v['admissions']=[]
  for i in range(64):
   ip=proposal(i,S1,S1);h={'generation':i+1,'source':S1};v['admissions'].append({'id':f'M{i:02d}','intent':ip,'receipt':{'kind':'Admitted','head':h}})
  v['head']=h;storage.compare_and_swap(db,before['generation'],before['digest'],enc(v));p=proposal(64,S1,S2)
 before,v=read(db)
 try:call();got='UNEXPECTED_SUCCESS'
 except (envelope.ProgrammeError,storage.StorageError) as e:got=e.code
 after,w=read(db)
 if name=='late-head-change':assert after['generation']==before['generation']+1 and w['head']['generation']==1 and [r['id'] for r in w['admissions']]==['nested'] and w['receiver']==v['receiver']
 elif name=='late-application-decline':assert after['generation']==before['generation']+1 and w['head']==v['head'] and w['admissions']==[] and w['receiver']==s['images']['declined']
 else:assert after==before
 rows.append({'id':name,'actual':got,'expected':wanted,'matched':got==wanted});native_calls+=len(n.calls);applications+=n.apps
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if trace_match and all(r['matched'] for r in rows) else 'FAILED','trace_steps':len(actual),'rows':rows,'native_calls':native_calls,'application_evaluations':applications,'scope':'Actual typed owner and SQLite CAS; admission receipts controlled to isolate ordering. Not new candidate refinement evidence.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['status']=='PASSED'
