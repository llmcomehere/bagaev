"""Selected pre-COMMIT interruption and explicitly admitted retry of the same intent."""
from pathlib import Path
import copy,hashlib,json,os,sqlite3,sys
T=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(T/'src'),str(T/'tests/probes')]
import bagaev_component_edit as edit
import bagaev_owner_image_store as storage
from bagaev_outcome_storage import Bridge
from persistence_host import Native,explicit

stage,db_path,selection_path,out_path=sys.argv[1:]
assert stage in ('cut','retry','verify')
db=Path(db_path);out=Path(out_path)
assert db.is_absolute() and out.is_absolute() and out.parent.is_dir() and not out.exists()
explicit(json.loads(Path(selection_path).read_bytes()))
D=T/'examples/probes/stock-adjustment'
for name,digest in json.loads((D/'manifest.json').read_bytes())['sha256'].items():
 assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest
s=json.loads((D/'cases.json').read_bytes());out.mkdir();native=Native(out/'native')
conditions=copy.deepcopy(s['conditions'])
bridge=Bridge(s['config'],checker=native.checker,evaluator=native.evaluator,conditions=lambda:copy.deepcopy(conditions))
packet=lambda name:edit.canonical(s['packets'][name])
if stage=='cut':
 armed=[False];original=sqlite3.connect
 class CutConnection(sqlite3.Connection):
  def execute(self,sql,*args,**kwargs):
   value=super().execute(sql,*args,**kwargs)
   if sql.startswith('UPDATE image SET') and armed[0]:os._exit(88)
   return value
 def connect(*args,**kwargs):kwargs['factory']=CutConnection;return original(*args,**kwargs)
 sqlite3.connect=connect
 bridge.create(db)
 for step in s['steps']:
  name=step['packet']
  if name=='E':
   before=storage.read(db);(out/'before-E.image').write_bytes(before['image'])
   assert before['generation']==4
   armed[0]=True
  conditions['observe']=name!='E'
  assert bridge.call(db,'submit',packet(name))==step['answer']
  row=storage.read(db);image=json.loads(row['image'])
  assert row['generation']==step['generation'] and image['revision']==step['revision'] and image['state']['quantity']==step['quantity']
 raise AssertionError('pre-COMMIT interruption was not reached')

before=storage.read(db);initial=json.loads(before['image'])
conditions.update(tick=2,observe=True,submit=False,write=False)
if stage=='retry':
 assert before['generation']==4 and initial['revision']==9 and initial['state']['quantity']==0 and initial['mutations']==2
 assert bridge.call(db,'observe',packet('E'))=={'status':'Unknown'}
 assert bridge.call(db,'observe',packet('D'))==s['receipts']['D']
 assert bridge.call(db,'submit',packet('E'))=={'status':'AccessDenied'}
 assert storage.read(db)==before and native.apps==0
 conditions.update(submit=True,write=True,tick=3)
 assert bridge.call(db,'submit',packet('E'))==s['receipts']['E']
 assert native.apps==1
 committed=storage.read(db)
 assert bridge.call(db,'submit',packet('E'))==s['receipts']['E']
 assert storage.read(db)==committed and native.apps==1
else:
 assert before['generation']==5 and initial['revision']==10 and initial['state']['quantity']==7 and initial['mutations']==3
 conditions.update(tick=3)
 for name in ('E','A'):assert bridge.call(db,'observe',packet(name))==s['receipts'][name]
 assert storage.read(db)==before and native.apps==0
after=storage.read(db);image=json.loads(after['image'])
assert after['generation']==5 and image['revision']==10 and image['state']['quantity']==7 and image['mutations']==3
result={'stage':stage,'status':'PASSED','initial_digest':before['digest'],'final_digest':after['digest'],
 'G':5,'R':10,'quantity':7,'mutations':3,'application_evaluations':native.apps,'typed_calls':len(native.calls)}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
