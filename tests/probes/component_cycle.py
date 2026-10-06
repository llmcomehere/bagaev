"""Owned bounded component-source composition experiment. No production effects."""
import argparse, datetime, hashlib, json, re, subprocess
from pathlib import Path
import whole_cycle as b
P=b.P; D=P/'examples/probes/component-source'
READER=None; READER_SHA=None
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read_checked(source,policy,label):
 before=source.read_bytes();pb=policy.read_bytes()
 q=subprocess.run([str(READER),'policy',str(source),str(policy)],capture_output=True,timeout=10)
 target=b.R/(label+'.check.stdout');b.need(not target.exists(),'reader evidence collision');target.write_bytes(q.stdout)
 b.need(q.returncode==0 and not q.stderr and source.read_bytes()==before and policy.read_bytes()==pb,'component reader environment')
 out=json.loads(q.stdout)
 b.need(out['status']=='checked' and out['policy_compatible'] is True and out['execution_admission'] is False,'component policy refused')
 return out
class ComponentEngine(b.Engine):
 def __init__(self,policy=None):
  super().__init__();self.bindings=[];self.fault=None;self.checked={};self.frozen_sources={}
  b.need(hashlib.sha256(READER.read_bytes()).hexdigest()==READER_SHA,'reader identity')
  self.contract=json.loads((D/'CONTRACT.json').read_text());policy=policy or D/'policy.json'
  for alias in ('S1','S2'):
   f=D/(alias+'.json');raw=f.read_bytes();src=json.loads(raw)
   checked=read_checked(f,policy,alias+('-wrong-policy' if policy.name=='wrong-policy.json' else ''))
   pins=self.contract['pins'][alias]
   b.need(digest(src)==pins['component_sha256']==checked['source_sha256'],'source pin')
   b.need(digest(src['program'])==pins['program_sha256']==checked['program_sha256'],'core pin')
   b.need(digest(json.loads(policy.read_bytes()))==checked['policy_sha256']==self.contract['policy_sha256'],'policy pin')
   self.frozen_sources[alias]=raw;self.checked[alias]=b.encoded(checked)
 def transition(self,source,entry,intent,label,operation_key=None):
  src=json.loads(self.frozen_sources[source]);checked=json.loads(self.checked[source]);program=src['program']
  original=b.clone(entry);wire={'id':{'value':entry['id']},'indexed':b.clone(entry['indexed']),'manual':b.clone(entry['manual'])}
  request={'id':{'value':intent['entry']},'base':{'value':intent['expected_revision']},'tags':b.clone(intent['tags'])}
  ids=checked['identity_binding'];revision=checked['revision_binding']
  b.need(wire[ids['state']]==request[ids['request']],'declared identity binding')
  b.need(type(request[revision]['value']) is int and request[revision]['value']==intent['expected_revision'],'declared revision binding')
  out=self.invoke(program,[wire,request],label+'-transition')
  b.need(out['status']=='success' and out['value_type']=='Record:'+checked['state_type'],'pure evaluation refused')
  value=b.clone(out['value'])
  if self.fault=='manual':value['manual']=['corrupted']
  if self.fault=='indexed':value['indexed']=17
  validator={'schema':'bagaev-typed-record/10','records':b.clone(program['records']),'lists':{},'variants':{},'entry':'main','functions':{'main':{'params':[['value',checked['state_type']]],'result':checked['state_type'],'body':['arg','value']}}}
  validated=self.invoke(validator,[value],label+'-result-type')
  b.need(validated['status']=='success' and validated['value_type']=='Record:'+checked['state_type'] and validated['value']==value,'declared result type')
  b.need(all(value[k]==wire[k] for k in checked['preserve_fields']),'declared component frame')
  b.need(entry==original,'input mutation')
  self.bindings.append({'label':label,'operation_key':b.clone(operation_key),'source':source,'component_sha256':checked['source_sha256'],'program_sha256':checked['program_sha256'],'state_sha256':digest(wire),'request_sha256':digest(request),'result_sha256':digest(value),'preserve_fields':checked['preserve_fields']})
  return {'id':value['id']['value'],'indexed':b.clone(value['indexed']),'manual':b.clone(value['manual'])}
 def transform(self,source,entry,tags,label):return self.transition(source,entry,{'entry':entry['id'],'expected_revision':0,'tags':tags},label)
 def check_candidate(self,source):
  for c in json.loads((b.D/'pure/cases.json').read_text())['cases']:
   entry=b.clone(c['entry']);entry['id']=entry['id']['value']
   actual=self.transform(source,entry,c['tags'],'admission-'+source+'-'+c['id'])
   expected=b.clone(c['value']);expected['id']=expected['id']['value']
   b.need(actual==expected,'candidate value expectation')
def main():
 verify_component_inputs()
 b.verify_inputs();contract=json.loads((D/'CONTRACT.json').read_text())
 for name,key in [('cases.json','whole_cycle_cases_sha256'),('pure/cases.json','pure_value_expectations_sha256')]:
  b.need(hashlib.sha256((b.D/name).read_bytes()).hexdigest()==contract['immutable_expectation_files'][key],'expectation pin')
 suite=json.loads((b.D/'cases.json').read_text());engine=ComponentEngine();rows=[]
 for case in suite['cases']:
  receiver=b.Receiver(suite['profile'],engine);receiver.current_case=case['id'];start=len(engine.bindings)
  for event in case['events']:receiver.execute(event)
  actual=receiver.projection();diff={k:{'expected':v,'actual':actual.get(k)} for k,v in case['expected'].items() if b.encoded(v)!=b.encoded(actual.get(k))}
  bindings=engine.bindings[start:]
  if case['id']=='WC17':
   effects=[x for x in bindings if x['operation_key'] is not None]
   b.need([x['source'] for x in effects]==['S1','S2'] and [x['operation_key']['id'] for x in effects]==['A','B'],'WC17 operation association/replay')
   for x in effects:b.need(x['component_sha256']==contract['pins'][x['source']]['component_sha256'],'WC17 source association')
  rows.append({'id':case['id'],'matched':not diff,'differences':diff,'bindings':bindings,'actual':actual})
 positive_calls=engine.count
 guards=[];first=next(c for c in suite['cases'] if c['id']=='WC17');event=next(e for e in first['events'] if e['command']=='Submit')
 for fault,required in [('manual','declared component frame'),('indexed','declared result type')]:
  engine.fault=fault;r=b.Receiver(suite['profile'],engine);before=b.clone(r.state);error=None
  try:r.execute(event)
  except ValueError as e:error=str(e)
  b.need(error==required and r.state==before and not r.ledger and r.mutations==0,'guard failed '+fault)
  guards.append({'fault':fault,'observed':error,'committed':False})
 engine.fault=None
 policy=json.loads((D/'policy.json').read_text());policy['records']['OtherId']=policy['records'].pop('EntryId');policy['records']['Entry']['id']='OtherId';policy['records']['ReindexRequest']['id']='OtherId'
 f=b.R/'wrong-policy.json';f.write_bytes(b.encoded(policy));error=None
 try:ComponentEngine(f)
 except ValueError as e:error=str(e)
 b.need(error=='component policy refused','policy guard failed');guards.append({'fault':'wrong receiver nominal type','observed':error,'pure_invoked':False})
 result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','matched':sum(x['matched'] for x in rows),'requested':len(rows),'rows':rows,'guards':guards,'reference_calls':engine.calls,'bindings':engine.bindings,'scope':'Actual checked component source and typed pure calls; simulated receiver, authority, admission and recovery. No timing or production durability claim.','reference_sha256':b.REFERENCE_SHA,'reader_sha256':READER_SHA}
 result['positive_reference_calls']=positive_calls;result['guard_reference_calls']=engine.count-positive_calls
 (b.R/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'matched':result['matched'],'guards':len(guards),'positive_calls':positive_calls,'guard_calls':engine.count-positive_calls}));b.need(result['status']=='PASSED','projection mismatch')
def verify_component_inputs():
 frozen=json.loads((D/'inputs.json').read_text())
 for name,sha in frozen['sha256'].items():b.need(hashlib.sha256((D/name).read_bytes()).hexdigest()==sha,'component frozen input '+name)
 return frozen
def configure():
 global READER,READER_SHA
 parser=argparse.ArgumentParser(description='Checked component source in finite whole-cycle simulation. Requires separately reviewed binaries and bounded execution.')
 parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True)
 ns,remaining=parser.parse_known_args()
 b.need(ns.reader.is_absolute() and ns.reader.is_file() and not ns.reader.is_symlink(),'reader must be absolute regular file')
 b.need(re.fullmatch('[0-9a-f]{64}',ns.reader_sha256) is not None and hashlib.sha256(ns.reader.read_bytes()).hexdigest()==ns.reader_sha256,'reader identity')
 READER=ns.reader;READER_SHA=ns.reader_sha256;b.configure(remaining)
if __name__=='__main__':configure();main()
