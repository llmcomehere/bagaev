"""Frozen values and limits through the unchanged reviewed typed-record10 core."""
from pathlib import Path
import json,hashlib,subprocess,copy,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-fold'
from outcome_host import configure
args=configure(reference=True);R=args.output;reader=args.reader;ref=args.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_fold_form as form
s=json.loads((D/'cases.json').read_bytes());rows=[];canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def run(name,source):
 program=copy.deepcopy(form.decode(source)['program']);program['entry']='calc';raw=canon({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':[]});f=R/(name+'.json');f.write_bytes(raw);q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);(R/(name+'.stdout')).write_bytes(q.stdout);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw;v=json.loads(q.stdout);rows.append({'id':name,'wire':v});return v
for c in s['positive']:
 v=run(c['id'],c['source']);assert v['status']=='success' and v['value_type']==c['value_type'] and type(v['value'])is type(c['value']) and v['value']==c['value'],(c['id'],v)
result={'status':'PASSED','reference_invocations':len(rows),'rows':rows};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':'PASSED','reference_invocations':len(rows)})
