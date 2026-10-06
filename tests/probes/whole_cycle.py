"""Owned finite simulation of the proposed whole-cycle bridge, not a durable receiver.
Calls the existing reviewed typed-record/10 reference serially with synthetic data.
No network, credentials, arbitrary command dispatch, native kernel or production rights.
"""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,re,subprocess
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/whole-cycle';R=None;REFERENCE=None;REFERENCE_SHA=None
def clone(x):return copy.deepcopy(x)
def encoded(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def identity(x):return encoded(x).decode()
def need(b,message):
 if not b:raise ValueError(message)
class Engine:
 def __init__(self):
  self.count=0;self.calls=[];self.sources={s:json.loads((D/'pure'/f'{s}.json').read_text()) for s in ('S1','S2')};self.binary=REFERENCE
  need(self.binary is not None and hashlib.sha256(self.binary.read_bytes()).hexdigest()==REFERENCE_SHA,'reference identity mismatch')
 def invoke(self,program,args,label):
  self.count+=1;name=f'{self.count:03d}';f=R/(name+'.input.json');b=encoded({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':args});need(len(b)<=1048576,'input bound');f.write_bytes(b)
  q=subprocess.run([str(self.binary),'run','--input',str(f)],capture_output=True,timeout=20)
  (R/(name+'.stdout')).write_bytes(q.stdout);(R/(name+'.stderr')).write_bytes(q.stderr)
  need(q.returncode==0 and not q.stderr and len(q.stdout)<=1048576,'reference environment failure');need(f.read_bytes()==b,'input changed')
  out=json.loads(q.stdout);need(set(out)=={'schema','status','reason','location','value_type','value','work'} and out['schema']=='bagaev-typed-record-result/10','result frame');need(type(out['work']) is int and 0<=out['work']<=65536,'work field')
  self.calls.append({'n':self.count,'label':label,'input_sha256':hashlib.sha256(b).hexdigest(),'output_sha256':hashlib.sha256(q.stdout).hexdigest(),'status':out['status']});return out
 def transform(self,source,entry,tags,label):
  original=clone(entry);wire={'id':{'value':entry['id']},'manual':clone(entry['manual']),'indexed':clone(entry['indexed'])}
  out=self.invoke(self.sources[source],[wire,tags],label)
  need(out['status']=='success' and out['reason'] is None and out['location'] is None and out['value_type']=='Record:Entry','pure evaluation refused')
  v=out['value'];need(type(v) is dict and set(v)=={'id','manual','indexed'} and type(v['id']) is dict and set(v['id'])=={'value'},'entry shape')
  need(entry==original,'input mutation');return {'id':v['id']['value'],'manual':clone(v['manual']),'indexed':clone(v['indexed'])}
 def check_candidate(self,source):
  for c in json.loads((D/'pure/cases.json').read_text())['cases']:
   out=self.invoke(self.sources[source],[c['entry'],c['tags']],'admission-pure-'+source+'-'+c['id']);need(encoded(out)==encoded(c['expected'][source]),'candidate pure expectation')
 def scalar(self,body,label):
  p={'schema':'bagaev-typed-record/10','records':{},'lists':{},'variants':{},'entry':'main','functions':{'main':{'params':[],'result':'Int64','body':body}}};return self.invoke(p,[],label)
class Receiver:
 def __init__(self,profile,engine):
  self.state=clone(profile['initial_state']);self.engine=engine;self.ledger={};self.default='S1';self.runs={'original':'S1'};self.last=None;self.observations=[];self.knowledge={};self.current=None;self.mutations=0;self.audit=0;self.calls=[];self.checkpoint=None;self.resumed=None;self.horizon=profile['reconciliation_horizon_tick'];self.last_tick=0;self.extra={};self.current_case=''
 def observe_result(self,value,key=None,terminal=None):
  self.last=clone(value);self.observations.append(clone(value))
  if key is not None:self.current=identity(key)
  if terminal is not None:self.knowledge[self.current]='TerminalObserved'
 def keycheck(self,e):
  key=e['key'];need(set(key)=={'resource','domain','id'},'key shape');need(key['resource']==self.state['resource'],'resource incarnation');return identity(key)
 def permission(self,e,k):return type(e.get('permissions',{}).get(k)) is bool and e['permissions'][k]
 def read_terminal(self,e,row):
  if not self.permission(e,'observe'):self.observe_result('AccessDenied',e['key']);return
  if row['intent']!=e['intent']:self.observe_result('IntentConflict',e['key']);return
  self.observe_result(row['receipt'],e['key'],terminal=True)
 def bind(self,e,receipt):
  k=self.keycheck(e);need(k not in self.ledger,'terminal overwrite');self.ledger[k]={'intent':clone(e['intent']),'receipt':clone(receipt)};self.audit+=1
 def submit(self,e):
  k=self.keycheck(e);self.current=k
  if not self.permission(e,'submit'):self.observe_result('AccessDenied',e['key']);return
  if k in self.ledger:self.read_terminal(e,self.ledger[k]);return
  if not self.permission(e,'write'):self.observe_result('AccessDenied',e['key']);return
  i=e['intent'];source={'reindex/v1':'S1','reindex/v2':'S2'}[i['behaviour']]
  if e.get('run_id') is not None:need(self.runs[e['run_id']]==source,'run/behaviour mismatch')
  old=clone(self.state);reason=None
  if e['tick']>i['deadline_tick']:reason='DeadlineExpired'
  elif self.state['write_epoch']!=i['write_epoch']:reason='EpochMismatch'
  elif self.state['revision']!=i['expected_revision']:reason='RevisionMismatch'
  matches=[j for j,v in enumerate(self.state['entries']) if v['id']==i['entry']]
  if reason is None and len(matches)!=1:reason='MissingEntry'
  if reason is not None:
   receipt={'kind':'Refused','reason':reason,'revision':self.state['revision']};self.bind(e,receipt);self.read_terminal(e,self.ledger[k]);return
  index=matches[0];entry=self.state['entries'][index];candidate=self.engine.transform(source,entry,i['tags'],self.current_case+'-operation-'+source);self.calls.append(source)
  # A source result is not a write receipt. Independent component frame before commit.
  need(candidate['id']==entry['id'] and candidate['manual']==entry['manual'] and candidate['indexed']==sorted(set(i['tags'])),'component frame')
  self.state['entries'][index]=candidate;self.state['revision']+=1;self.mutations+=1
  need(all(v==self.state['entries'][j] for j,v in enumerate(old['entries']) if j!=index),'foreign entry changed')
  receipt={'kind':'Applied','key':clone(e['key']),'intent':clone(i),'revision':self.state['revision'],'entry':clone(candidate)};self.bind(e,receipt)
  if e.get('reply')=='drop':self.knowledge[k]='OutcomeUnknown';self.last=None
  else:self.read_terminal(e,self.ledger[k])
 def execute(self,e):
  command=e['command']
  if 'tick' in e:need(type(e['tick']) is int and e['tick']>=self.last_tick,'clock order');self.last_tick=e['tick']
  if command=='Submit':self.submit(e)
  elif command=='Observe':
   k=self.keycheck(e);self.current=k
   if not self.permission(e,'observe'):self.observe_result('AccessDenied',e['key'])
   elif k in self.ledger:self.read_terminal(e,self.ledger[k])
   else:self.observe_result('ReconciliationUnavailableExpired' if e['tick']>self.horizon else 'NoRecordedOutcome',e['key'])
  elif command=='Cancel':
   k=self.keycheck(e);self.current=k
   if not self.permission(e,'cancel'):self.observe_result('AccessDenied',e['key']);return
   if k in self.ledger:
    row=self.ledger[k]
    if not self.permission(e,'observe'):self.observe_result('AccessDenied',e['key'])
    elif row['intent']!=e['intent']:self.observe_result('IntentConflict',e['key'])
    elif row['receipt']['kind']=='Applied':self.observe_result({'kind':'AlreadyApplied','receipt':row['receipt']},e['key'],terminal=True)
    else:self.read_terminal(e,row)
   else:
    receipt={'kind':'Cancelled','key':clone(e['key']),'intent':clone(e['intent']),'revision':self.state['revision']};self.bind(e,receipt);self.read_terminal(e,self.ledger[k])
  elif command=='ObserverTimeout':
   if self.knowledge.get(self.current)!='TerminalObserved':self.knowledge[self.current]='OutcomeUnknown';self.observe_result('OutcomeUnknown')
  elif command=='FenceWrites':
   need(e['control_authorized'] is True and self.state['write_epoch']==e['expected_epoch'] and e['new_epoch']>e['expected_epoch'],'fence guard');self.state['write_epoch']=e['new_epoch'];self.last='Fenced'
  elif command=='AdmitProgramme':
   if e['admission_authorized'] is not True:self.last='AccessDenied';return
   if e['base']!=self.default:self.last='AdmissionStale';return
   if e['requires_migration']:self.last='UnsupportedMigration';return
   need(e['obligation_set']=='catalogue-contract/v1','policy mismatch')
   if e['evidence_set']=='missing-actual-entry-consumer':self.last='AdmissionUnresolved';self.extra['missing_obligation']='actual-entry-consumer';return
   need(e['evidence_set']=='complete-admissible-fixture','unsupported evidence fixture')
   self.engine.check_candidate(e['candidate']);self.default=e['candidate'];self.last='SimulatedAdmissionAccepted'
  elif command=='StartRun':
   need(e['run_id'] not in self.runs,'run overwrite');self.runs[e['run_id']]=self.default;self.last='RunStarted'
  elif command=='SaveContinuation':
   need(e['programme']=='S1','unsupported continuation');self.checkpoint=encoded({'programme':e['programme'],'unresolved':clone(e['unresolved'])})
  elif command=='Resume':
   need(self.checkpoint is not None,'missing continuation');saved=json.loads(self.checkpoint);need(saved['programme']==e['programme'],'continuation revision');self.resumed=saved
  elif command=='RemoveDiagnosticAudit':self.audit=0
  elif command=='AssertFixtureAuditRows':need(self.audit==e['expected'],'vacuous diagnostic fixture')
  elif command=='RetireTerminalWitness':
   need(e['retention_authorized'] is True and e['tick']>self.horizon and e['live_consumers']==0,'retirement guard');self.ledger={}
  elif command=='ResolveDisplayName':self.extra['resolved_resource']=e['resolved_resource']
  elif command=='AttemptReacquire':self.last='ResourceIncarnationMismatch' if e['requested_resource']!=e['available_resource'] else 'Reacquired';self.extra.update(g2_mutations=0,automatic_rebind=False)
  elif command=='PureCall':
   if e['function']=='reindex_entry/v1':self.extra['result']=self.engine.transform('S1',e['entry'],e['tags'],self.current_case+'-pure');self.extra['input_after']=clone(e['entry'])
   elif e['function']=='add_int64':
    out=self.engine.scalar(['add',*([ 'int',v] for v in e['arguments'])],self.current_case+'-scalar');need(out['status']=='integer-overflow' and out['reason']=='RR_OVERFLOW','wrong overflow outcome');self.extra.update(error='Int64Overflow',success_value_present=False)
   else:raise ValueError('unsupported pure function')
  elif command=='PureConditional':
   out=self.engine.scalar(['if',['bool',e['condition']],['int',e['then_value']],['add',*(['int',v] for v in e['else_expression']['add_int64'])]],self.current_case+'-lazy');need(out['status']=='success','lazy outcome');self.extra.update(result=out['value'],else_evaluated=False)
  else:raise ValueError('unsupported simulation command')
 def projection(self):
  keyA=identity({'resource':'catalogue/g1','domain':'owner','id':'A'});keyB=identity({'resource':'catalogue/g1','domain':'owner','id':'B'});a=self.ledger.get(keyA);b=self.ledger.get(keyB)
  return {'last_observation':clone(self.last),'observations':clone(self.observations),'catalogue_revision':self.state['revision'],'entry':clone(self.state['entries'][0]),'ledger_rows':len(self.ledger),'data_mutations':self.mutations,'write_epoch':self.state['write_epoch'],'audit_rows':self.audit,'receiver_terminal':None if a is None else clone(a['receipt']),'observer_outcome':self.knowledge.get(keyA,'OutcomeUnknown'),'private_receipt_disclosed':False if self.last=='AccessDenied' else None,'original_intent_deadline_tick':None if a is None else a['intent']['deadline_tick'],'new_run_default':self.default,'original_run_programme':self.runs['original'],'new_run_programme':self.runs.get('new-run'),'resumed_unresolved_programme':None if self.resumed is None else self.resumed['programme'],'receipt_behaviour':None if a is None else a['intent']['behaviour'],'A_terminal_exists':a is not None,'B_terminal_kind':None if b is None else b['receipt']['kind'],'automatic_fresh_operation':False,'source_call_order':self.calls,**clone(self.extra)}
def verify_inputs():
 frozen=json.loads((D/'inputs.json').read_text())
 for n,h in frozen['sha256'].items():need(hashlib.sha256((D/n).read_bytes()).hexdigest()==h,'frozen input changed: '+n)
 return frozen
def main():
 frozen=verify_inputs()
 suite=json.loads((D/'cases.json').read_text());engine=Engine();rows=[]
 for c in suite['cases']:
  receiver=Receiver(suite['profile'],engine);receiver.current_case=c['id']
  for event in c['events']:receiver.execute(event)
  actual=receiver.projection();differences={k:{'expected':v,'actual':actual.get(k)} for k,v in c['expected'].items() if encoded(actual.get(k))!=encoded(v)}
  rows.append({'id':c['id'],'matched':not differences,'differences':differences,'actual':actual})
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','scope':'Finite in-memory receiver/observer simulation with actual typed-record/10 pure reference calls. No native kernel, real durable receiver, authentication or production admission.','requested':len(rows),'matched':sum(r['matched'] for r in rows),'rows':rows,'reference_calls':engine.calls,'timing_or_model_measurements':False,'frozen':frozen,'simulator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(R/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'matched':result['matched'],'requested':len(rows),'reference_calls':engine.count,'differences':[{'id':r['id'],'differences':r['differences']} for r in rows if not r['matched']]}));need(result['status']=='PASSED','simulation mismatch')
def configure(args=None):
 global R,REFERENCE,REFERENCE_SHA
 parser=argparse.ArgumentParser(description='Finite synthetic whole-cycle simulation; requires a separately reviewed/admitted reference executable and bounded profile.')
 parser.add_argument('--reference',required=True,type=Path)
 parser.add_argument('--reference-sha256',required=True)
 parser.add_argument('--output',required=True,type=Path)
 ns=parser.parse_args(args)
 need(ns.reference.is_absolute() and ns.reference.is_file() and not ns.reference.is_symlink(),'reference must be an absolute regular file')
 need(re.fullmatch('[0-9a-f]{64}',ns.reference_sha256) is not None,'reference SHA256')
 need(hashlib.sha256(ns.reference.read_bytes()).hexdigest()==ns.reference_sha256,'reference identity mismatch')
 need(ns.output.is_absolute() and ns.output.parent.is_dir() and not ns.output.exists(),'output must be a new absolute directory with existing parent')
 ns.output.mkdir();R=ns.output;REFERENCE=ns.reference;REFERENCE_SHA=ns.reference_sha256
 return ns
if __name__=='__main__':
 configure();main()
