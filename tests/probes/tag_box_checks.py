"""Actual typed TextList business rules and unchanged durable receiver boundaries."""
from pathlib import Path
import json,hashlib,copy,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/tag-box'
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
from outcome_host import configure
args=configure(reference=True);R=args.output
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_component_text_list_form as form
import bagaev_component_edit as edit
import bagaev_owner_image_store as storage
import bagaev_component_owner as base
from bagaev_outcome_storage import Bridge
from persistence_host import Native,explicit
for name,pin in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==pin
s=json.loads((D/'cases.json').read_bytes());raw=(D/'TagBox.bagaev').read_bytes();assert form.decode(raw)==s['source'];assert form.decode(form.encode(s['source']))==s['source']
explicit({k:str(getattr(args,k)) for k in ['reader','reference','reader_sha256','reference_sha256']})
R.mkdir(exist_ok=False);conditions=copy.deepcopy(s['conditions']);n=Native(R/'main-native')
def make(config,native):return Bridge(config,checker=native.checker,evaluator=native.evaluator,conditions=lambda:copy.deepcopy(conditions))
m=make(s['config'],n);db=R/'tags.sqlite';m.create(db);rows=[]
for step in s['steps']:
 name=step['packet'];conditions['observe']=name!='D';actual=m.call(db,'submit',edit.canonical(s['packets'][name]));assert actual==step['answer'],(name,actual,step['answer']);saved=storage.read(db);image=json.loads(saved['image']);assert saved['generation']==step['generation'] and image['revision']==step['revision'] and image['state']['tags']==step['tags'] and image['mutations']==step['mutations'] and n.apps==step['application_evaluations'];rows.append({'id':name,'answer':actual,'generation':saved['generation'],'revision':image['revision'],'tags':image['state']['tags']})
m=make(s['config'],n);before=storage.read(db);apps=n.apps;assert m.call(db,'submit',edit.canonical(s['packets']['D']))=={'status':'AccessDenied'};assert storage.read(db)==before and n.apps==apps
conditions.update(observe=True,write=False,submit=False,tick=2)
for name in ['D','A']:assert m.call(db,'observe',edit.canonical(s['packets'][name]))==s['receipts'][name];assert storage.read(db)==before and n.apps==apps
assert m.call(db,'submit',edit.canonical(s['packets']['E']))=={'status':'AccessDenied'};assert storage.read(db)==before and n.apps==apps==4
conditions.update(s['conditions']);full_native=Native(R/'full-native');m=make(s['full']['config'],full_native);full_db=R/'full.sqlite';m.create(full_db);assert m.call(full_db,'submit',edit.canonical(s['full']['packet']))==s['full']['receipt'];saved=storage.read(full_db);image=json.loads(saved['image']);assert saved['generation']==1 and image['revision']==1 and image['mutations']==0 and image['state']==s['full']['config']['origin']['state'] and full_native.apps==1
byte_native=Native(R/'bytes-native');m=make(s['bytes']['config'],byte_native);byte_db=R/'bytes.sqlite';m.create(byte_db);before=storage.read(byte_db)
try:m.call(byte_db,'submit',edit.canonical(s['bytes']['packet']))
except base.OwnerEvaluationError as error:assert error.code==s['bytes']['owner_error']
else:raise AssertionError('aggregate overflow became business result')
wire=json.loads((byte_native.out/f'{len(byte_native.calls):03d}.stdout').read_bytes());assert wire['reason']==s['bytes']['core_reason'] and wire['status']!='success';assert storage.read(byte_db)==before and byte_native.apps==1
assert (D/'TagBox.bagaev').read_bytes()==raw
result={'status':'PASSED','main_steps':rows,'main_generation':4,'main_revision':3,'main_mutations':2,'main_business_evaluations':n.apps,'main_native_calls':len(n.calls),'full_native_calls':len(full_native.calls),'bytes_native_calls':len(byte_native.calls),'full_business_decline':True,'byte_failure_uncommitted':True,'replay_new_business_evaluations':0,'scope':'Fixed source and trusted serial SQLite/callback profile; no source admission, process crash, production authority or measurement.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='main_steps'}))
