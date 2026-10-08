from pathlib import Path
import json,hashlib,sys,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/catalog-edit-workflow'
a=configure(reference=True);R=a.output;ref=a.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_json_form as form;import bagaev_record_json_draft as draft;import bagaev_record_json_diagnostics as diag
for c in json.loads((T/'examples/probes/record-diagnostics/cases.json').read_bytes()):
 raw_source=c['source'].replace('record-form/1','record-form/4').encode();observation=diag.diagnose(raw_source)
 assert observation['form']=='record-form/4' and observation['source_sha256']==hashlib.sha256(raw_source).hexdigest()
 if c['code'] is None:assert observation['valid_form'] and observation['error'] is None
 else:assert observation['error']=={'code':c['code'],'phase':c['phase'],'span':c.get('span')}
base=(T/'examples/probes/pure-json-form/Catalog.bagaev').read_bytes();candidate=json.loads((D/'candidate.json').read_bytes());source=form.encode(candidate);assert form.decode(source)==candidate
v=diag.diagnose(source);assert v['valid_form'] and v['form']=='record-form/4' and v['source_sha256']==hashlib.sha256(source).hexdigest() and not v['semantic_check']
bpin=draft.digest(form.decode(base));tpin=draft.digest(candidate);result=draft.draft(base,source,base_sha256=bpin,target_sha256=tpin);assert result['delta']=={'add':['id_ok_body'],'replace':['id_ok']} and result['program']==candidate and not result['execution_admission']
try:draft.draft(source,base,base_sha256=bpin,target_sha256=tpin)
except draft.DraftError as e:assert e.code=='DRAFT_BASE'
else:raise AssertionError('stale base accepted')
original=R/'original.bagaev';original.write_bytes(base);target=R/'candidate.bagaev';target.write_bytes(source)
for tool,args,out in [('record_diagnose.py',[str(target)],R/'diag.json'),('record_draft.py',[str(original),str(target),'--base',bpin,'--target',tpin],R/'draft.json')]:
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools'/tool),*args,'--form','4','--output',str(out)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr
assert json.loads((R/'draft.json').read_bytes())==result

raw=(T/'examples/beta/catalog-cases.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==(T/'examples/probes/pure-json-form/oracle-sha256.txt').read_text().strip();oracle=json.loads(raw)
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
for c in oracle['cases']:
 expected=oracle['responses'][c['expect']];inp=R/(c['id']+'.json');data=canonical({'schema':'bagaev-typed-record-invocation/10','program':result['program'],'arguments':[oracle['requests'][c['request']]]}).encode();inp.write_bytes(data);q=subprocess.run([str(ref),'run','--input',str(inp)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and inp.read_bytes()==data;v=json.loads(q.stdout);assert v['status']=='success' and v['value']['case']==('Ok' if expected['kind']=='success' else 'Error') and canonical(v['value']['value'])==canonical(expected);(R/(c['id']+'.stdout')).write_bytes(q.stdout)
assert original.read_bytes()==base and target.read_bytes()==source
r={'status':'PASSED','functions':25,'literal_cases':99,'reference_calls':99,'cli_calls':2,'stale_refusals':1,'delta':result['delta']};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
