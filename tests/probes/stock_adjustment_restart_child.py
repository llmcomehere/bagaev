"""One explicitly selected stage of the serial stock restart experiment."""
from pathlib import Path
import copy,hashlib,json,os,sqlite3,sys
T=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_component_edit as edit
import bagaev_owner_image_store as storage
from bagaev_outcome_storage import Bridge
from persistence_host import Native,explicit

stage,db_path,selection_path,out_path=sys.argv[1:]
assert stage in ('cut','recover','verify')
db=Path(db_path);out=Path(out_path)
assert db.is_absolute() and out.is_absolute() and out.parent.is_dir() and not out.exists()
selection=json.loads(Path(selection_path).read_bytes());explicit(selection)
D=T/'examples/probes/stock-adjustment'
for name,digest in json.loads((D/'manifest.json').read_bytes())['sha256'].items():
 assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest
s=json.loads((D/'cases.json').read_bytes());out.mkdir();native=Native(out/'native')
conditions=copy.deepcopy(s['conditions'])
bridge=Bridge(s['config'],checker=native.checker,evaluator=native.evaluator,conditions=lambda:copy.deepcopy(conditions))
packet=lambda name:edit.canonical(s['packets'][name])
expected_f={'kind':'Applied','key':copy.deepcopy(s['packets']['F']['key']),
 'intent':{k:copy.deepcopy(s['packets']['F'][k]) for k in ('source','request','epoch','deadline')},
 'revision':11,'state':{'key':{'code':'sku1'},'note':'kept','quantity':8}}

if stage=='cut':
 armed=[False];original=sqlite3.connect
 class CutConnection(sqlite3.Connection):
  dirty=False
  def execute(self,sql,*args,**kwargs):
   value=super().execute(sql,*args,**kwargs)
   if sql.startswith('UPDATE image SET'):self.dirty=True
   if sql=='COMMIT' and self.dirty and armed[0]:os._exit(87)
   return value
 def connect(*args,**kwargs):kwargs['factory']=CutConnection;return original(*args,**kwargs)
 sqlite3.connect=connect
 bridge.create(db)
 for step in s['steps']:
  name=step['packet'];conditions['observe']=name!='E';armed[0]=name=='E'
  result=bridge.call(db,'submit',packet(name))
  assert result==step['answer']
  row=storage.read(db);image=json.loads(row['image'])
  assert row['generation']==step['generation'] and image['revision']==step['revision'] and image['state']['quantity']==step['quantity']
 raise AssertionError('selected post-COMMIT cut not reached')

before=storage.read(db);initial=json.loads(before['image'])
conditions.update(tick=2,observe=False)
if stage=='recover':
 assert before['generation']==5 and initial['revision']==10 and initial['state']['quantity']==7 and initial['mutations']==3
 assert bridge.call(db,'submit',packet('E'))=={'status':'AccessDenied'}
 conditions.update(observe=True,submit=False,write=False)
 for name in ('E','A'):assert bridge.call(db,'observe',packet(name))==s['receipts'][name]
 assert bridge.call(db,'submit',packet('F'))=={'status':'AccessDenied'}
 assert storage.read(db)==before and native.apps==0
 conditions.update(submit=True,write=True,tick=3)
 assert bridge.call(db,'submit',packet('F'))==expected_f
 assert native.apps==1
else:
 assert before['generation']==6 and initial['revision']==11 and initial['state']['quantity']==8 and initial['mutations']==4
 conditions.update(tick=3,observe=True,submit=False,write=False)
 assert bridge.call(db,'observe',packet('F'))==expected_f
 for name in ('E','A'):assert bridge.call(db,'observe',packet(name))==s['receipts'][name]
 assert storage.read(db)==before and native.apps==0

after=storage.read(db);image=json.loads(after['image']);apps=native.apps
assert bridge.call(db,'observe',packet('E'))==s['receipts']['E']
assert storage.read(db)==after and native.apps==apps
assert after['generation']==6 and image['revision']==11 and image['state']['quantity']==8 and image['mutations']==4
result={'stage':stage,'status':'PASSED','initial_digest':before['digest'],'final_digest':after['digest'],
 'G':6,'R':11,'quantity':8,'mutations':4,'application_evaluations':native.apps,'typed_calls':len(native.calls)}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
