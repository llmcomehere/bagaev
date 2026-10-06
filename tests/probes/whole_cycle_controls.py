"""Finite negative controls for the owned simulation, not production/security probes."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('whole_cycle_owned',HERE/'whole_cycle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure()
suite=json.loads((m.D/'cases.json').read_text());cases={c['id']:c for c in suite['cases']};ROOT=m.R
class StaleBeforeReplay(m.Receiver):
 def submit(self,e):
  k=self.keycheck(e)
  if k in self.ledger and self.state['revision']!=e['intent']['expected_revision']:
   self.extra['target_hit']=self.extra.get('target_hit',0)+1;self.last={'kind':'Refused','reason':'RevisionMismatch','revision':self.state['revision']};return
  super().submit(e)
class UnboundCancellation(m.Receiver):
 def execute(self,e):
  if e['command']=='Cancel' and self.keycheck(e) not in self.ledger:
   self.extra['target_hit']=self.extra.get('target_hit',0)+1;self.observe_result({'kind':'Cancelled','key':e['key'],'intent':e['intent'],'revision':self.state['revision']},e['key'],terminal=True);return
  super().execute(e)
class LeakyObservation(m.Receiver):
 def execute(self,e):
  if e['command']=='Observe' and e['permissions']['observe'] is False:
   self.extra['target_hit']=self.extra.get('target_hit',0)+1;e=copy.deepcopy(e);e['permissions']['observe']=True
  super().execute(e)
class CorruptAdapter(m.Engine):
 def transform(self,*args):
  value=super().transform(*args);value['manual']=[];return value
rows=[]
def run(label,case,receiver=m.Receiver,engine=m.Engine):
 m.R=ROOT/label;m.R.mkdir(exist_ok=True);eng=engine();r=receiver(suite['profile'],eng);r.current_case=case['id']
 for e in case['events']:r.execute(e)
 actual=r.projection();diff=[k for k,v in case['expected'].items() if m.encoded(actual.get(k))!=m.encoded(v)]
 return r,eng,actual,diff
for label,cid,cls in [('stale-before-replay','WC03',StaleBeforeReplay),('unbound-cancellation','WC06',UnboundCancellation),('leaky-observation','WC04',LeakyObservation)]:
 original,eng,actual,diff=run(label+'-original',cases[cid]);m.need(not diff,'control positive setup')
 wrong,eng2,actual2,diff2=run(label+'-mutant',cases[cid],cls);m.need(diff2 and actual2.get('target_hit')==1,'mutant witness not reached');rows.append({'id':label,'case':cid,'positive_matched':True,'detection':'normal-complete-projection-mismatch','target_hit':actual2['target_hit'],'differing_observables':diff2,'mutant_projection':actual2,'reference_calls':eng2.calls})
# Corrupt a correctly returned pure value at the adapter boundary: the state receiver
# must refuse before mutation. This is guard detection, not a full-output mismatch.
case=cases['WC02'];r,eng,_,diff=run('corrupt-adapter-original',case);m.need(not diff,'adapter positive setup')
m.R=ROOT/'corrupt-adapter-mutant';m.R.mkdir(exist_ok=True);bad=CorruptAdapter();receiver=m.Receiver(suite['profile'],bad);before=copy.deepcopy(receiver.state)
try:
 for e in case['events']:receiver.execute(e)
except ValueError as exc:
 m.need(str(exc)=='component frame','wrong guard');m.need(receiver.state==before and not receiver.ledger and receiver.mutations==0 and len(bad.calls)==1,'frame refusal after mutation or before pure call');rows.append({'id':'corrupt-adapter','case':'WC02','positive_matched':True,'detection':'component-frame-guard-before-state-mutation','reference_calls':bad.calls,'state_unchanged':True})
else:raise ValueError('corrupt adapter accepted')
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'controls':rows,'detected':len(rows),'source_sha256':hashlib.sha256((HERE/'whole_cycle.py').read_bytes()).hexdigest(),'scope':'Three normal projection mismatches and one frame-guard refusal, all reached after valid positive setups; synthetic simulation only'}
(ROOT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'detected':len(rows),'normal_mismatches':3,'guard_refusals':1}))
