from pathlib import Path
import json,hashlib,sys,copy,subprocess
from outcome_host import configure
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/record-export'
a=configure(reference=True);R=a.output;R.mkdir(exist_ok=False);ref=a.reference
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import bagaev_record_export as export
cli_calls=0;refusals=0
for version,source,candidate in [('4','pure-json-form','focused-function'),('5','catalog-wide','wide-function')]:
 edit=export.wide if version=='5' else export.narrow;raw=(T/f'examples/probes/{source}/Catalog.bagaev').read_bytes();base=edit.form.decode(raw);target=json.loads((T/f'examples/probes/{candidate}/candidate.json').read_bytes());part=edit.form.decode(edit.fragment(raw,'id_ok')['source']);part['functions']['id_ok']=target['functions']['id_ok'];packet=edit.replace(raw,edit.form.encode(part),base_sha256=edit.digest(base),function_sha256=edit.digest(base['functions']['id_ok']));assert packet['program']==target
 params={'base_sha256':packet['base'],'target_sha256':packet['target'],'form_version':version};out=export.export_source(raw,packet,**params);assert edit.form.decode(out)==target
 def refuse(value,code,**changes):
  global refusals
  try:export.export_source(raw,value,**(params|changes))
  except export.DraftError as e:assert e.code==code,(e.code,code)
  else:raise AssertionError(code)
  refusals+=1
 refuse(packet,'EXPORT_BASE',base_sha256='0'*64);refuse(packet,'EXPORT_TARGET',target_sha256='0'*64)
 for key,val in [('semantic_check',True),('execution_admission',0),('delta',{'add':['oops'],'replace':[]}),('extra',True)]:
  bad=copy.deepcopy(packet);bad[key]=val;refuse(bad,'EXPORT_PACKET')
 bad=copy.deepcopy(packet);bad['program']['entry']='id_ok';bad['target']=edit.digest(bad['program']);refuse(bad,'EXPORT_SCOPE',target_sha256=bad['target'])
 bad=copy.deepcopy(packet);bad['program']['functions']['id_ok']['result']='Int64';bad['target']=edit.digest(bad['program']);refuse(bad,'FUNCTION_SIGNATURE',target_sha256=bad['target'])
 original=R/f'original{version}.bagaev';original.write_bytes(raw);draft=R/f'draft{version}.json';draft.write_text(json.dumps(packet));output=R/f'candidate{version}.bagaev'
 cmd=[sys.executable,'-B','-S',str(T/'tools/record_export.py'),str(original),'--draft',str(draft),'--base',packet['base'],'--target',packet['target'],'--form',version,'--output',str(output)]
 q=subprocess.run(cmd,capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and output.read_bytes()==out;cli_calls+=1
 q=subprocess.run(cmd,capture_output=True,timeout=20);assert q.returncode==2 and json.loads(q.stdout)['error']['code']=='RECORD_PATH' and output.read_bytes()==out;cli_calls+=1
 assert original.read_bytes()==raw
 if version=='5':
  case=json.loads((T/'examples/probes/catalog-wide/cases.json').read_bytes())[0];args=R/'arguments.json';args.write_text(json.dumps([case['request']]));inv=R/'invocation.json'
  q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/record_text.py'),'prepare',str(output),'--form','5','--arguments',str(args),'--output',str(inv)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr;cli_calls+=1
  q=subprocess.run([str(ref),'run','--input',str(inv)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr;(R/'reference.stdout').write_bytes(q.stdout);wire=json.loads(q.stdout);assert wire['status']=='success' and wire['value']=={'case':'Ok','value':case['expected']}
result={'status':'PASSED','forms':2,'refusals':refusals,'cli_calls':cli_calls,'reference_calls':1,'full_sixteen_entry_response':True};(R/'result.json').write_text(json.dumps(result)+'\n');print(result)
