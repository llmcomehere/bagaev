"""New explicit frame with unchanged shared compatibility rules and real checking."""
from pathlib import Path
import json,hashlib,subprocess,sys,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-arithmetic/edit';sys.path.insert(0,str(T/'src'))
import bagaev_component_arithmetic_edit as edit
import bagaev_component_outcome_edit as old
from outcome_host import configure
args=configure(reference=True);R=args.output;reader=args.reader;ref=args.reference
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
R.mkdir(exist_ok=False);suite=json.loads((D/'cases.json').read_bytes());rows=[];calls=[];drafts={}
def invoke(binary,args,inputs):
 paths=[]
 for suffix,raw in inputs:
  f=R/f'{len(calls):02d}.{suffix}';f.write_bytes(raw);paths.append(f)
 q=subprocess.run([str(binary),*args,*map(str,paths)],capture_output=True,timeout=20)
 (R/f'{len(calls):02d}.stdout').write_bytes(q.stdout);(R/f'{len(calls):02d}.stderr').write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and all(f.read_bytes()==b for f,(_,b) in zip(paths,inputs));v=json.loads(q.stdout);calls.append({'binary':binary.name,'observation':v});return v
def checker(a,b):return invoke(reader,['policy'],[('source.json',a),('policy.json',b)])
def substitute(a,b):
 v=checker(a,b);v['source_sha256']='0'*64;return v
def profile(a,b):
 v=checker(a,b);v['schema']='bagaev-component-check/1';return v
for c in suite['cases']:
 before=edit.canonical(c);start=len(calls)
 try:actual=edit.draft(suite['original'],edit.canonical(c['frame']),edit.canonical(suite['policy']),{'actual':checker,'missing':None,'substitute':substitute,'profile':profile}[c['checker']],candidate_map=c['map'])
 except edit.EditError as e:actual={'error':e.code}
 except edit.CheckerUnavailable:actual={'error':'CheckerUnavailable'}
 except edit.ComponentRefused as e:actual={'error':'ComponentRefused','stage':e.stage,'reason':e.reason}
 assert actual==c['expected'],(c['id'],actual,c['expected']);assert edit.canonical(c)==before
 if actual.get('status')=='draft':drafts[c['id']]=actual
 rows.append({'id':c['id'],'matched':True,'calls':len(calls)-start})
try:old.frame(edit.canonical(suite['cases'][0]['frame']))
except old.EditError as e:assert e.code=='EDIT_VERSION'
else:raise AssertionError('old frame accepted')
controls=[]
for name in ['helper','business-wrong-draft']:
 v=invoke(ref,['run','--input'],[('invocation.json',edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':drafts[name]['component']['program'],'arguments':suite['zero_arguments']}))]);assert v['status']=='success';matched=v['value']==suite['zero_expected'];assert matched is (name=='helper');controls.append({'draft':name,'matches_literal_zero':matched,'actual':v})
result={'status':'PASSED','cases':len(rows),'calls':len(calls),'rows':rows,'zero_controls':controls,'old_frame_refuses':True,'scope':'Detached checked source/2 drafts only; no registration/admission. Compatibility is not business refinement.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('rows','zero_controls')}))
