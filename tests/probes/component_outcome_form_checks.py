"""Frozen form/2 cases plus exact data-reader and existing receiver composition."""
from pathlib import Path
import argparse,copy,json,hashlib,re,sys,subprocess,datetime
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-outcomes/form'
sys.path.insert(0,str(T/'src'));import bagaev_component_form as old
import bagaev_component_outcome_form as form2
sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
for n,h in json.loads((D/'inputs.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
parser=argparse.ArgumentParser(description='Explicit outcome profile with separately reviewed host executables.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();reader=args.reader;R=args.output
assert reader.is_absolute() and reader.is_file() and not reader.is_symlink() and re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
assert R.is_absolute() and R.parent.is_dir()
assert not R.exists();R.mkdir();suite=json.loads((D/'cases.json').read_bytes());rows=[]
for case in suite['cases']:
 try:
  value=form2.decode(case['text']);actual={'source':value};encoded=form2.encode(value);assert form2.decode(encoded)==value
 except form2.FormError as e:actual={'error':e.code}
 rows.append({'id':case['id'],'matched':actual==case['expected'],'actual':actual,'expected':case['expected']})
try:old.decode((D/'StockOutcome.bagaev').read_bytes());raise AssertionError('old form accepted /2')
except old.FormError as error:assert error.code==suite['legacy_refusal']
source=form2.decode((D/'StockOutcome.bagaev').read_bytes());canonical=form2.encode(source);(R/'canonical.bagaev').write_bytes(canonical);src=R/'source.json';src.write_bytes(enc(source))
policy=P/'examples/probes/component-outcomes/source/policy.json';pb=policy.read_bytes();q=subprocess.run([str(reader),'policy',str(src),str(policy)],capture_output=True,timeout=10);(R/'reader.stdout').write_bytes(q.stdout);(R/'reader.stderr').write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and src.read_bytes()==enc(source) and policy.read_bytes()==pb
wire=json.loads(q.stdout);wanted=next(x for x in json.loads((P/'examples/probes/component-outcomes/source/cases.json').read_bytes())['cases'] if x['id']=='POLICY')['expected'];assert wire==wanted
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'old_form_refuses':True,'reader':wire,'scope':'Codec is data-only; exact /2 source policy check, no execution admission or new syntax in /1.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'matched':sum(r['matched'] for r in rows),'requested':len(rows),'failures':[r for r in rows if not r['matched']]});assert result['status']=='PASSED'
