"""Pre-frozen readable collection graphs and exact roundtrip."""
from pathlib import Path
import json,hashlib,sys,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-text-list'
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_text_list_form as form
import bagaev_component_match_form as prior
s=json.loads((D/'cases.json').read_bytes());rows=[]
for c in s['positive']:
 actual=form.decode(c['source']);assert actual==c['expected'],c['id'];before=json.dumps(actual,sort_keys=True);assert form.decode(form.encode(actual))==actual and json.dumps(actual,sort_keys=True)==before;rows.append(c['id'])
for c in s['syntax']:
 try:form.decode(c['source'])
 except form.FormError as e:assert e.code==c['code'],(c['id'],e.code)
 else:raise AssertionError(c['id'])
for call in [lambda:prior.decode(s['positive'][0]['source']),lambda:form.decode(s['positive'][0]['source'].replace('component-form/5','component-form/4'))]:
 try:call()
 except form.FormError as e:assert e.code=='FORM_VERSION'
 else:raise AssertionError('version accepted')
v=copy.deepcopy(s['positive'][0]['expected']);v['program']['variants']['text']={'eq':'Int64'};v['program']['functions']['calc'].update(result='text',body=['variant','text','eq',['int',1]])
try:form.encode(v)
except form.FormError as e:assert e.code=='FORM_PROFILE'
else:raise AssertionError('intrinsic collision encoded')
for op in [[],{},None,True]:
 v=copy.deepcopy(s['positive'][0]['expected']);v['program']['functions']['calc']['body']=[op]
 try:form.encode(v)
 except form.FormError as e:assert e.code=='FORM_PROFILE'
 else:raise AssertionError('non-string operator accepted')
result={'status':'PASSED','operator_kind_refusals':4,'exact_graphs':len(rows),'syntax_refusals':len(s['syntax']),'version_gates':2,'namespace_collision_refusals':1};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
