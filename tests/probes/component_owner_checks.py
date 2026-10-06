"""Actual reviewed reader/reference with frozen receiver oracle, no network."""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-owner';T=P
sys.path.insert(0,str(T/'src'));import bagaev_component_edit as edit
import bagaev_component_owner as owner
sha=lambda b:hashlib.sha256(b).hexdigest()
for n,h in json.loads((D/'inputs.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
suite=json.loads((D/'receiver-cases.json').read_bytes())
parser=argparse.ArgumentParser(description='Serial owned-record simulation with separately reviewed host binaries.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--reference',required=True,type=Path);parser.add_argument('--reference-sha256',required=True);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();reader=args.reader;reference=args.reference;R=args.output
for binary,pin in [(reader,args.reader_sha256),(reference,args.reference_sha256)]:
 assert binary.is_absolute() and binary.is_file() and not binary.is_symlink() and re.fullmatch('[0-9a-f]{64}',pin) and sha(binary.read_bytes())==pin
assert R.is_absolute() and R.parent.is_dir()
assert not R.exists();R.mkdir();calls=[];rows=[];control={};conditions={};application=0
suite['cases']+=json.loads((D/'extra-cases.json').read_bytes())['cases']
clone=copy.deepcopy
def invoke(binary,argv,inputs):
 n=len(calls)+1;paths=[]
 for name,data in inputs:
  p=R/f'{n:03d}.{name}';p.write_bytes(data);paths.append(p)
 q=subprocess.run([str(binary),*argv,*map(str,paths)],capture_output=True,timeout=20);(R/f'{n:03d}.stdout').write_bytes(q.stdout);(R/f'{n:03d}.stderr').write_bytes(q.stderr)
 assert q.returncode==0 and not q.stderr and all(p.read_bytes()==data for p,(_,data) in zip(paths,inputs))
 calls.append({'binary':binary.name,'input_sha256':[sha(d) for _,d in inputs],'output_sha256':sha(q.stdout)});return json.loads(q.stdout)
def checker(source,policy):return invoke(reader,['policy'],[('source.json',source),('policy.json',policy)])
def evaluator(program,arguments):
 global application
 actual_app=program['functions'][program['entry']]['body'][0]!='arg'
 if actual_app:
  application+=1
  if control.get('evaluator_fault')=='unavailable':raise RuntimeError('controlled failure')
 wire=invoke(reference,['run','--input'],[('input.json',edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':arguments}))])
 if actual_app:
  conditions.update(control.get('during_evaluation',{}))
  if control.get('nested_submit') is not None:
   nested=control.pop('nested_submit');obj.submit(edit.canonical(nested))
  if control.get('evaluator_fault')=='preserved':wire['value']['note']='corrupt'
  if control.get('evaluator_fault')=='type':wire['value']['quantity']='bad'
 return wire
for case in suite['cases']:
 conditions=clone(suite['initial_conditions']);control={};application=0;d=case['domain'];start=len(calls)
 obj=owner.Owner(policy=suite['policies'][d],sources=[suite['sources'][d]],state=suite['initial'][d],revision=7,resource=d+'/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions));outputs=[]
 for action in case['actions']:
  conditions.update(action.get('conditions',{}));control=clone(action)
  try:result=getattr(obj,action['command'])(edit.canonical(action['packet']))
  except (owner.OwnerInputError,owner.OwnerEvaluationError) as e:result={'error':e.code}
  except owner.OwnerUnavailable:result={'error':'OwnerUnavailable'}
  if action.get('drop_reply'):result={'transport':'lost'}
  outputs.append(result)
 actual={'outputs':outputs,**obj.snapshot(),'application_evaluations':application};matched=edit.canonical(actual)==edit.canonical(case['expected']);rows.append({'id':case['id'],'matched':matched,'actual':actual,'expected':case['expected'],'reference_and_checker_calls':len(calls)-start})
# Separate capacity and detached-output guards over the actual source/reference.
def make_stock():
 global conditions,control,application
 conditions=clone(suite['initial_conditions']);control={};application=0
 return owner.Owner(policy=suite['policies']['stock'],sources=[suite['sources']['stock']],state=suite['initial']['stock'],revision=7,resource='stock/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions))
a=clone(next(c for c in suite['cases'] if c['id']=='REPLAY')['actions'][0]['packet']);obj=make_stock()
for i in range(64):
 p=clone(a);p['key']['id']='C'+str(i);r=obj.cancel(edit.canonical(p));assert r['kind']=='Cancelled'
assert obj.submit(edit.canonical(a))=={'status':'CapacityExceeded'} and obj.snapshot()['terminal_rows']==64 and application==0 and obj.snapshot()['mutations']==0
obj=make_stock();r=obj.submit(edit.canonical(a));r['state']['quantity']=999;r['intent']['request']['quantity']=999;snap=obj.snapshot();snap['state']['quantity']=999
r=obj.observe(edit.canonical(a));assert r['state']['quantity']==13 and r['intent']['request']['quantity']==13 and obj.snapshot()['state']['quantity']==13 and obj.snapshot()['mutations']==1
guards={'capacity':True,'detached_outputs':True}
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'guards':guards,'calls':calls,'scope':'Generic serial in-memory owned-record simulation over two actual source domains; no durable/authenticated/concurrent execution.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'matched':sum(r['matched'] for r in rows),'requested':len(rows),'calls':len(calls),'failures':[r for r in rows if not r['matched']]});assert result['status']=='PASSED'
