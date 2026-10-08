from pathlib import Path
import json,hashlib,sys,subprocess,argparse
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/record-diagnostics'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);R=p.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_form as form;import bagaev_record_diagnostics as diag
rows=json.loads((D/'cases.json').read_bytes())
for c in rows:
 raw=c['source'].encode();v=diag.diagnose(raw)
 assert v['form']=='record-form/1' and v['source_sha256']==hashlib.sha256(raw).hexdigest() and not v['semantic_check'] and not v['execution_admission']
 try:form.decode(raw);code=None
 except form.FormError as e:code=e.code
 assert code==c['code'] and v['valid_form']==(code is None)
 if code:assert v['error']=={'code':code,'phase':c['phase'],'span':c.get('span')},(c['id'],v)
 else:assert v['error'] is None
 inp=R/(c['id']+'.bagaev');inp.write_bytes(raw);out=R/(c['id']+'.json');q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_diagnose.py'),str(inp),'--output',str(out)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and json.loads(out.read_bytes())==v and inp.read_bytes()==raw
 assert json.loads(q.stdout)['diagnostic']==v
for x in [b'\xff','\ud800',None]:assert diag.diagnose(x)['error']['phase']=='transport'
assert diag.diagnose(b' '*1048577)['error']['code']=='FORM_BOUNDS'
result={'status':'PASSED','exact_observations':len(rows),'cli_calls':len(rows),'transport_controls':4};(R/'result.json').write_text(json.dumps(result)+'\n');print(result)
