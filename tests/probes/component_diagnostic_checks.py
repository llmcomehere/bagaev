"""Frozen independent endpoints plus original-codec outcome equivalence."""
from pathlib import Path
import json,hashlib,sys,subprocess
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-diagnostics'
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
manifest=json.loads((D/'manifest.json').read_bytes())
for n,h in manifest['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
for n,h in manifest['unchanged'].items():assert hashlib.sha256((T/n).read_bytes()).hexdigest()==h
for n,h in manifest.get('dependencies',{}).items():assert hashlib.sha256((T/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_component_arithmetic_diagnostics as diag
import bagaev_component_arithmetic_form as form
R.mkdir(exist_ok=False);rows=[]
def materialize(spec):
 if 'text'in spec:return spec['text']
 if 'hex'in spec:return bytes.fromhex(spec['hex'])
 if 'repeat'in spec:return spec.get('prefix','')+spec['repeat']*spec['count']
 return spec['value']
for c in json.loads((D/'cases.json').read_bytes())['cases']:
 source=materialize(c['input']);actual=diag.diagnose(source);assert actual==c['expected'],(c['id'],actual,c['expected'])
 try:form.decode(source);original=None
 except form.FormError as e:original=e.code
 assert original==(actual['error']['code'] if actual['error'] else None),c['id']
 if type(source) in (str,bytes) and len(source.encode() if type(source)is str else source)<=1048576:
  inp=R/(c['id']+'.bagaev');raw=source.encode() if type(source)is str else source;inp.write_bytes(raw)
  q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/component_diagnose.py'),str(inp)],capture_output=True,timeout=20);(R/(c['id']+'.stdout')).write_bytes(q.stdout);assert q.returncode==(0 if actual['valid_form'] else 2) and not q.stderr and json.loads(q.stdout)==actual and inp.read_bytes()==raw
 rows.append({'id':c['id'],'matched':True,'diagnostic':actual})
encoding_rows=[]
for name,source in [('oversize-invalid-bytes',b' '*1048576+b'\xff'),('oversize-surrogate',' '*1048576+'\ud800')]:
 actual=diag.diagnose(source);assert actual['source_sha256'] is None and actual['error']=={'code':'FORM_SYNTAX','phase':'transport','span':None}
 try:form.decode(source)
 except form.FormError as e:assert e.code=='FORM_SYNTAX'
 else:raise AssertionError(name)
 encoding_rows.append({'id':name,'same_refusal':True})
transport=[]
big=R/'oversize';big.write_bytes(b' '*1048577);link=R/'symlink';link.symlink_to(R/'valid.bagaev')
for name,argv,code in [('directory',[R],'COMPONENT_PATH'),('symlink',[link],'COMPONENT_PATH'),('oversize',[big],'COMPONENT_BOUNDS'),('usage',[R,'extra'],'TOOL_USAGE')]:
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/component_diagnose.py'),*map(str,argv)],capture_output=True,timeout=20);assert q.returncode==2 and not q.stderr;v=json.loads(q.stdout);assert v['error']=={'code':code,'phase':'transport','span':None} and v['source_sha256'] is None;transport.append({'id':name,'code':code})
result={'status':'PASSED','cases':len(rows),'rows':rows,'encoding_supplements':encoding_rows,'transport':transport,'scope':'Lexical token or parser context spans only; lowering span unavailable, no semantic checking.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASSED','cases':len(rows)}))
