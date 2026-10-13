"""Own serial typed reconstruction qualification, finite twelve-case contract."""
from pathlib import Path
import copy, datetime, hashlib, json, sys
from unittest.mock import patch
S=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(S/'src'),str(S/'tests/probes')]
import bagaev_owner_image_store as storage
import bagaev_outcome_image as image_codec
import bagaev_outcome_programme_image as envelope
import bagaev_outcome_retained_view as view
from bagaev_outcome_durable_programmes import DurableProgrammes
from persistence_host import Native,select
from outcome_host import configure
a=configure(reference=True);select(a);R=a.output;R.mkdir()
D=S/'examples/probes/outcome-persistence'
sha=lambda b:hashlib.sha256(b).hexdigest()
for name,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():
 assert sha((D/name).read_bytes())==h
s=json.loads((D/'bridge.json').read_bytes());cfg=s['config']
S1=s['packets']['A']['source'];S2=s['packets']['B']['source']
proposal={'expected':{'generation':0,'source':S1},'target':S2,
 'policy':image_codec.pin(cfg['policy']),'assertions':'a'*64,'producer':'b'*64,'qualification':'c'*64}
def qualifier(p,source):
 return {'decision':'accepted','binding':{k:p[k] for k in ('target','policy','assertions','producer','qualification')}}
frozen=json.loads((D/'retained-view-final-read.json').read_bytes())
assert frozen['schema']=='retained-view-final-read/1'
rows=[]
for kind in ('retained','absent','conflicting'):
 for cut in ('unchanged','changed','aba','denied'):
  folder=R/(kind+'-'+cut);folder.mkdir();db=folder/'owner.sqlite'
  n=Native(folder/'typed');conditions=copy.deepcopy(s['conditions'])
  m=DurableProgrammes(cfg,bootstrap=S1,checker=n.checker,evaluator=n.evaluator,
   conditions=lambda:copy.deepcopy(conditions),authority=lambda:True,qualifier=qualifier)
  m.create(db);m.start(db,'old')
  receipt=m.call(db,'old','submit',envelope.encode(s['packets']['A']))
  m.admit(db,'M1',proposal);m.start(db,'new');conditions['tick']=2
  m.call(db,'new','submit',envelope.encode(s['packets']['B']))
  before=storage.read(db);assert before['generation']==5 and n.apps==2
  packet=copy.deepcopy(s['packets']['A'])
  if kind=='absent':packet['key']['id']='never-observed'
  if kind=='conflicting':packet['request']['quantity']=0
  observed=[0];live=[0];calls=len(n.calls);apps=n.apps
  def observer():
   observed[0]+=1
   if observed[0]==2 and cut!='unchanged':
    other=storage.compare_and_swap(db,before['generation'],before['digest'],b'{"changed":true}')
    if cut=='aba':storage.compare_and_swap(db,other['generation'],other['digest'],before['image'])
   return not(cut=='denied' and observed[0]==2)
  def blocked():
   live[0]+=1;raise AssertionError('live conditions invoked')
  expected=frozen['answers'][kind][cut]
  answer=None;error_code=None
  with patch.object(view,'_no_live_conditions',blocked):
   try:
    answer=view.observe_retained(db,cfg,bootstrap=S1,run_id='old',packet=envelope.encode(packet),
     checker=n.checker,evaluator=n.evaluator,observer=observer)
   except envelope.ProgrammeError as error:error_code=error.code
  if cut in ('changed','aba'):
   assert answer is None and error_code==expected,(kind,cut,answer,error_code)
   actual=error_code
  else:
   assert error_code is None,(kind,cut,error_code)
   required=receipt if kind=='retained' and cut=='unchanged' else {'status':expected}
   assert answer==required,(kind,cut,answer,required)
   actual=answer.get('status',answer.get('kind'))
  assert actual==expected,(kind,cut,actual,expected)
  after=storage.read(db);generation=frozen['generations'][cut]
  assert after['generation']==generation
  assert after['image']==(before['image'] if cut in ('unchanged','aba') else b'{"changed":true}')
  assert observed==[frozen['observer_calls']] and live==[frozen['live_condition_calls']]
  assert n.apps-apps==frozen['read_application_evaluations'] and apps==2 and len(n.calls)>calls
  if kind=='retained' and cut=='unchanged':
   assert answer==receipt
   answer['revision']=999
   assert receipt['revision']!=999 and storage.read(db)==before
  rows.append({'id':kind+'-'+cut,'actual':actual,'expected':expected,'generation':generation,
   'setup_calls':calls,'read_calls':len(n.calls)-calls,'setup_apps':apps,'read_apps':n.apps-apps,
   'observer_calls':observed[0],'live_calls':live[0]})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED','rows':rows,
 'expectations_sha256':sha((D/'retained-view-final-read.json').read_bytes()),
 'reader_sha256':a.reader_sha256,'reference_sha256':a.reference_sha256,
 'scope':'Actual typed original-envelope reconstruction and serial real SQLite final-callback cuts. No production concurrency, authenticity or new clock activation.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
