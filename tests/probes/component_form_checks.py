"""Frozen reconstruction/refusal cases and separately reviewed component checker."""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-form'
sys.path.insert(0,str(P/'src'));import bagaev_component_form as codec
def enc(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
frozen=json.loads((D/'inputs.json').read_bytes())
for n,h in frozen['sha256'].items():assert sha((D/n).read_bytes())==h
parser=argparse.ArgumentParser(description='Exact readable component reconstruction and data-only checking in an approved bounded profile.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
reader=args.reader;R=args.output;assert reader.is_absolute() and reader.is_file() and not reader.is_symlink();assert re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
suite=json.loads((D/'cases.json').read_bytes());assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir();policy=R/'policy.json';policy.write_bytes(enc(suite['policy']));rows=[]
for case in suite['cases']:
 try:
  data=codec.decode(case['source']);error=None
 except codec.FormError as e:data=None;error=e.code
 row={'id':case['id'],'error':error}
 if 'error' in case:row['matched']=error==case['error']
 else:
  row['matched']=error is None and enc(data)==enc(case['expected_data'])
  if row['matched']:
   canonical=codec.encode(data);assert enc(codec.decode(canonical))==enc(data) and codec.encode(codec.decode(canonical))==canonical
   assert enc(codec.decode(' \n\t'+canonical.decode()))==enc(data)
   (R/(case['id']+'.bagaev')).write_bytes(canonical);f=R/(case['id']+'.json');f.write_bytes(enc(data));q=subprocess.run([str(reader),'policy',str(f),str(policy)],capture_output=True,timeout=10);(R/(case['id']+'.stdout')).write_bytes(q.stdout);assert q.returncode==0 and not q.stderr;actual=json.loads(q.stdout);row['checker_match']=enc(actual)==enc(case['expected_checker']);row['matched']&=row['checker_match'];row['canonical_source_sha256']=sha(enc(data))
 rows.append(row)
guards=[]
def refuses(name,fn,expected):
 try:fn();actual=None
 except codec.FormError as e:actual=e.code
 guards.append({'id':name,'actual':actual,'expected':expected,'matched':actual==expected})
refuses('invalid-utf8',lambda:codec.decode(b'\xff'),'FORM_SYNTAX')
refuses('BOM',lambda:codec.decode('\ufeff'+suite['cases'][0]['source']),'FORM_SYNTAX')
refuses('byte-limit',lambda:codec.decode('x'*(codec.BYTE_LIMIT+1)),'FORM_BOUNDS')
refuses('token-limit',lambda:codec.decode('bagaev component-form/1; '+'('* (codec.TOKEN_LIMIT+1)),'FORM_BOUNDS')
nested=suite['cases'][0]['source'].replace('list.unique(request.tags)','list.unique('*129+'request.tags'+')'*129)
refuses('expression-depth',lambda:codec.decode(nested),'FORM_BOUNDS')
bad=copy.deepcopy(suite['cases'][0]['expected_data']);bad['program']['functions']['main']['body']=['int',3]
refuses('unsupported-expression',lambda:codec.encode(bad),'FORM_PROFILE')
bad2=copy.deepcopy(suite['cases'][0]['expected_data']);bad2['program']['extra']=True
refuses('extra-source-field',lambda:codec.encode(bad2),'FORM_PROFILE')
cycle=[];cycle.append(cycle);refuses('cycle',lambda:codec.encode(cycle),'FORM_PROFILE')
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows+guards) else 'FAILED','rows':rows,'guards':guards,'scope':'Readable source reconstruction and actual component data checking. No host evaluation, application execution, token/model/cost claim or full-language grammar.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'cases':len(rows),'guards':len(guards),'failures':[x for x in rows+guards if not x['matched']]});assert result['status']=='PASSED'
