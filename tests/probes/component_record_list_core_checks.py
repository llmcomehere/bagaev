"""Frozen values and limits through the unchanged reviewed typed-record10 core."""
from pathlib import Path
import json,hashlib,subprocess,copy,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-record-list'
from outcome_host import configure
args=configure(reference=True);R=args.output;reader=args.reader;ref=args.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_record_list_form as form
s=json.loads((D/'cases.json').read_bytes());rows=[];canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def run(name,source):
 program=copy.deepcopy(form.decode(source)['program']);program['entry']='calc';raw=canon({'schema':'bagaev-typed-record-invocation/10','program':program,'arguments':[]});f=R/(name+'.json');f.write_bytes(raw);q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);(R/(name+'.stdout')).write_bytes(q.stdout);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw;v=json.loads(q.stdout);rows.append({'id':name,'wire':v});return v
for c in s['positive']:
 v=run(c['id'],c['source']);assert v['status']=='success' and v['value_type']==('RecordList:'+c['value_type'] if c['value_type']=='Items' else c['value_type']) and type(v['value'])is type(c['value']) and v['value']==c['value'],(c['id'],v)
for c in s['core_refusals']:
 text=s['template'].rstrip()[:-1]+f" fn calc() -> {c['type']} = {c['expression']};\n}}\n";value=form.decode(text);assert value['program']['functions']['calc']['body']==c['body'];v=run(c['id'],text);assert v['status']!='success' and v['reason']==c['reason'],(c['id'],v)
c=s['positive'][0];raw=canon(c['expected']);f=R/'source.json';f.write_bytes(raw);policy=T/'examples/probes/component-arithmetic/policy.json';pb=policy.read_bytes();q=subprocess.run([str(reader),'policy',str(f),str(policy)],capture_output=True,timeout=20);(R/'policy.stdout').write_bytes(q.stdout);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw and policy.read_bytes()==pb;wire=json.loads(q.stdout);assert wire['status']=='checked' and wire['policy_compatible'] is True and wire['execution_admission'] is False
result={'status':'PASSED','reference_invocations':len(rows),'source_policy_checks':1,'rows':rows,'scope':'Pre-frozen values/reasons, unchanged core; recorded work/location are observations, not independent full-wire oracles.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
