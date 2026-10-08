"""Owned checked-source inspector only; all raw data observations packed together."""
from pathlib import Path
import json,hashlib,subprocess,copy,base64
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/native-source-locations'
from outcome_host import configure
a=configure();R=a.output;R.mkdir(exist_ok=False)
exe=a.reader;binary=hashlib.sha256(exe.read_bytes()).hexdigest();observations=[]
def pin(inv):return 'sha256:'+hashlib.sha256(json.dumps(inv['program'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def call(inv,mode='locations',node=None,expected_pin=None,ok=True,name='case',path=None):
 f=R/'input.json'
 if path is None:f.write_text(json.dumps(inv,ensure_ascii=False));path=f
 args=[mode,'--input',str(path),'--source-pin',pin(inv) if expected_pin is None else expected_pin]
 if node is not None:args+=['--node',str(node)]
 q=subprocess.run([str(exe),*args],capture_output=True,timeout=20)
 observations.append({'name':name,'args':args,'input_base64':base64.b64encode(path.read_bytes()).decode(),'exit':q.returncode,'stdout':q.stdout.decode(),'stderr':q.stderr.decode()})
 assert (q.returncode==0)==ok,(name,q.stderr)
 if not ok:assert not q.stdout;return q.stderr.decode()
 assert not q.stderr
 v=json.loads(q.stdout);assert v['source_pin']==pin(inv) and v['profile']=='bagaev-typed-record/11'
 assert v['semantic_check'] is True
 assert all(v[k] is False for k in ('program_executed','native_output_authenticated','execution_admission'))
 return v
for row in json.loads((D/'expected.json').read_bytes()):
 inv=json.loads((D/(row['id']+'.json')).read_bytes());allnodes=call(inv,name=row['id'])
 assert allnodes['node_count']==row['node_count']
 assert [n['id'] for n in allnodes['locations']]==list(range(1,row['node_count']+1))
 if 'nodes' in row:assert allnodes['locations']==row['nodes']
 else:assert allnodes['locations'][row['node']['id']-1]==row['node']
 target=row['nodes'][-1] if 'nodes' in row else row['node']
 single=call(inv,'locate',target['id'],name=row['id']+'-single')
 assert single['locations']==[target] and single['node_count']==row['node_count']
 permuted=copy.deepcopy(inv);permuted['program']=dict(reversed(list(permuted['program'].items())));permuted['program']['functions']=dict(reversed(list(permuted['program']['functions'].items())))
 assert call(permuted,name=row['id']+'-order')==allnodes
inv=json.loads((D/'add-overflow.json').read_bytes())
assert 'LOCATION_SOURCE_PIN' in call(inv,expected_pin='sha256:'+'0'*64,ok=False,name='wrong-pin')
for n in (0,65535,'-1','text'):assert 'LOCATION_NODE' in call(inv,'locate',n,ok=False,name='bad-node-'+str(n))
old=copy.deepcopy(inv);old['schema']='bagaev-typed-record-invocation/10';old['program']['schema']='bagaev-typed-record/10';call(old,ok=False,name='old-profile')
bad=copy.deepcopy(inv);bad['program']['functions']['main']['params']=[['x','Int64']];bad['arguments']=[1];call(bad,ok=False,name='typed-signature')
bad=copy.deepcopy(inv);bad['arguments']=[0];call(bad,ok=False,name='arity')
call(inv,mode='run',ok=False,name='no-run-mode')
link=R/'symlink.json';link.symlink_to(R/'input.json');call(inv,path=link,ok=False,name='symlink')
huge=R/'oversized.json';huge.write_bytes(b' '*1048577);call(inv,path=huge,ok=False,name='oversized')
program=json.loads((T/'examples/probes/inventory-json/program.json').read_bytes())
cases=json.loads((T/'examples/probes/inventory-json/cases.json').read_bytes())
a={'schema':'bagaev-typed-record-invocation/11','program':program,'arguments':[cases[0]['request']]}
b=copy.deepcopy(a);b['arguments']=[cases[1]['request']]
assert call(a,name='inventory-first')==call(b,name='inventory-second')
assert hashlib.sha256(exe.read_bytes()).hexdigest()==binary
(R/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
result={'status':'PASSED','data_calls':len(observations),'literal_sources':6,'single_locations':6,'order_invariance':6,'refusals':11,'arguments_do_not_change_map':True,'program_evaluations':0,'native_kernel_calls':0,'binary_sha256':binary}
(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
