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
clone=copy.deepcopy;sha=lambda b:hashlib.sha256(b).hexdigest()
s=json.loads((D/'bridge.json').read_bytes());S1=s['packets']['A']['source'];S2=s['packets']['B']['source'];cfg=s['config'];R.mkdir(exist_ok=False);rows=[]
p={'expected':{'generation':0,'source':S1},'target':S2,'policy':image_codec.pin(cfg['policy']),'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64}
def qualified(p,source):return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
for case in json.loads((D/'cuts.json').read_bytes())['cases']:
 folder=R/case['id'];folder.mkdir();db=folder/'owner.sqlite';n=Native(folder/'native');m=DurableProgrammes(cfg,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(s['conditions']),authority=lambda:True,qualifier=qualified)
 m.create(db);m.start(db,'old');a=m.call(db,'old','submit',envelope.encode(s['packets']['A']))
 if case['operation']=='start':m.admit(db,'M1',p)
 before=storage.read(db);old=json.loads(before['image']);fixture=folder/'fixture.json';fixture.write_bytes(envelope.encode({'config':cfg,'bootstrap':S1,'conditions':s['conditions'],'proposal':p,'operation':case['operation'],'point':case['point'],'executables':{k:str(getattr(args,k)) for k in ('reader','reference','reader_sha256','reference_sha256')}}))
 z=subprocess.run([sys.executable,'-B',str(O/'outcome_persistence_fault_child.py'),str(db),str(fixture),str(folder/'child-native')],capture_output=True,timeout=30)
 (folder/'child.stdout').write_bytes(z.stdout);(folder/'child.stderr').write_bytes(z.stderr);assert not z.stdout and not z.stderr
 row=storage.read(db);v,owner=envelope.restore(row['image'],selected_digest=row['digest'],bootstrap=S1,config=cfg,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(s['conditions']))
 wanted=clone(old)
 if case['point']=='after':
  if case['operation']=='start':wanted['runs'].insert(0,{'id':'new','head':clone(wanted['head'])})
  else:
   wanted['head']={'generation':1,'source':S2};wanted['admissions'].append({'id':'M1','intent':clone(p),'receipt':{'kind':'Admitted','head':clone(wanted['head'])}})
 assert envelope.encode(wanted)==row['image'] and v['receiver']==s['images']['declined']
 beforeapps=n.apps;assert m.call(db,'old','observe',envelope.encode(s['packets']['A']))==a and n.apps==beforeapps
 child=json.loads((folder/'child-native/calls.json').read_bytes());assert child['application_evaluations']==0
 actual={'id':case['id'],'operation':case['operation'],'point':case['point'],'exit':z.returncode,'G':row['generation'],'H':v['head']['generation'],'runs':len(v['runs']),'admissions':len(v['admissions']),'R':v['receiver']['revision']}
 rows.append({'actual':actual,'expected':case,'matched':actual==case,'parent_calls':len(n.calls),'child_calls':len(child['calls'])})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'native_calls':sum(r['parent_calls']+r['child_calls'] for r in rows),'application_evaluations':4,'scope':'Four selected serial own-process dirty COMMIT cuts; controlled admission qualifications. No power-loss, arbitrary interruption or production durability claim.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['status']=='PASSED'
