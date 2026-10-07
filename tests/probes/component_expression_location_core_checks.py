"""Map one actual typed-core refusal back to the exact authored expression."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-expression-locations'
from outcome_host import configure
args=configure(reference=True);R=args.output;ref=args.reference;R.mkdir(exist_ok=False)
sys.path.insert(0,str(T/'src'));import bagaev_component_expression_locations as loc
import bagaev_component_match_form as form
c=json.loads((D/'cases.json').read_bytes())['cases'][0];text=c['source'].replace('Decline(error): -1','Decline(error): true');component=copy.deepcopy(c['component']);component['program']['functions']['quantity']['body'][2][0][2]=['bool',True]
assert form.decode(text)==component
canonical=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()

# Keep the exact component program, including its original apply entry.
invocation={'schema':'bagaev-typed-record-invocation/10','program':component['program'],'arguments':[{'key':{'code':'sku1'},'note':'kept','quantity':10},{'item':{'code':'sku1'},'expected':{'value':7},'delta':1}]};raw=canonical(invocation);f=R/'invocation.json';f.write_bytes(raw)
q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);(R/'stdout.json').write_bytes(q.stdout);assert q.returncode==0 and not q.stderr and f.read_bytes()==raw;wire=json.loads(q.stdout)
assert wire['status']=='invalid-ir' and wire['reason']=='RR_TYPE' and wire['work']==0 and wire['location']=='/program/functions/quantity/body/2/1/2',wire
result=loc.locate(text,wire['location'],source_sha256=hashlib.sha256(text.encode()).hexdigest(),component_sha256=hashlib.sha256(canonical(component)).hexdigest());span=result['span'];assert text.encode()[span['start_byte']:span['end_byte']]==b'stock.quantity'
assert result['semantic_check'] is False and result['execution_admission'] is False
(R/'result.json').write_text(json.dumps({'status':'PASSED','actual_core_refusal':wire,'location':result,'scope':'One real zero-work type refusal on unchanged component program; location lookup grants no checker authority.'},indent=2)+'\n');print(json.dumps({'status':'PASSED','reason':wire['reason'],'work':wire['work'],'selected_expression':'stock.quantity'}))
