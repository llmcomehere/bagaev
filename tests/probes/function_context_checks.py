from pathlib import Path
import json,hashlib,sys,subprocess,argparse
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/function-context'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_function as edit
s=json.loads((D/'cases.json').read_bytes());program=edit.form.decode(s['source'])
for name in ['main','helper']:
 v=edit.context(s['source'],name);assert v['scope']=='direct-syntactic-calls' and v['fragment']==edit.fragment(s['source'],name) and not v['semantic_check'] and not v['execution_admission']
 assert [x['name'] for x in v['callers']]==s[name+'_callers'];assert [x['name'] for x in v['callees']]==s[name+'_callees']
 for x in v['callers']+v['callees']:
  f=program['functions'].get(x['name']);assert x=={'name':x['name'],'declared':f is not None,'params':f['params'] if f else None,'result':f['result'] if f else None,'function_sha256':edit.digest(f) if f else None}
  assert 'body' not in x
 v['fragment']['source']='changed';assert edit.fragment(s['source'],name)['source']!='changed'
raw=(T/'examples/probes/pure-json-form/Catalog.bagaev').read_bytes();v=edit.context(raw,'id_ok');assert [x['name'] for x in v['callers']]==s['catalog_id_ok_callers'];assert v['callees']==[]
for x in v['callers']:assert x['params']==[['x','Json']] and x['result']=='Bool' and x['declared']
source=R/'source.bagaev';source.write_bytes(raw);out=R/'context.json';q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_function.py'),'context',str(source),'--name','id_ok','--output',str(out)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and json.loads(out.read_bytes())==v and source.read_bytes()==raw
q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_function.py'),'context',str(source),'--name','missing','--output',str(R/'missing.json')],capture_output=True,timeout=20);assert q.returncode==2 and json.loads(q.stdout)['error']['code']=='FUNCTION_NAME' and not (R/'missing.json').exists()
r={'status':'PASSED','contexts':3,'cli_calls':2,'missing_refusals':1,'reference_calls':0,'scope':'Syntactic dependency metadata only'};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
