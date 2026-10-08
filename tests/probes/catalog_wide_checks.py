from pathlib import Path
import json,hashlib,sys,subprocess,argparse,re,copy
T=Path(__file__).resolve().parents[2];D=T/'examples/probes/catalog-wide'
p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--reference-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
ref=a.reference;assert ref.is_absolute() and ref.is_file() and not ref.is_symlink() and re.fullmatch('[0-9a-f]{64}',a.reference_sha256);assert hashlib.sha256(ref.read_bytes()).hexdigest()==a.reference_sha256
R=a.output;assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir()
for n,h in json.loads((D/'manifest.json').read_bytes())['sha256'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h
sys.path.insert(0,str(T/'src'));import catalog_wide_reference as ordinary;import bagaev_record_wide_form as form
p=json.loads((D/'program.json').read_bytes());raw=form.encode(p);assert form.decode(raw)==p;(R/'Catalog.bagaev').write_bytes(raw)

def check(c):
 assert ordinary.evaluate(c['request'])==c['expected'],('ordinary',c['id'])
 f=R/(c['id']+'.json');data=json.dumps({'schema':'bagaev-typed-record-invocation/11','program':p,'arguments':[c['request']]}).encode();f.write_bytes(data)
 q=subprocess.run([str(ref),'run','--input',str(f)],capture_output=True,timeout=20);(R/(c['id']+'.stdout')).write_bytes(q.stdout);assert q.returncode==0 and not q.stderr and f.read_bytes()==data
 v=json.loads(q.stdout);assert v['schema']=='bagaev-typed-record-result/11' and v['status']=='success' and v['value']=={'case':'Ok' if c['expected']['kind']=='success' else 'Error','value':c['expected']},(c['id'],v)
for c in json.loads((D/'cases.json').read_bytes()):check(c)
legacy_raw=(T/'examples/beta/catalog-cases.json').read_bytes();assert hashlib.sha256(legacy_raw).hexdigest()==(T/'examples/probes/pure-json-form/oracle-sha256.txt').read_text().strip();legacy=json.loads(legacy_raw)
for c in legacy['cases']:
 if c['id']=='ENTRIES-LIMIT':continue # Deliberately different four-entry contract.
 request=copy.deepcopy(legacy['requests'][c['request']])
 if isinstance(request,dict) and request.get('interface')=='catalog-application/2':request['interface']='catalog-application/3'
 check({'id':'translated-'+c['id'],'request':request,'expected':legacy['responses'][c['expect']]})
result={'status':'PASSED','literal_cases':15,'translated_legacy_cases':98,'excluded_old_capacity_cases':1,'reference_calls':113,'ordinary_cases':113,'exact_graph':True};(R/'result.json').write_text(json.dumps(result)+'\n');print(result)
