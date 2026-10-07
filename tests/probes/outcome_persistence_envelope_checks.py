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
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
s=json.loads((D/'bridge.json').read_bytes());cfg=s['config'];S1=s['packets']['A']['source'];S2=s['packets']['B']['source'];policy=image_codec.pin(cfg['policy'])
h0={'generation':0,'source':S1};h1={'generation':1,'source':S2};h2={'generation':2,'source':S1}
def admission(i,previous,target):
 h={'generation':previous['generation']+1,'source':target}
 return {'id':i,'intent':{'expected':clone(previous),'target':target,'policy':policy,'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64},'receipt':{'kind':'Admitted','head':h}}
initial={'schema':'owned-programmes-image/1','bootstrap':S1,'head':h0,'receiver':s['images']['initial'],'runs':[],'admissions':[]}
history=clone(initial);history.update(head=h2,admissions=[admission('M1',h0,S2),admission('M2',h1,S1)],runs=[{'id':'new','head':h1},{'id':'old','head':h0}]);history['receiver']=s['images']['applied']
fixtures={'initial':clone(initial),'history-two-admissions':clone(history),'ABA-run-pins':clone(history)}
fixtures['ABA-run-pins']['runs'].append({'id':'return','head':h2})
for name,_ in json.loads((D/'envelope.json').read_bytes())['codec_cases']:
 if name not in fixtures:fixtures[name]=clone(history)
fixtures['wrong-bootstrap']['bootstrap']=S2
fixtures['extra-field']['permission']=True
fixtures['head-bool']['head']['generation']=True
fixtures['head-gap']['head']['generation']=3
fixtures['history-gap']['admissions'][1]['receipt']['head']['generation']=3
fixtures['history-wrong-base']['admissions'][1]['intent']['expected']=clone(h0)
fixtures['history-wrong-policy']['admissions'][1]['intent']['policy']='0'*64
fixtures['duplicate-admission-id']['admissions'][1]['id']='M1'
fixtures['changed-receipt-target']['admissions'][1]['receipt']['head']['source']=S2
fixtures['unknown-target']['admissions'][1]['intent']['target']='0'*64
fixtures['run-unknown-generation']['runs'][0]['head']={'generation':3,'source':S2}
fixtures['run-wrong-source']['runs'][0]['head']['source']=S1
fixtures['duplicate-run']['runs'][1]['id']='new'
fixtures['unsorted-runs']['runs'].reverse()
fixtures['too-many-runs']['runs']=[{'id':f'r{i:02d}','head':clone(h0)} for i in range(65)]
fixtures['too-many-admissions']['admissions']*=33
fixtures['unbound-terminal-source']['runs']=[{'id':'old','head':clone(h0)}]
R.mkdir(exist_ok=False);rows=[];n=Native(R/'native')
for name,expected in json.loads((D/'envelope.json').read_bytes())['codec_cases']:
 raw=envelope.encode(fixtures[name]);(R/(name+'.json')).write_bytes(raw)
 try:
  decoded,owner=envelope.restore(raw,selected_digest=sha(raw),bootstrap=S1,config=cfg,checker=n.checker,evaluator=n.evaluator,conditions=lambda:clone(s['conditions']))
  assert envelope.encode(decoded)==raw and owner._revision==fixtures[name]['receiver']['revision'];actual='PASS'
 except envelope.ProgrammeError as e:actual=e.code
 rows.append({'id':name,'expected':expected,'actual':actual,'matched':expected==actual})
assert n.apps==0
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'native_calls':len(n.calls),'application_evaluations':n.apps,'scope':'Structural programme history plus typed receiver reconstruction. No live admission, runtime refinement or authority proof.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['status']=='PASSED'
