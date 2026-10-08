from pathlib import Path
import json,hashlib,sys,subprocess,copy
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/pure-json-form'
a=configure(reference=True);R=a.output;ref=a.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_json_form as form
oracle_raw=(T/'examples/beta/catalog-cases.json').read_bytes();assert hashlib.sha256(oracle_raw).hexdigest()==(D/'oracle-sha256.txt').read_text().strip();oracle=json.loads(oracle_raw);assert len(oracle['cases'])==99
program=json.loads((D/'program.json').read_bytes());source=(D/'Catalog.bagaev').read_bytes();assert form.decode(source)==program and form.decode(form.encode(program))==program;(R/'Catalog.bagaev').write_bytes(source)

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
actual={};rows=[]
def run(ident,request,expected):
 f=R/(ident+'.json');raw=canonical({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':[request]}).encode();f.write_bytes(raw);q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw;v=json.loads(q.stdout);(R/(ident+'.stdout')).write_bytes(q.stdout)
 assert v['status']=='success',(ident,v)
 wrapper=v['value'];assert wrapper['case']==('Ok' if expected['kind']=='success' else 'Error') and canonical(wrapper['value'])==canonical(expected),(ident,v,expected)
 rows.append({'id':ident,'work':v['work'],'complete_match':True});return wrapper['value']
index={c['id']:c for c in oracle['cases']}
for c in oracle['cases']:actual[c['id']]=run(c['id'],oracle['requests'][c['request']],oracle['responses'][c['expect']])
feeds=0;steps=0
for chain in oracle['chains']:
 previous=None
 for ident in chain['cases']:
  c=index[ident];request=copy.deepcopy(oracle['requests'][c['request']])
  if previous is not None:
   assert canonical(previous['state'])==canonical(request['state']);request['state']=copy.deepcopy(previous['state']);feeds+=1
  previous=run('chain-'+str(steps),request,oracle['responses'][c['expect']]);steps+=1

small='bagaev record-form/4; program { entry calc; fn calc(x: Json) -> Json = json.field(x, "date"); }'
for source_text,code in [(small.replace('"date"','"d" + "a"'),'FORM_PROFILE'),(small.replace('"date"','"'+'é'*33+'"'),'FORM_BOUNDS')]:
 try:form.decode(source_text)
 except form.FormError as e:assert e.code==code
 else:raise AssertionError('literal-key refusal')
import bagaev_record_optional_fields_form as old
try:old.decode(small)
except old.FormError as e:assert e.code=='FORM_VERSION'
else:raise AssertionError('old form accepted4')
source_file=D/'Catalog.bagaev';out=R/'cli-program.json';args=R/'cli-args.json';args.write_text(canonical([oracle['requests']['REV-3']]))
for op,inp,target,extra in [('decode',source_file,out,[]),('encode',out,R/'cli-back.bagaev',[]),('prepare',source_file,R/'cli-invocation.json',['--arguments',str(args)]),('inspect',source_file,R/'cli-info.json',[])]:
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_text.py'),op,str(inp),'--form','4','--output',str(target),*extra],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr
assert json.loads(out.read_bytes())==program and form.decode((R/'cli-back.bagaev').read_bytes())==program
assert json.loads((R/'cli-invocation.json').read_bytes())=={'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':[oracle['requests']['REV-3']]}
assert len(json.loads((R/'cli-info.json').read_bytes())['functions'])==24

r={'status':'PASSED','literal_cases':99,'cli_calls':4,'syntax_version_refusals':3,'chain_steps':steps,'actual_predecessor_feeds':feeds,'reference_calls':len(rows),'functions':len(program['functions']),'source_bytes':len(source),'rows':rows};(R/'result.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='rows'})
