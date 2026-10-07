"""Readable composed business rules through actual typed execution and SQLite image CAS."""
from pathlib import Path
import json,hashlib,sys,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/stock-adjustment'
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
from outcome_host import configure
args=configure(reference=True);R=args.output
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_component_match_form as form
import bagaev_component_match_diagnostics as diagnostic
import bagaev_component_edit as edit
import bagaev_owner_image_store as storage
from bagaev_outcome_storage import Bridge
from persistence_host import Native,explicit
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
s=json.loads((D/'cases.json').read_bytes());text=(D/'StockAdjustment.bagaev').read_bytes();assert form.decode(text)==s['source'];assert form.decode(form.encode(s['source']))==s['source'];assert diagnostic.diagnose(text)['valid_form'] is True
explicit({k:str(getattr(args,k)) for k in ['reader','reference','reader_sha256','reference_sha256']})
R.mkdir(exist_ok=False);native=Native(R/'native');conditions=copy.deepcopy(s['conditions'])
def bridge():return Bridge(s['config'],checker=native.checker,evaluator=native.evaluator,conditions=lambda:copy.deepcopy(conditions))
m=bridge();db=R/'stock.sqlite';m.create(db);rows=[]
for step in s['steps']:
 name=step['packet'];conditions['observe']=name!='E';actual=m.call(db,'submit',edit.canonical(s['packets'][name]));assert actual==step['answer'],(name,actual,step['answer'])
 saved=storage.read(db);image=json.loads(saved['image']);assert saved['generation']==step['generation'] and image['revision']==step['revision'] and image['state']['quantity']==step['quantity'] and image['mutations']==step['mutations'] and native.apps==step['application_evaluations'],(name,saved,native.apps)
 rows.append({'id':name,'answer':actual,'generation':saved['generation'],'revision':image['revision'],'quantity':image['state']['quantity'],'application_evaluations':native.apps})
# Reconstruct with the same explicitly selected source, policy and clock domain.
m=bridge();before=storage.read(db);apps=native.apps
replayed=m.call(db,'submit',edit.canonical(s['packets']['E']));(R/'replay-denied.json').write_text(json.dumps(replayed));assert replayed=={'status':'AccessDenied'}
assert storage.read(db)==before and native.apps==apps
conditions.update(observe=True,write=False,submit=False,tick=2)
for name in ['E','A']:
 assert m.call(db,'observe',edit.canonical(s['packets'][name]))==s['receipts'][name]
 assert storage.read(db)==before and native.apps==apps
assert m.call(db,'submit',edit.canonical(s['packets']['F']))=={'status':'AccessDenied'}
assert storage.read(db)==before and native.apps==apps==5
assert (D/'StockAdjustment.bagaev').read_bytes()==text
result={'status':'PASSED','source_sha256':hashlib.sha256(edit.canonical(s['source'])).hexdigest(),'steps':rows,'native_calls':len(native.calls),'application_evaluations':native.apps,'generation':5,'revision':10,'mutations':3,'quantity':7,'old_decline_revision':7,'reconstructed_replay_new_evaluations':0,'new_write_denied':True,'scope':'Single fixed source, serial trusted Linux/CPython/SQLite profile. Object reconstruction, not process/power-loss recovery; no new source admission, H transition, real authority, production durability or measurement.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='steps'}))
