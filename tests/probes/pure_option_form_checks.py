from pathlib import Path
import json,hashlib,sys,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/pure-option-form'
a=configure(reference=True);R=a.output;ref=a.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_option_form as form;import bagaev_record_form as old
s=json.loads((D/'cases.json').read_bytes())
rows=[]
for c in s['positive']+[{'id':'wrong','source':s['wrong_type']}]:
 program=form.decode(c['source']);assert form.decode(form.encode(program))==program
 if 'program' in c:assert program==c['program']
 try:old.decode(c['source'])
 except old.FormError as e:assert e.code=='FORM_VERSION'
 else:raise AssertionError('old codec accepted2')
 inp=R/(c['id']+'.json');raw=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':[]}).encode();inp.write_bytes(raw);q=subprocess.run([str(ref),'run','--input',str(inp)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and inp.read_bytes()==raw;v=json.loads(q.stdout);(R/(c['id']+'.stdout')).write_bytes(q.stdout)
 if 'value' in c:assert v['status']=='success' and v['value_type']==c['value_type'] and type(v['value']) is type(c['value']) and v['value']==c['value']
 else:assert v['reason']==s['wrong_reason'] and v['value'] is None
 rows.append(v)
for c in s['syntax']:
 try:form.decode(c['source'])
 except form.FormError as e:assert e.code==c['code']
 else:raise AssertionError('syntax accepted')

source=R/'input.bagaev';source.write_text(s['positive'][1]['source']);out=R/'program.json';args=R/'args.json';args.write_text('[]');cli_calls=0
def cli(op,inp,output,extra=(),error=None):
 global cli_calls
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_text.py'),op,str(inp),'--form','2','--output',str(output),*map(str,extra)],capture_output=True,timeout=20);assert not q.stderr and q.returncode==(2 if error else 0)
 if error:assert json.loads(q.stdout)['error']['code']==error
 cli_calls+=1
cli('decode',source,out);assert json.loads(out.read_bytes())==s['positive'][1]['program']
cli('encode',out,R/'back.bagaev');assert form.decode((R/'back.bagaev').read_bytes())==s['positive'][1]['program']
cli('prepare',source,R/'invoke.json',['--arguments',args]);assert json.loads((R/'invoke.json').read_bytes())=={'schema':'bagaev-typed-record-invocation/10','program':s['positive'][1]['program'],'arguments':[]}
cli('inspect',source,R/'info.json');assert json.loads((R/'info.json').read_bytes())['entry']=='calc'
saved=out.read_bytes();cli('decode',source,out,error='RECORD_PATH');assert out.read_bytes()==saved

legacy=json.loads((T/'examples/probes/pure-record-form/cases.json').read_bytes())
for c in legacy['positive']:
 assert form.decode(c['source'].replace('record-form/1','record-form/2'))==c['expected']
r={'status':'PASSED','exact_graphs':5,'cli_calls':cli_calls,'native_invocations':6,'syntax_refusals':3,'old_version_refusals':6,'rows':rows};(R/'result.json').write_text(json.dumps(r)+'\n');print({k:v for k,v in r.items() if k!='rows'})
