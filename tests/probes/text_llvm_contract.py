"""Check an explicitly admitted Text LLVM-data CLI; never run generated code."""
from pathlib import Path
import argparse,json,hashlib,subprocess
PIN='3abb7620cdc102d34401a330126eb0b9bdb5a114c0590305d00b8f4f72b5fdb2'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();binary=a.binary.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parents[2];raw=(root/'examples/probes/text-llvm-envelope-cases.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN;cases=json.loads(raw)['cases'];assert len(cases)==44;rows=[]
 for c in cases:
  ident=c['id'];assert all(x.isascii() and (x.isalnum() or x=='-') for x in ident);inp=out/(ident+'.source.json');inp.write_bytes(c['raw'].encode() if 'raw' in c else json.dumps(c['source'],ensure_ascii=True).encode());r=subprocess.run([str(binary),'emit-llvm','--input',str(inp)],capture_output=True,timeout=20);assert r.returncode==0 and not r.stderr,(ident,r.returncode);value=json.loads(r.stdout);assert r.stdout==canonical(value)+b'\n',ident
  if 'expected_refusal' in c:assert value==c['expected_refusal'],ident
  else:
   ref=c['reference'];assert set(value)=={'execution_admission','kind','llvm_ir','module_record','schema','source_pin'};assert value['execution_admission'] is False and value['kind']=='module' and value['schema']=='bagaev-typed-text-llvm/1';record=value['module_record'];llvm=value['llvm_ir'].encode();assert value['source_pin']==ref['source_pin']==record['binding']['source_pin'];assert record['artifact_pin']==ref['artifact_pin']=='sha256:'+hashlib.sha256(llvm).hexdigest();assert record['binding_pin']==ref['binding_pin']=='sha256:'+hashlib.sha256(canonical(record['binding'])).hexdigest();assert len(llvm)==record['module_bytes']==ref['module_bytes'];assert hashlib.sha256(canonical(record)+b'\n').hexdigest()==ref['record_sha256']
  (out/(ident+'.stdout')).write_bytes(r.stdout);rows.append({'id':ident,'matched':True,'wire_sha256':hashlib.sha256(r.stdout).hexdigest()});print(ident,'PASS',flush=True)
 (out/'result.json').write_text(json.dumps({'status':'PASS','fixture_sha256':PIN,'observations':rows,'scope':'Shared-library envelope integration, not new native execution or independent semantic proof'},indent=2)+'\n')
if __name__=='__main__':main()
