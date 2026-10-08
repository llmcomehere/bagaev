from pathlib import Path
import json,hashlib,sys,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/inventory-reserve'
a=configure(reference=True);R=a.output;R.mkdir(exist_ok=False);ref=a.reference
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_wide_form as form
raw=(D/'Reserve.bagaev').read_bytes();program=form.decode(raw);assert form.decode(form.encode(program))==program;(R/'program.json').write_text(json.dumps(program,indent=2)+'\n')
cases=json.loads((D/'cases.json').read_bytes())
for c in cases:
 f=R/(c['id']+'.json');data=json.dumps({'schema':'bagaev-typed-record-invocation/11','program':program,'arguments':c['arguments']}).encode();f.write_bytes(data);q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and f.read_bytes()==data;(R/(c['id']+'.stdout')).write_bytes(q.stdout);v=json.loads(q.stdout)
 if 'reason' in c:assert v['reason']==c['reason'] and v['value'] is None,(c['id'],v)
 else:assert v['status']=='success' and v['value']==c['value'],(c['id'],v)
result={'status':'PASSED','literal_cases':len(cases),'reference_calls':len(cases),'graph_roundtrip':True};(R/'result.json').write_text(json.dumps(result)+'\n');print(result)
