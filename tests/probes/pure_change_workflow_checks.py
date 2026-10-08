from pathlib import Path
import sys,json,hashlib,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];a=configure(reference=True);R=a.output;R.mkdir(exist_ok=False)
s=json.loads((T/'examples/probes/pure-record-draft/cases.json').read_bytes());calls=[]
def cli(tool,args,error=None):
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools'/tool),*map(str,args)],capture_output=True,timeout=20);assert not q.stderr and q.returncode==(2 if error else 0);v=json.loads(q.stdout)
 if error:assert v['error']['code']==error
 calls.append({'tool':tool,'error':error});return v
pins={};sources={}
for name,key in [('base','base'),('helper','helper')]:
 f=R/(name+'.bagaev');f.write_text(s[key]);sources[name]=f;out=R/(name+'-info.json');cli('record_text.py',['inspect',f,'--output',out]);info=json.loads(out.read_bytes());expected=s[key+'_program'];canonical=json.dumps(expected,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
 assert info=={'schema':'bagaev-record-inspection/1','source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'program_sha256':hashlib.sha256(canonical).hexdigest(),'entry':'calc','functions':[{'name':n,'params':v['params'],'result':v['result']} for n,v in sorted(expected['functions'].items())],'types':{'records':0,'lists':0,'variants':0},'semantic_check':False,'execution_admission':False}
 pins[name]=info['program_sha256']
space=R/'space.bagaev';space.write_text('\n'+s['base']);cli('record_text.py',['inspect',space,'--output',R/'space-info.json']);info=json.loads((R/'space-info.json').read_bytes());assert info['program_sha256']==pins['base'] and info['source_sha256']!=json.loads((R/'base-info.json').read_bytes())['source_sha256']
draft=R/'draft.json';cli('record_draft.py',[sources['base'],sources['helper'],'--base',pins['base'],'--target',pins['helper'],'--output',draft]);assert json.loads(draft.read_bytes())['delta']=={'add':['plus_one'],'replace':['calc']}
args=R/'arguments.json';args.write_text('[7]')
for name in ['base','helper']:
 out=R/(name+'-invocation.json');cli('record_text.py',['prepare',sources[name],'--arguments',args,'--output',out]);raw=out.read_bytes();q=subprocess.run([str(a.reference),'run','--input',str(out)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and out.read_bytes()==raw;v=json.loads(q.stdout);assert v['status']=='success' and v['value']==8;(R/(name+'-result.json')).write_bytes(q.stdout)
cli('record_text.py',['inspect',sources['base'],'--arguments',args,'--output',R/'bad'],'TOOL_USAGE');assert not (R/'bad').exists()
saved=(R/'base-info.json').read_bytes();cli('record_text.py',['inspect',sources['base'],'--output',R/'base-info.json'],'RECORD_PATH');assert (R/'base-info.json').read_bytes()==saved
for name,key in [('base','base'),('helper','helper')]:assert sources[name].read_text()==s[key]
r={'status':'PASSED','cli_calls':len(calls),'refusals':2,'native_invocations':2,'preserved_result':8,'same_program_different_raw_pin':True};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
