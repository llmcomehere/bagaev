"""Retained-admission boundary with actual typed reconstruction."""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys
S=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(S/'src'),str(S/'tests/probes')]
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image
import bagaev_outcome_programme_image as envelope
from persistence_host import Native,select
from outcome_host import configure
a=configure(reference=True);select(a);R=a.output;R.mkdir()
D=S/'examples/probes/outcome-persistence'
for name,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==h
s=json.loads((D/'bridge.json').read_bytes());cfg=s['config'];S1=s['packets']['A']['source'];S2=s['packets']['B']['source']
p={'expected':{'generation':0,'source':S1},'target':S2,'policy':image.pin(cfg['policy']),'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64}
rows=[]
for label,source in [('candidate',S/'src/bagaev_outcome_durable_programmes.py')]:
 spec=importlib.util.spec_from_file_location(label,source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 for mode in ('stable','nested-start','aba'):
  folder=R/(label+'-'+mode);folder.mkdir();db=folder/'owner.sqlite';n=Native(folder/'typed');armed=[False];counts={'qualifier':0,'authority':0}
  def authority():counts['authority']+=1;return True
  def qualifier(proposal,raw):
   counts['qualifier']+=1
   return {'decision':'accepted','binding':{k:proposal[k] for k in ('target','policy','assertions','producer','qualification')}}
  def checker(raw,policy):
   answer=n.checker(raw,policy)
   if armed[0]:
    armed[0]=False
    if mode=='nested-start':manager.start(db,'nested')
    elif mode=='aba':
     v=json.loads(before['image']);v['runs'].append({'id':'nested','head':copy.deepcopy(v['head'])})
     other=storage.compare_and_swap(db,before['generation'],before['digest'],envelope.encode(v))
     storage.compare_and_swap(db,other['generation'],other['digest'],before['image'])
   return answer
  manager=module.DurableProgrammes(cfg,bootstrap=S1,checker=checker,evaluator=n.evaluator,conditions=lambda:copy.deepcopy(s['conditions']),authority=authority,qualifier=qualifier)
  manager.create(db);receipt=manager.admit(db,'M1',p);before=storage.read(db);assert before['generation']==1
  setup=dict(counts);calls=len(n.calls);apps=n.apps;armed[0]=mode!='stable'
  try:actual={'returned':manager.admit(db,'M1',p)}
  except storage.StorageError as error:actual={'raised':error.code}
  expected={'returned':receipt} if mode=='stable' else {'raised':'STORAGE_CONFLICT'}
  after=storage.read(db);assert after['generation']=={'stable':1,'nested-start':2,'aba':3}[mode]
  if mode in ('stable','aba'):assert after['image']==before['image']
  else:assert json.loads(after['image'])['runs']==[{'id':'nested','head':receipt['head']}]
  assert counts['qualifier']==setup['qualifier'] and counts['authority']==setup['authority']+(mode=='nested-start') and n.apps==apps==0
  observed=len(n.calls)-calls;retry_calls=len(n.calls)
  assert manager.admit(db,'M1',p)==receipt and storage.read(db)==after and n.apps==0
  rows.append({'version':label,'case':mode,'actual':actual,'expected':expected,'matches':actual==expected,'G_before':1,'G_after':after['generation'],'typed_calls':observed,'explicit_retry_calls':len(n.calls)-retry_calls,'applications':0,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
assert all(r['matches'] for r in rows if r['version']=='candidate')
out={'status':'PASSED','rows':rows,'reader':a.reader_sha256,'reference':a.reference_sha256,'scope':'Actual typed reconstruction, serial synthetic callbacks and real SQLite; controlled qualification receipts; no native application kernel or model.'}
(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
