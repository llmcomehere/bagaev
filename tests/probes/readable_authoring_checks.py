"""Connect accepted data-only authoring tools to the existing checked draft."""
from pathlib import Path
import json,hashlib,subprocess,sys
T=Path(__file__).resolve().parents[2]
from outcome_host import configure
args=configure(reference=True);R=args.output;reader=args.reader;reference=args.reference
sys.path.insert(0,str(T/'src'))
import bagaev_component_arithmetic_edit as edit
R.mkdir(exist_ok=False)
suite=json.loads((T/'examples/probes/component-arithmetic/edit/cases.json').read_bytes())
helper=next(c for c in suite['cases'] if c['id']=='helper')
original=suite['original'].encode();good=helper['frame']['source'].encode();bad=good.replace(b'entry apply;',b'entry apply',1)
assert bad!=good
for n,b in [('original.bagaev',original),('candidate.bagaev',good),('broken.bagaev',bad),('policy.json',edit.canonical(suite['policy']))]:(R/n).write_bytes(b)
manifest=json.loads((T/'examples/probes/component-arithmetic/edit/manifest.json').read_bytes())
for name,pin in manifest['sha256'].items():assert hashlib.sha256((T/'examples/probes/component-arithmetic/edit'/name).read_bytes()).hexdigest()==pin
rows=[]
def command(name,args,code):
 q=subprocess.run(args,capture_output=True,timeout=20);(R/(name+'.stdout')).write_bytes(q.stdout);(R/(name+'.stderr')).write_bytes(q.stderr)
 assert q.returncode==code and not q.stderr,(name,q.returncode,q.stderr)
 v=json.loads(q.stdout);rows.append(name);return v
for name,code in [('broken',2),('candidate',0)]:
 v=command('diagnose-'+name,[sys.executable,'-B','-S',str(T/'tools/component_diagnose.py'),str(R/(name+'.bagaev'))],code)
 assert v['valid_form'] is (code==0) and v['semantic_check'] is False and v['execution_admission'] is False
 if code:assert v['error']['code']=='FORM_SYNTAX' and v['error']['span']['kind']=='context'
for name in ['original','candidate']:
 v=command('decode-'+name,[sys.executable,'-B','-S',str(T/'tools/component_text.py'),'decode',str(R/(name+'.bagaev')),'--form','3','--output',str(R/(name+'.json'))],0)
 assert v['result']['execution_admission'] is False and v['result']['semantic_check'] is False
checks=[]
def checker(source,policy):
 n=len(checks);a=R/f'check-{n}.source.json';b=R/f'check-{n}.policy.json';a.write_bytes(source);b.write_bytes(policy)
 v=command(f'check-{n}',[str(reader),'policy',str(a),str(b)],0);assert a.read_bytes()==source and b.read_bytes()==policy;checks.append(v);return v
actual=edit.draft(original,edit.canonical(helper['frame']),(R/'policy.json').read_bytes(),checker,candidate_map=helper['map'])
assert actual==helper['expected'] and actual['execution_admission'] is False
assert edit.canonical(actual['component'])==(R/'candidate.json').read_bytes()
assert (R/'original.bagaev').read_bytes()==original and (R/'candidate.bagaev').read_bytes()==good and (R/'broken.bagaev').read_bytes()==bad
(R/'draft.json').write_bytes(edit.canonical(actual))
wrong=next(c for c in suite['cases'] if c['id']=='business-wrong-draft')
wrong_draft=edit.draft(original,edit.canonical(wrong['frame']),(R/'policy.json').read_bytes(),checker,candidate_map=wrong['map'])
assert wrong_draft==wrong['expected']
for name,draft,expected_match in [('helper',actual,True),('wrong',wrong_draft,False)]:
 f=R/(name+'.invocation.json');raw=edit.canonical({'schema':'bagaev-typed-record-invocation/10','program':draft['component']['program'],'arguments':suite['zero_arguments']});f.write_bytes(raw)
 observed=command('observe-'+name,[str(reference),'run','--input',str(f)],0)
 assert observed['status']=='success' and (observed['value']==suite['zero_expected']) is expected_match
 assert f.read_bytes()==raw
result={'status':'PASSED','file_cli_calls':4,'actual_source_policy_checks':len(checks),'exact_existing_draft':True,'pure_reference_invocations':2,'external_application_effects':0,'execution_admission':False,'scope':'Connected existing stages; no new semantic cases or independent oracle.'}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
