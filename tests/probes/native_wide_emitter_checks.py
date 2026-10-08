from pathlib import Path
import json,hashlib,subprocess,copy,argparse,re
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/native-wide-emitter'
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
for name in ('emitter','legacy'):
 p.add_argument('--'+name,type=Path,required=True);p.add_argument('--'+name+'-sha256',required=True)
a=p.parse_args();R=a.output;assert R.is_absolute() and R.parent.is_dir() and not R.exists()
for name in ('emitter','legacy'):
 f=getattr(a,name);h=getattr(a,name+'_sha256');assert f.is_absolute() and f.is_file() and not f.is_symlink() and re.fullmatch('[0-9a-f]{64}',h);assert hashlib.sha256(f.read_bytes()).hexdigest()==h
R.mkdir(exist_ok=False);new=a.emitter;old=a.legacy
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
count=0

def run(exe,mode,path,ok=True):
 global count
 q=subprocess.run([str(exe),mode,'--input',str(path)],capture_output=True,timeout=20);count+=1
 assert (q.returncode==0 and not q.stderr) if ok else (q.returncode!=0 and not q.stdout),(path,q.stderr)
 return q.stdout
for name in ('sum','catalog'):
 path=D/(name+'-invocation.json');module=run(new,'emit',path);binding_raw=run(new,'binding',path);assert run(new,'emit',path)==module and run(new,'binding',path)==binding_raw
 v=json.loads(binding_raw);assert v['schema']=='bagaev-json-view11-llvm-module/1' and v['artifact_pin']=='sha256:'+hashlib.sha256(module).hexdigest() and v['module_bytes']==len(module)
 b=v['binding'];assert b['schema']=='bagaev-json-view11-llvm-binding/1' and b['execution_admission'] is False and b['cell_capacity']==b['scratch_capacity']==65536;assert b['source_pin']=='sha256:'+hashlib.sha256(b['source'].encode()).hexdigest();assert v['binding_pin']=='sha256:'+hashlib.sha256(json.dumps(b,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();assert '@bagaev_json_view11_kernel' in module.decode() and 'bagaev_json_view10_kernel' not in module.decode()
 (R/(name+'.ll')).write_bytes(module);(R/(name+'.binding.json')).write_bytes(binding_raw);run(old,'emit',path,False)
run(new,'emit',D/'typed-argument-invocation.json',False)
# Old schema remains refused even when the program uses only old-compatible features.
p=json.loads((D/'sum-invocation.json').read_bytes());p['schema']='bagaev-typed-record-invocation/10';p['program']['schema']='bagaev-typed-record/10';f=R/'old-schema.json';f.write_text(json.dumps(p));run(new,'emit',f,False)
result={'status':'PASSED','emitted_modules':2,'data_tool_calls':count,'refusals':4,'deterministic':True,'all_binding_hashes_verified':True,'native_compilation':'NOT_RUN','native_execution':'NOT_RUN'};(R/'result.json').write_text(json.dumps(result)+'\n');print(result)
