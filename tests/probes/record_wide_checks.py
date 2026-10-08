from pathlib import Path
import json,hashlib,subprocess,copy,argparse,re
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/record-wide'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
for name in ('reference','legacy'):
 p.add_argument('--'+name,required=True,type=Path);p.add_argument('--'+name+'-sha256',required=True)
a=p.parse_args();R=a.output;assert R.is_absolute() and R.parent.is_dir() and not R.exists()
for name in ('reference','legacy'):
 f=getattr(a,name);h=getattr(a,name+'_sha256');assert f.is_absolute() and f.is_file() and not f.is_symlink() and re.fullmatch('[0-9a-f]{64}',h);assert hashlib.sha256(f.read_bytes()).hexdigest()==h
R.mkdir(exist_ok=False);ref=a.reference;old=a.legacy
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h

canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
rows=[]
def run(ident,program,args,exe=ref,version=11):
 f=R/(ident+'.json');data=canonical({'schema':f'bagaev-typed-record-invocation/{version}','program':program,'arguments':args}).encode();f.write_bytes(data);q=subprocess.run([str(exe),'run','--input',str(f)],capture_output=True,timeout=20);assert q.returncode==0 and not q.stderr and f.read_bytes()==data;wire=json.loads(q.stdout);assert wire['schema']==f'bagaev-typed-record-result/{version}';(R/(ident+'.stdout')).write_bytes(q.stdout);rows.append(ident);return wire
cases=json.loads((D/'cases.json').read_bytes())
for c in cases:
 v=run(c['id'],c['program'],c['arguments'])
 if 'reason' in c:assert v['reason']==c['reason'] and v['value'] is None,(c['id'],v)
 else:assert v['status']=='success' and canonical(v['value'])==canonical(c['value']),(c['id'],v)
legacy=copy.deepcopy(cases[0]['program']);legacy['schema']='bagaev-typed-record/10';v=run('old-capacity',legacy,[],old,10);assert v['reason']=='RR_BOUNDS'
base=json.loads((T/'examples/probes/pure-json-form/program.json').read_bytes());base['schema']='bagaev-typed-record/11';oracle_raw=(T/'examples/beta/catalog-cases.json').read_bytes();assert hashlib.sha256(oracle_raw).hexdigest()==(T/'examples/probes/pure-json-form/oracle-sha256.txt').read_text().strip();oracle=json.loads(oracle_raw)
for c in oracle['cases']:
 v=run('catalog-'+c['id'],base,[oracle['requests'][c['request']]]);expected=oracle['responses'][c['expect']];assert v['status']=='success' and v['value']['case']==('Ok' if expected['kind']=='success' else 'Error') and canonical(v['value']['value'])==canonical(expected),(c['id'],v)
r={'status':'PASSED','new_cases':7,'legacy_capacity_refusals':1,'catalog_cases':99,'reference_calls':len(rows),'profile11_calls':len(rows)-1};(R/'result.json').write_text(json.dumps(r)+'\n');print(r)
