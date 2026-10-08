from pathlib import Path
import json,hashlib,sys,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/pure-batch-reindex'
a=configure(reference=True);R=a.output;ref=a.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_form as form
raw=(D/'ReindexBatch.bagaev').read_bytes();program=form.decode(raw);assert form.decode(form.encode(program))==program

rows=[]
for c in json.loads((D/'cases.json').read_bytes())['cases']:
 data=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':c['arguments']},ensure_ascii=False,sort_keys=True).encode();f=R/(c['id']+'.json');f.write_bytes(data)
 q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);(R/(c['id']+'.stdout')).write_bytes(q.stdout);(R/(c['id']+'.stderr')).write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and f.read_bytes()==data
 v=json.loads(q.stdout)
 if 'reason' in c:assert v['reason']==c['reason'] and v['value'] is None,v
 else:assert v['status']=='success' and json.dumps(v['value'],sort_keys=True)==json.dumps(c['expected'],sort_keys=True),v
 rows.append({'id':c['id'],'result':v})
assert (D/'ReindexBatch.bagaev').read_bytes()==raw
result={'status':'PASSED','native_invocations':6,'full_values':5,'work_refusals':1,'rows':rows};(R/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
