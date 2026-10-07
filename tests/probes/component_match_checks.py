"""Frozen match form observations; no core execution in this codec check."""
from pathlib import Path
import sys,json,hashlib,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-match'
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_match_form as form
import bagaev_component_arithmetic_form as old
s=json.loads((D/'cases.json').read_bytes());rows=[]
for c in s['positive']:
 actual=form.decode(c['source']);assert actual==c['expected'],c['id'];assert form.decode(form.encode(actual))==actual;rows.append(c['id'])
for c in s['syntax']:
 try:form.decode(c['source'])
 except form.FormError as e:assert e.code==c['code'],(c['id'],e.code)
 else:raise AssertionError(c['id'])
try:old.decode(s['positive'][0]['source'])
except old.FormError as e:assert e.code=='FORM_VERSION'
else:raise AssertionError('old accepted')
for name,ast in [('captured-arg',['match',['arg','value'],[['Decline','error',['int',-1]],['Propose','stock',['field',['arg','stock'],'quantity']]]]),('unbound-use',['match',['use','value'],[['Decline','error',['int',-1]],['Propose','stock',['field',['use','stock'],'quantity']]]])]:
 v=copy.deepcopy(s['positive'][0]['expected']);v['program']['functions']['quantity']['body']=ast;before=json.dumps(v,sort_keys=True)
 try:form.encode(v)
 except form.FormError as e:assert e.code=='FORM_PROFILE'
 else:raise AssertionError(name)
 assert json.dumps(v,sort_keys=True)==before
result={'status':'PASSED','exact_graphs':len(rows),'syntax_refusals':len(s['syntax']),'old_version_refuses':True,'encoding_scope_controls':2};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
