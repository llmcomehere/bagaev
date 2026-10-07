"""Complete frozen /2 checker wires through the reviewed data-only executable."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,datetime
P=Path(__file__).resolve().parents[2];D=P/'examples/probes/component-outcomes/source';sha=lambda b:hashlib.sha256(b).hexdigest()

for n,h in json.loads((D/'inputs.json').read_bytes())['sha256'].items():assert sha((D/n).read_bytes())==h
parser=argparse.ArgumentParser(description='Explicit outcome profile with separately reviewed host executables.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();reader=args.reader;R=args.output
assert reader.is_absolute() and reader.is_file() and not reader.is_symlink() and re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
assert R.is_absolute() and R.parent.is_dir()
assert not R.exists();R.mkdir();rows=[]
for i,c in enumerate(json.loads((D/'cases.json').read_bytes())['cases']):
 source=json.dumps(c['source'],sort_keys=True,separators=(',',':')).encode();s=R/f'{i:02d}.source.json';s.write_bytes(source);args=[str(reader),'check',str(s)];inputs=[(s,source)]
 if c['policy'] is not None:
  policy=json.dumps(c['policy'],sort_keys=True,separators=(',',':')).encode();p=R/f'{i:02d}.policy.json';p.write_bytes(policy);args=[str(reader),'policy',str(s),str(p)];inputs.append((p,policy))
 q=subprocess.run(args,capture_output=True,timeout=10);(R/f'{i:02d}.stdout').write_bytes(q.stdout);(R/f'{i:02d}.stderr').write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and all(f.read_bytes()==v for f,v in inputs);actual=json.loads(q.stdout);rows.append({'id':c['id'],'matched':actual==c['expected'],'actual':actual,'expected':c['expected'],'input_sha256':[sha(v) for _,v in inputs],'output_sha256':sha(q.stdout)})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(r['matched'] for r in rows) else 'FAILED','rows':rows,'reader_sha256':sha(reader.read_bytes()),'scope':'Explicit /2 source+policy data checking only; no application evaluation, receiver/2, readable form/2 or production authority.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'matched':sum(r['matched'] for r in rows),'requested':len(rows),'failures':[r for r in rows if not r['matched']]});assert result['status']=='PASSED'
