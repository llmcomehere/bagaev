from pathlib import Path
import json,hashlib,sys,subprocess
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/pure-record-form'
from outcome_host import configure
args=configure(reference=True);R=args.output;ref=args.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_form as form
s=json.loads((D/'cases.json').read_bytes());rows=[]
for c in s['positive']+[{'id':'type',**s['type_refusal']}]:
 p=form.decode(c['source']);assert p==c['expected'];assert form.decode(form.encode(p))==p;raw=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':p,'arguments':[]},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();path=R/(c['id']+'.json');path.write_bytes(raw);q=subprocess.run([str(ref),'run','--input',str(path)],capture_output=True,timeout=20);(R/(c['id']+'.stdout')).write_bytes(q.stdout);assert q.returncode==0 and not q.stderr and path.read_bytes()==raw;wire=json.loads(q.stdout)
 if 'reason' in c:assert wire['reason']==c['reason'] and wire['status']!='success'
 else:assert wire['status']=='success' and wire['value_type']==c['value_type'] and type(wire['value'])is type(c['value']) and wire['value']==c['value']
 rows.append({'id':c['id'],'wire':wire})
for c in s['syntax']:
 try:form.decode(c['source'])
 except form.FormError as e:assert e.code==c['code']
 else:raise AssertionError(c['id'])
result={'status':'PASSED','graphs':6,'reference_invocations':6,'syntax_refusals':3,'rows':rows};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
