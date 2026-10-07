"""Frozen data-only conversion CLI checks; source programs are never evaluated."""
from pathlib import Path
import json,hashlib,subprocess,sys
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/component-outcomes/form'
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);R=parser.parse_args().output
assert R.is_absolute() and R.parent.is_dir() and not R.exists()
for n,h in json.loads((D/'inputs.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
frozen=json.loads((D/'cli-expectations.json').read_bytes())
cases=json.loads((D/'cases.json').read_bytes())['cases']
source_expected=json.dumps(next(c['expected']['source'] for c in cases if c['id']=='EXACT'),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
assert hashlib.sha256(source_expected).hexdigest()==frozen['source']['sha256'] and len(source_expected)==frozen['source']['bytes']
R.mkdir(exist_ok=False);rows=[]
def call(args,*,error=None,output=None,expected=None):
 before={str(f):f.read_bytes() for f in D.iterdir() if f.is_file()}
 q=subprocess.run([sys.executable,'-B','-S',str(T/'tools/component_text.py'),*map(str,args)],capture_output=True,timeout=20)
 n=len(rows);(R/f'{n:02d}.stdout').write_bytes(q.stdout);(R/f'{n:02d}.stderr').write_bytes(q.stderr)
 assert q.returncode==(2 if error else 0) and not q.stderr,(args,q.returncode,q.stdout,q.stderr)
 v=json.loads(q.stdout);assert v['schema']=='bagaev-component-text/1' and v['ok'] is (error is None)
 if error:
  assert v=={'schema':'bagaev-component-text/1','ok':False,'error':{'code':error}},v
  if output is not None:assert not output.exists() and not output.is_symlink()
 else:
  raw=output.read_bytes()
  if expected is not None:assert raw==expected
  else:assert hashlib.sha256(raw).hexdigest()==frozen['form']['sha256'] and len(raw)==frozen['form']['bytes']
  assert v['result']=={'operation':str(args[0]),'source_schema':'bagaev-component-source/2','output_bytes':len(raw),'output_sha256':hashlib.sha256(raw).hexdigest(),'semantic_check':False,'execution_admission':False}
 assert all(Path(n).read_bytes()==raw for n,raw in before.items())
 rows.append({'args':list(map(str,args)),'error':error})
a=R/'source.json';b=R/'canonical.bagaev'
call(['decode',D/'StockOutcome.bagaev','--output',a],output=a,expected=source_expected)
call(['encode',a,'--output',b],output=b,expected=None)
cases=json.loads((T/'examples/probes/component-outcomes/form/cases.json').read_bytes())['cases']
for i,c in enumerate(cases):
 inp=R/f'form-{i}.bagaev';out=R/f'form-{i}.json';inp.write_text(c['text'])
 if 'error' in c['expected']:call(['decode',inp,'--output',out],error=c['expected']['error'],output=out)
 else:call(['decode',inp,'--output',out],output=out,expected=json.dumps(c['expected']['source'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
bad=[('duplicate',b'{"schema":1,"schema":1}','COMPONENT_JSON'),('float',b'1.0','COMPONENT_JSON'),('nan',b'NaN','COMPONENT_JSON'),('integer',b'9223372036854775808','COMPONENT_JSON'),('utf8',b'\xff','COMPONENT_JSON'),('deep',b'['*129+b'0'+b']'*129,'COMPONENT_BOUNDS'),('old-profile',b'{"schema":"bagaev-component-source/1"}','FORM_PROFILE')]
for name,raw,code in bad:
 inp=R/(name+'.json');out=R/(name+'.bagaev');inp.write_bytes(raw);call(['encode',inp,'--output',out],error=code,output=out)
big=R/'oversize';big.write_bytes(b' '*(1048576+1));out=R/'oversize-result';call(['decode',big,'--output',out],error='COMPONENT_BOUNDS',output=out)
out=R/'directory-result';call(['decode',R,'--output',out],error='COMPONENT_PATH',output=out)
link=R/'input-link';link.symlink_to(D/'StockOutcome.bagaev');out=R/'link-result';call(['decode',link,'--output',out],error='COMPONENT_PATH',output=out)
saved=a.read_bytes();call(['decode',D/'StockOutcome.bagaev','--output',a],error='COMPONENT_PATH');assert a.read_bytes()==saved
call(['encode',a,'--output',a],error='COMPONENT_PATH');assert a.read_bytes()==saved
outlink=R/'output-link';outlink.symlink_to(a);call(['decode',D/'StockOutcome.bagaev','--output',outlink],error='COMPONENT_PATH');assert a.read_bytes()==saved
call(['run',a,'--output',R/'not-run'],error='TOOL_USAGE')
call(['decode',D/'StockOutcome.bagaev'],error='TOOL_USAGE')
call(['decode',D/'StockOutcome.bagaev','--out',R/'abbrev'],error='TOOL_USAGE')
assert not (R/'not-run').exists() and not (R/'abbrev').exists()
base=(D/'StockOutcome.bagaev').read_bytes();limit=1048576
padded=R/'exact-limit.bagaev';padded.write_bytes(base+b' '*(limit-len(base)))
out=R/'exact-limit.json';call(['decode',padded,'--output',out],output=out,expected=source_expected)
large=R/'expanded-output.bagaev';large.write_bytes(base.replace(b'negative-quantity',b'a'*(len(b'negative-quantity')+limit-len(base))))
assert large.stat().st_size==limit
out=R/'expanded-output.json';call(['decode',large,'--output',out],error='COMPONENT_BOUNDS',output=out)
result={'status':'PASSED','cli_calls':len(rows),'expected_refusals':sum(x['error'] is not None for x in rows),'program_evaluations':0,'semantic_checker_calls':0,'rows':rows};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
