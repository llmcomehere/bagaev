"""A recovery cutoff prevents new execution, not observation of an old fact."""
from pathlib import Path
import copy, hashlib, json, sys
T=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_component_edit as edit
import bagaev_owner_image_store as storage
from bagaev_outcome_storage import Bridge
from persistence_host import Native,explicit

point,cutoff,stage,db_path,selection_path,out_path=sys.argv[1:]
assert point in ('before','after') and cutoff in ('deadline','epoch') and stage in ('resume','verify')
db=Path(db_path);out=Path(out_path)
assert db.is_absolute() and out.is_absolute() and out.parent.is_dir() and not out.exists()
explicit(json.loads(Path(selection_path).read_bytes()))
D=T/'examples/probes/stock-adjustment'
for name,digest in json.loads((D/'manifest.json').read_bytes())['sha256'].items():
 assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest
s=json.loads((D/'cases.json').read_bytes());out.mkdir();native=Native(out/'native')
conditions=copy.deepcopy(s['conditions'])
conditions.update(tick=101 if cutoff=='deadline' else 2,epoch=1 if cutoff=='deadline' else 2,
                  observe=True,submit=False,write=False,cancel=False)
bridge=Bridge(s['config'],checker=native.checker,evaluator=native.evaluator,conditions=lambda:copy.deepcopy(conditions))
packet=edit.canonical(s['packets']['E'])
refused={'kind':'Refused','reason':'DeadlineExpired' if cutoff=='deadline' else 'EpochMismatch','revision':9}
terminal=refused if point=='before' else s['receipts']['E']
before=storage.read(db);initial=json.loads(before['image'])
assert initial['revision']==(9 if point=='before' else 10)
assert initial['state']['quantity']==(0 if point=='before' else 7)
assert initial['mutations']==(2 if point=='before' else 3)
if stage=='resume':
 assert before['generation']==(4 if point=='before' else 5)
 assert bridge.call(db,'observe',packet)==({'status':'Unknown'} if point=='before' else terminal)
 assert bridge.call(db,'submit',packet)=={'status':'AccessDenied'}
 assert storage.read(db)==before and native.apps==0
 conditions.update(submit=True,write=True)
 assert bridge.call(db,'submit',packet)==terminal
 after=storage.read(db);assert after['generation']==5 and native.apps==0
 if point=='after':assert after==before
 conditions['write']=False
 assert bridge.call(db,'submit',packet)==terminal
 assert storage.read(db)==after and native.apps==0
else:
 assert before['generation']==5
 after=before
assert bridge.call(db,'observe',packet)==terminal
assert storage.read(db)==after and native.apps==0
final=json.loads(after['image'])
assert final['state']==initial['state'] and final['revision']==initial['revision'] and final['mutations']==initial['mutations']
result={'point':point,'cutoff':cutoff,'stage':stage,'status':'PASSED','initial_digest':before['digest'],
 'final_digest':after['digest'],'terminal':terminal,'G':5,'R':final['revision'],
 'quantity':final['state']['quantity'],'mutations':final['mutations'],
 'application_evaluations':native.apps,'typed_calls':len(native.calls)}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
