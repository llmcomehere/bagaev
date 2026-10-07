from pathlib import Path
import copy,json,os,sqlite3,sys
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'src'))
from bagaev_outcome_durable_programmes import DurableProgrammes
from persistence_host import Native,explicit
db,fixture,output=sys.argv[1:];f=json.loads(Path(fixture).read_bytes());assert f['point'] in ('before','after') and f['operation'] in ('start','admit')
explicit(f['executables']);n=Native(output);original=sqlite3.connect
class CrashConnection(sqlite3.Connection):
 dirty=False
 def execute(self,sql,*args,**kwargs):
  if sql=='COMMIT' and self.dirty and f['point']=='before':os._exit(86)
  result=super().execute(sql,*args,**kwargs)
  if sql.startswith('UPDATE image SET'):self.dirty=True
  if sql=='COMMIT' and self.dirty and f['point']=='after':os._exit(87)
  return result
def connect(*args,**kwargs):kwargs['factory']=CrashConnection;return original(*args,**kwargs)
sqlite3.connect=connect
def qualified(p,source):return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
m=DurableProgrammes(f['config'],bootstrap=f['bootstrap'],checker=n.checker,evaluator=n.evaluator,conditions=lambda:copy.deepcopy(f['conditions']),authority=lambda:True,qualifier=qualified)
if f['operation']=='start':m.start(Path(db),'new')
else:m.admit(Path(db),'M1',f['proposal'])
raise AssertionError('commit cut not reached')
