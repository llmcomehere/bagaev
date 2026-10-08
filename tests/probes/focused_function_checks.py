from pathlib import Path
import json,hashlib,sys,subprocess,copy
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/focused-function'
a=configure(reference=True);R=a.output;ref=a.reference;R.mkdir(exist_ok=False)
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_function as edit
form=edit.form;raw=(T/'examples/probes/pure-json-form/Catalog.bagaev').read_bytes();base=form.decode(raw);expected=json.loads((D/'candidate.json').read_bytes());packet=edit.fragment(raw,'id_ok');part=form.decode(packet['source']);assert set(part['functions'])=={'id_ok'} and part['entry']=='id_ok';assert len(packet['source'].encode())<len(raw)
part['functions']['id_ok']=copy.deepcopy(expected['functions']['id_ok']);replacement=form.encode(part)
v=edit.replace(raw,replacement,base_sha256=packet['base'],function_sha256=packet['function_sha256']);assert v['program']==expected and v['delta']=={'add':[],'replace':['id_ok']} and not v['semantic_check'] and not v['execution_admission'];assert v['target']==edit.digest(expected)
refusals=0
def refuse(part,code,b=packet['base'],f=packet['function_sha256']):
 global refusals
 try:edit.replace(raw,form.encode(part),base_sha256=b,function_sha256=f)
 except edit.DraftError as e:assert e.code==code,(e.code,code)
 else:raise AssertionError(code)
 refusals+=1
refuse(part,'FUNCTION_BASE',b='0'*64);refuse(part,'FUNCTION_PIN',f='0'*64);refuse(form.decode(packet['source']),'FUNCTION_NO_CHANGE')
bad=copy.deepcopy(part);bad['functions']['id_ok']['result']='Int64';refuse(bad,'FUNCTION_SIGNATURE')
bad=copy.deepcopy(part);bad['records']={};bad['lists']={};bad['variants']={};refuse(bad,'FUNCTION_SCOPE')
bad=copy.deepcopy(part);bad['functions']['extra']={'params':[],'result':'Int64','body':['int',0]};refuse(bad,'FUNCTION_SCOPE')
try:edit.fragment(raw,'missing')
except edit.DraftError as e:assert e.code=='FUNCTION_NAME';refusals+=1
else:raise AssertionError('unknown name')

oraw=(T/'examples/beta/catalog-cases.json').read_bytes();assert hashlib.sha256(oraw).hexdigest()==(T/'examples/probes/pure-json-form/oracle-sha256.txt').read_text().strip();oracle=json.loads(oraw);canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
for c in oracle['cases']:
 expect=oracle['responses'][c['expect']];f=R/(c['id']+'.json');data=canonical({'schema':'bagaev-typed-record-invocation/10','program':v['program'],'arguments':[oracle['requests'][c['request']]]}).encode();f.write_bytes(data);q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and f.read_bytes()==data;result=json.loads(q.stdout);assert result['status']=='success' and result['value']['case']==('Ok' if expect['kind']=='success' else 'Error') and canonical(result['value']['value'])==canonical(expect);(R/(c['id']+'.stdout')).write_bytes(q.stdout)
v['program']['functions']['id_ok']['body']=['bool',False];assert form.decode(raw)==base
(R/'fragment.bagaev').write_text(packet['source']);(R/'replacement.bagaev').write_bytes(replacement)

original=R/'original.bagaev';original.write_bytes(raw);replacement_file=R/'replacement.bagaev'
cli_calls=0
def cli(args,error=None):
 global cli_calls
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_function.py'),*map(str,args)],capture_output=True,timeout=20);assert not q.stderr and q.returncode==(2 if error else 0)
 if error:assert json.loads(q.stdout)['error']['code']==error
 cli_calls+=1
packet_file=R/'packet.json';cli(['extract',original,'--name','id_ok','--output',packet_file]);assert json.loads(packet_file.read_bytes())==packet
out=R/'draft.json';cmd=['replace',original,'--replacement',replacement_file,'--base',packet['base'],'--function-pin',packet['function_sha256'],'--output',out];cli(cmd);assert json.loads(out.read_bytes())['program']==expected
saved=out.read_bytes();cli(cmd,'RECORD_PATH');assert out.read_bytes()==saved
cli(['extract',original,'--name','id_ok','--base',packet['base'],'--output',R/'bad'],'TOOL_USAGE');assert not (R/'bad').exists()
assert original.read_bytes()==raw

r={'status':'PASSED','literal_cases':99,'cli_calls':cli_calls,'reference_calls':99,'refusals':refusals,'full_source_bytes':len(raw),'fragment_bytes':len(packet['source'].encode()),'changed_functions':1};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
