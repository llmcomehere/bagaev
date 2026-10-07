"""Frozen /2 owner cases with actual separately reviewed data/reference binaries."""
from pathlib import Path
import argparse,copy,json,hashlib,re,subprocess,sys,datetime
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-outcomes/owner'
sys.path.insert(0,str(T/'src'));import bagaev_component_owner as base;import bagaev_component_edit as edit
from bagaev_component_outcome_owner import OutcomeOwner
import bagaev_component_outcome_form as form2
sha=lambda b:hashlib.sha256(b).hexdigest();clone=copy.deepcopy
for n,h in json.loads((D/'inputs.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
parser=argparse.ArgumentParser(description='Explicit outcome profile with separately reviewed host executables.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path)
parser.add_argument('--reference',required=True,type=Path);parser.add_argument('--reference-sha256',required=True)
args=parser.parse_args();reader=args.reader;R=args.output
assert reader.is_absolute() and reader.is_file() and not reader.is_symlink() and re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
assert R.is_absolute() and R.parent.is_dir()
ref=args.reference;assert ref.is_absolute() and ref.is_file() and not ref.is_symlink() and re.fullmatch('[0-9a-f]{64}',args.reference_sha256) and sha(ref.read_bytes())==args.reference_sha256
assert not R.exists();R.mkdir();suite=json.loads((D/'cases.json').read_bytes());calls=[];rows=[];conditions={};control={};apps=0
F=D.parent/'form'
for n,h in json.loads((F/'inputs.json').read_bytes())['sha256'].items():assert sha((F/n).read_bytes())==h
decoded=form2.decode((F/'StockOutcome.bagaev').read_bytes());assert edit.canonical(decoded)==edit.canonical(suite['source']);suite['source']=decoded

def invoke(binary,args,inputs):
 n=len(calls)+1;paths=[]
 for name,data in inputs:
  p=R/f'{n:03d}.{name}';p.write_bytes(data);paths.append(p)
 q=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20);(R/f'{n:03d}.stdout').write_bytes(q.stdout);(R/f'{n:03d}.stderr').write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and all(p.read_bytes()==d for p,(_,d) in zip(paths,inputs));calls.append({'input_sha256':[sha(d) for _,d in inputs],'output_sha256':sha(q.stdout),'binary':binary.name});return json.loads(q.stdout)
def checker(source,policy):return invoke(reader,['policy'],[('source.json',source),('policy.json',policy)])
def evaluator(program,args):
 global apps
 wire=invoke(ref,['run','--input'],[('input.json',edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':args}))])
 if program['functions'][program['entry']]['body'][0]!='arg':
  apps+=1;conditions.update(control.get('during',{}))
  if control.get('nested') is not None:
   nested=control.pop('nested');obj.submit(edit.canonical(nested))
  fault=control.get('fault')
  if fault=='frame':wire['value']['value']['note']='corrupt'
  elif fault=='error-type':wire['value']['value']['reason']=False
  elif fault=='unknown-alt':wire['value']['case']='Unknown'
  elif fault=='unavailable':raise RuntimeError('controlled evaluator response unavailable after pure execution')
 return wire
for case in suite['cases']:
 conditions=clone(suite['conditions']);control={};apps=0;start=len(calls);obj=OutcomeOwner(policy=suite['policy'],sources=[suite['source']],state=suite['initial'],revision=7,resource='stock/g1',checker=checker,evaluator=evaluator,conditions=lambda:clone(conditions));outputs=[]
 for action in case['actions']:
  control=clone(action);conditions.update(control.get('conditions',{}))
  try:r=getattr(obj,action['command'])(edit.canonical(action['packet']))
  except (base.OwnerInputError,base.OwnerEvaluationError) as e:r={'error':e.code}
  except base.OwnerUnavailable:r={'error':'OwnerUnavailable'}
  outputs.append(r)
 actual={'outputs':outputs,**obj.snapshot(),'application_evaluations':apps};matched=edit.canonical(actual)==edit.canonical(case['expected']);rows.append({'id':case['id'],'matched':matched,'actual':actual,'expected':case['expected'],'reader_reference_calls':len(calls)-start})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'calls':calls,'scope':'Explicit /2 business outcome model; actual pure evaluation and data checks, serial in-memory receiver. OldOwner unchanged; this does not establish production behavior.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'matched':sum(r['matched'] for r in rows),'requested':len(rows),'calls':len(calls),'failures':[r for r in rows if not r['matched']]});assert result['status']=='PASSED'
