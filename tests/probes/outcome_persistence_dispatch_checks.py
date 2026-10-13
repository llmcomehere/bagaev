"""Three no-op dispatch conflicts with actual typed reconstruction and SQLite."""
from pathlib import Path
import copy,hashlib,json,sys
T=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image
import bagaev_outcome_programme_image as envelope
from bagaev_outcome_durable_programmes import DurableProgrammes
from persistence_host import Native,select
from outcome_host import configure
args=configure(reference=True);select(args)
fixtures=T/'examples/probes/outcome-persistence'
for name,digest in json.loads((fixtures/'manifest.json').read_bytes())['sha256'].items():
 assert hashlib.sha256((fixtures/name).read_bytes()).hexdigest()==digest
data=json.loads((T/'examples/probes/outcome-persistence/bridge.json').read_bytes())
R=args.output;R.mkdir(exist_ok=False);rows=[]
for command in ('submit','observe','cancel'):
 folder=R/command;folder.mkdir();native=Native(folder/'native');db=folder/'owner.sqlite'
 cfg=copy.deepcopy(data['config']);packet=envelope.encode(data['packets']['A']);source=data['packets']['A']['source'];armed=[False]
 def checker(raw,policy):
  checked=native.checker(raw,policy)
  if armed[0]:
   armed[0]=False
   manager.start(db,'nested')
  return checked
 manager=DurableProgrammes(cfg,bootstrap=source,checker=checker,evaluator=native.evaluator,conditions=lambda:copy.deepcopy(data['conditions']),authority=lambda:True,qualifier=lambda *a: {'decision':'invalid'})
 manager.create(db);manager.start(db,'old')
 result=manager.call(db,'old','submit',packet)
 assert result['kind']=='Declined' and result['revision']==7
 before=storage.read(db);assert before['generation']==2;apps=native.apps;armed[0]=True
 try:manager.call(db,'old',command,packet);raise AssertionError('stale result returned')
 except storage.StorageError as error:assert error.code=='STORAGE_CONFLICT'
 after=storage.read(db);a=json.loads(after['image']);b=json.loads(before['image'])
 assert after['generation']==3 and a['receiver']==b['receiver'] and a['head']==b['head']
 assert [r['id'] for r in a['runs']]==['nested','old'] and native.apps==apps==1
 stable=storage.read(db);assert manager.call(db,'old',command,packet)==result
 assert storage.read(db)==stable and native.apps==apps
 rows.append({'command':command,'refusal':'STORAGE_CONFLICT','G_before':2,'G_after':3,'H':0,'R':7,'application_evaluations':native.apps,'typed_calls':len(native.calls),'explicit_retry':'retained Declined; no write or application evaluation'})
out={'status':'PASSED','cases':rows,'scope':'Actual typed reconstruction and SQLite; serial synthetic nested callback. No new application policy, native generated kernel, crash or production guarantee.'}
(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
