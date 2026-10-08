from pathlib import Path
import json,hashlib,sys,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/inventory-change'
a=configure(reference=True);R=a.output;R.mkdir(exist_ok=False);ref=a.reference
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_wide_form as form
from bagaev_record_draft import digest
source=T/'examples/probes/inventory-reserve/Reserve.bagaev';original=source.read_bytes();base=form.decode(original);expected=form.decode((D/'ReserveLimited.bagaev').read_bytes());pins=json.loads((D/'pins.json').read_bytes());assert digest(base)==pins['base'] and digest(expected)==pins['target'];assert base!=expected
calls=0

def cli(tool,args,error=None):
 global calls
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools'/tool),*map(str,args)],capture_output=True,timeout=20);calls+=1;assert not q.stderr and q.returncode==(2 if error else 0),(tool,q.stdout,q.stderr)
 if error:assert json.loads(q.stdout)['error']['code']==error
 return q
ctx=R/'context.json';cli('record_function.py',['context',source,'--form','5','--name','reserve','--output',ctx]);c=json.loads(ctx.read_bytes());assert c['fragment']['base']==pins['base'] and c['fragment']['function_sha256']==pins['function'];assert [x['name'] for x in c['callees']]==['decrement','find','sku_ok','stock_ok']
draft=R/'draft.json';cli('record_function.py',['replace',source,'--form','5','--replacement',D/'ReserveLimited.fragment.bagaev','--base',pins['base'],'--function-pin',pins['function'],'--output',draft]);v=json.loads(draft.read_bytes());assert v['target']==pins['target'] and v['program']==expected and v['delta']=={'add':[],'replace':['reserve']}
exported=R/'candidate.bagaev';cli('record_export.py',[source,'--form','5','--draft',draft,'--base',pins['base'],'--target',pins['target'],'--output',exported]);assert form.decode(exported.read_bytes())==expected
for c in json.loads((D/'cases.json').read_bytes()):
 args=R/(c['id']+'.arguments.json');args.write_text(json.dumps(c['arguments']));inv=R/(c['id']+'.invocation.json');cli('record_text.py',['prepare',exported,'--form','5','--arguments',args,'--output',inv]);data=inv.read_bytes();assert json.loads(data)['program']==expected
 q=subprocess.run([str(ref),'run','--input',str(inv)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and inv.read_bytes()==data;(R/(c['id']+'.stdout')).write_bytes(q.stdout);wire=json.loads(q.stdout)
 if 'reason' in c:assert wire['reason']==c['reason'] and wire['value'] is None
 else:assert wire['status']=='success' and wire['value']==c['value'],(c['id'],wire)
cli('record_function.py',['replace',exported,'--form','5','--replacement',D/'ReserveLimited.fragment.bagaev','--base',pins['base'],'--function-pin',pins['function'],'--output',R/'stale.json'],'FUNCTION_BASE');assert not (R/'stale.json').exists();assert source.read_bytes()==original
result={'status':'PASSED','literal_cases':24,'reference_calls':24,'cli_calls':calls,'changed_functions':['reserve'],'stale_base_refused':True};(R/'result.json').write_text(json.dumps(result)+'\n');print(result)
