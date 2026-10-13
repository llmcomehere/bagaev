"""Actual typed direct-bridge no-op conflicts with a nested cancellation."""
from pathlib import Path
import copy,hashlib,json,sys
T=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_owner_image_store as storage
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_storage import Bridge
from persistence_host import Native,select
from outcome_host import configure
args=configure(reference=True);select(args)
fixtures=T/'examples/probes/outcome-persistence'
for name,digest in json.loads((fixtures/'manifest.json').read_bytes())['sha256'].items():
 assert hashlib.sha256((fixtures/name).read_bytes()).hexdigest()==digest
data=json.loads((fixtures/'bridge.json').read_bytes())
R=args.output;R.mkdir(exist_ok=False);rows=[]
for command in ('submit','observe','cancel'):
 folder=R/command;folder.mkdir();native=Native(folder/'native');db=folder/'owner.sqlite'
 cfg=copy.deepcopy(data['config']);packet=envelope.encode(data['packets']['A']);armed=[False]
 other=copy.deepcopy(data['packets']['A']);other['key']['id']='nested-cancel';other=envelope.encode(other)
 def checker(raw,policy):
  checked=native.checker(raw,policy)
  if armed[0]:
   armed[0]=False
   assert bridge.call(db,'cancel',other)['kind']=='Cancelled'
  return checked
 bridge=Bridge(cfg,checker=checker,evaluator=native.evaluator,conditions=lambda:copy.deepcopy(data['conditions']))
 bridge.create(db);result=bridge.call(db,'submit',packet)
 assert result['kind']=='Declined' and result['revision']==7
 before=storage.read(db);assert before['generation']==1;apps=native.apps;armed[0]=True
 try:bridge.call(db,command,packet);raise AssertionError('stale result returned')
 except storage.StorageError as error:assert error.code=='STORAGE_CONFLICT'
 after=storage.read(db);assert after['generation']==2 and json.loads(after['image'])['revision']==7
 assert native.apps==apps==1
 stable=storage.read(db);assert bridge.call(db,command,packet)==result
 assert bridge.call(db,'observe',other)['kind']=='Cancelled'
 assert storage.read(db)==stable and native.apps==apps
 rows.append({'command':command,'refusal':'STORAGE_CONFLICT','G_before':1,'G_after':2,'R':7,'application_evaluations':native.apps,'typed_calls':len(native.calls),'nested_receipt':'Cancelled','explicit_retry':'old Declined; no write or application evaluation'})
out={'status':'PASSED','cases':rows,'scope':'Actual typed reconstruction and SQLite with a serial synthetic nested cancellation. No generated kernel, new application policy or production fault claim.'}
(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
