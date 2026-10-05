"""Explicit bounded typed Text-list reference runner against pre-implementation data.
Requires an independently admitted execution profile; never compiles a candidate.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
PIN='eac96268c91fd4008c2065a1418d8ec91ee52f14c3bb87cbafdb6a2d5c47169d'
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();binary=a.binary.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 root=Path(__file__).resolve().parents[2];raw=(root/'examples/probes/typed-list-cases.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
 cases=json.loads(raw)['cases'];assert len(cases)==32;rows=[]
 for case in cases:
  ident=case['id'];assert all(x.isascii() and (x.isalnum() or x=='-') for x in ident)
  data=canonical(case['invocation']);p=out/(ident+'.input');p.write_bytes(data)
  try:r=subprocess.run([str(binary),'run','--input',str(p)],capture_output=True,timeout=15);code=r.returncode;actual=r.stdout;error=r.stderr.decode('utf-8','replace')
  except subprocess.TimeoutExpired:code=None;actual=b'';error='timeout'
  expected=canonical(case['expected'])+b'\n';match=code==0 and actual==expected
  (out/(ident+'.stdout')).write_bytes(actual);rows.append({'id':ident,'exit':code,'exact_wire_match':match,'expected':case['expected'],'actual_sha256':hashlib.sha256(actual).hexdigest(),'stderr':error});print(ident,'PASS' if match else 'FAIL',flush=True)
 result={'status':'PASS' if all(x['exact_wire_match'] for x in rows) else 'FAILED','fixture_sha256':PIN,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'observations':rows,'scope':'Typed Text-list reference evaluator only; not generated native list code or performance evidence'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
