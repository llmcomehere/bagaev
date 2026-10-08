from pathlib import Path
import json,hashlib,sys,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/pure-optional-fields'
a=configure(reference=True);R=a.output;ref=a.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_optional_fields_form as form;import bagaev_record_option_form as old

s=json.loads((D/'cases.json').read_bytes());rows=[]
for c in s['cases']:
 p=form.decode(c['source']);assert p==c['program'];assert form.decode(form.encode(p))==p
 try:old.decode(c['source'])
 except old.FormError as e:assert e.code=='FORM_VERSION'
 else:raise AssertionError('old accepted3')
 f=R/(c['id']+'.json');raw=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':p,'arguments':c['arguments']}).encode();f.write_bytes(raw);q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw;v=json.loads(q.stdout);(R/(c['id']+'.stdout')).write_bytes(q.stdout)
 if 'reason'in c:assert v['reason']==c['reason'] and v['value'] is None,v
 else:assert v['status']=='success' and json.dumps(v['value'],sort_keys=True)==json.dumps(c['value'],sort_keys=True),v
 rows.append(v)
for c in s['syntax']:
 try:form.decode(c['source'])
 except form.FormError as e:assert e.code==c['code'],(c,e.code)
 else:raise AssertionError('syntax accepted')
bad=json.loads(json.dumps(s['cases'][0]['program']));bad['records']['Entry']['date']['omit_none']=False
try:form.encode(bad)
except form.FormError as e:assert e.code=='FORM_PROFILE'
else:raise AssertionError('malformed metadata accepted')

source=R/'input.bagaev';source.write_text(s['cases'][0]['source']);program_file=R/'program.json'
def cli(op,inp,out,extra=()):
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_text.py'),op,str(inp),'--form','3','--output',str(out),*map(str,extra)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr
cli('decode',source,program_file);assert json.loads(program_file.read_bytes())==s['cases'][0]['program']
cli('encode',program_file,R/'back.bagaev');assert form.decode((R/'back.bagaev').read_bytes())==s['cases'][0]['program']
args=R/'args.json';args.write_text('[{"id":1}]');cli('prepare',source,R/'invoke.json',['--arguments',args]);assert json.loads((R/'invoke.json').read_bytes())['arguments']==[{'id':1}]
cli('inspect',source,R/'info.json');assert json.loads((R/'info.json').read_bytes())['types']['records']==1
legacy=json.loads((T/'examples/probes/pure-option-form/cases.json').read_bytes())
for c in legacy['positive']:assert form.decode(c['source'].replace('record-form/2','record-form/3'))==c['program']

r={'status':'PASSED','native_invocations':7,'cli_calls':4,'inherited_graphs':5,'full_values':6,'null_refusals':1,'syntax_refusals':2,'encoder_refusals':1};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
