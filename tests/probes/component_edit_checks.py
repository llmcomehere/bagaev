"""Own bounded draft checks with the actual reviewed data-only component reader."""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-edit'
sys.path.insert(0,str(T/'src'));import bagaev_component_edit as edit
def sha(b):return hashlib.sha256(b).hexdigest()
frozen=json.loads((D/'inputs.json').read_bytes())
for n,h in frozen['sha256'].items():assert sha((D/n).read_bytes())==h
parser=argparse.ArgumentParser(description='Detached component edit checks with a separately reviewed data-only reader.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();reader=args.reader;R=args.output
assert reader.is_absolute() and reader.is_file() and not reader.is_symlink();assert re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
suite=json.loads((D/'cases.json').read_bytes());policy=edit.canonical(suite['policy']);assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir();calls=[];rows=[]
def actual_checker(source,policy_bytes):
 n=len(calls)+1;src=R/f'{n:03d}.source.json';pol=R/f'{n:03d}.policy.json';src.write_bytes(source);pol.write_bytes(policy_bytes);q=subprocess.run([str(reader),'policy',str(src),str(pol)],capture_output=True,timeout=10);(R/f'{n:03d}.stdout').write_bytes(q.stdout);(R/f'{n:03d}.stderr').write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and src.read_bytes()==source and pol.read_bytes()==policy_bytes
 calls.append({'source_sha256':sha(source),'policy_sha256':sha(policy_bytes),'output_sha256':sha(q.stdout)});return json.loads(q.stdout)
def substitute(source,policy_bytes):wire=actual_checker(source,policy_bytes);wire['source_sha256']='0'*64;return wire
def fails(*args):raise RuntimeError('controlled missing checker service')
for case in suite['cases']:
 mapping=copy.deepcopy(case['candidate_map']);before_mapping=edit.canonical(mapping);start=len(calls);checker={'actual':actual_checker,'missing':None,'substitute':substitute,'fails':fails}[case['checker']]
 try:actual=edit.draft(case['original'],case['frame'],policy,checker,candidate_map=mapping)
 except edit.EditError as e:actual={'error':e.code}
 except edit.ComponentRefused as e:actual={'error':'ComponentRefused','stage':e.stage,'reason':e.reason}
 except edit.CheckerUnavailable:actual={'error':'CheckerUnavailable'}
 except edit.form.FormError as e:actual={'error':e.code}
 assert edit.canonical(mapping)==before_mapping
 matched=edit.canonical(actual)==edit.canonical(case['expected']);rows.append({'id':case['id'],'matched':matched,'actual':copy.deepcopy(actual),'expected':case['expected'],'checker_calls':len(calls)-start})
 if actual.get('status')=='draft':
  actual['component']['program']['functions'].clear();assert edit.form.decode(json.loads(case['frame'])['source'])==case['expected']['component']
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','rows':rows,'checker_calls':calls,'scope':'New detached draft and actual data-only source/policy checks. No programme evaluation, admission, state/ledger mutation or production authority.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'matched':sum(x['matched'] for x in rows),'requested':len(rows),'checker_calls':len(calls),'failures':[x for x in rows if not x['matched']]});assert result['status']=='PASSED'
