"""Pre-frozen readable collection graphs and exact roundtrip."""
from pathlib import Path
import json,hashlib,sys,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-fold'
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_fold_form as form
import bagaev_component_match_form as prior
s=json.loads((D/'cases.json').read_bytes());rows=[]
for c in s['positive']:
 actual=form.decode(c['source']);assert actual==c['expected'],c['id'];before=json.dumps(actual,sort_keys=True);assert form.decode(form.encode(actual))==actual and json.dumps(actual,sort_keys=True)==before;rows.append(c['id'])
for c in s['syntax']:
 try:form.decode(c['source'])
 except form.FormError as e:assert e.code==c['code'],(c['id'],e.code)
 else:raise AssertionError(c['id'])
result={'status':'PASSED','graphs':len(rows),'syntax_refusals':len(s['syntax'])};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
