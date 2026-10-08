from pathlib import Path
import json, hashlib, sys, subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2]
D=T/'examples/probes/pure-reindex-entry'
args=configure(reference=True);R=args.output;ref=args.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():
 assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'))
import bagaev_record_form as form
s=json.loads((D/'cases.json').read_bytes());raw=(D/'ReindexEntry.bagaev').read_bytes();p=form.decode(raw);assert p==s['program'];assert form.decode(form.encode(p))==p
rows=[]
for c in s['cases']:
 data=json.dumps({'schema':'bagaev-typed-record-invocation/10','program':p,'arguments':c['arguments']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();inp=R/(c['id']+'.json');inp.write_bytes(data);q=subprocess.run([str(ref),'run','--input',str(inp)],capture_output=True,timeout=20);(R/(c['id']+'.stdout')).write_bytes(q.stdout);(R/(c['id']+'.stderr')).write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and inp.read_bytes()==data;wire=json.loads(q.stdout)
 if 'reason' in c:assert wire['reason']==c['reason'] and wire['status']!='success' and wire['value'] is None
 else:assert wire['status']=='success' and wire['value_type']=='Record:Entry' and wire['value']==c['expected']
 rows.append({'id':c['id'],'wire':wire,'input_preserved':True})
assert (D/'ReindexEntry.bagaev').read_bytes()==raw
result={'status':'PASSED','native_invocations':5,'successful_values':4,'work_refusals':1,'rows':rows,'scope':'Pure function only; no state transition, runtime change or measurement.'};(R/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
