from pathlib import Path
import json,copy,sys,subprocess,hashlib
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-record-list'
from outcome_host import configure
args=configure();R=args.output;reader=args.reader;R.mkdir(exist_ok=False);sys.path.insert(0,str(T/'src'))
import bagaev_component_record_list_form as form
import bagaev_component_fold_form as prior
s=json.loads((D/'cases.json').read_bytes());v=copy.deepcopy(s['positive'][0]['expected']);v['program']['records']['Stock']['items']='Items'
def patch(node):
 if isinstance(node,list):
  if node[:2]==['record','Stock']:node.insert(2,['records.list','Items'])
  for child in node:patch(child)
 elif isinstance(node,dict):
  for child in node.values():patch(child)
patch(v['program']['functions']);raw=json.dumps(v,sort_keys=True,separators=(',',':')).encode();source=R/'owned.json';source.write_bytes(raw);q=subprocess.run([str(reader),'check',str(source)],capture_output=True,timeout=20);(R/'owned.stdout').write_bytes(q.stdout);assert q.returncode==0 and not q.stderr;wire=json.loads(q.stdout);assert wire['status']=='refused' and wire['reason']=='CS_OWNED',wire
bad=[]
for name,body in [('missing-name',['records.list']),('unknown-name',['records.list','Missing']),('wrong-kind',['records.list',True])]:
 v=copy.deepcopy(s['positive'][0]['expected']);v['program']['functions']['calc']['body']=body
 try:form.encode(v)
 except form.FormError as e:assert e.code=='FORM_PROFILE';bad.append(name)
 else:raise AssertionError(name)
for c in json.loads((T/'examples/probes/component-fold/cases.json').read_bytes())['positive']:assert form.decode(c['source'].replace('component-form/6','component-form/7'))==c['expected']
try:prior.decode(s['positive'][0]['source'])
except form.FormError as e:assert e.code=='FORM_VERSION'
else:raise AssertionError('prior accepted')
result={'status':'PASSED','owned_refusal':wire,'encoder_refusals':bad,'legacy_fold_graphs':5,'prior_form6_refuses':True};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
