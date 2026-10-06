"""Frozen new-profile inspection with actual reader; legacy route stays separate."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parents[2];T=P;D=P/'examples/probes/component-context'
sys.path.insert(0,str(T/'src'));import bagaev_component_context as context;import bagaev_probe_context as legacy;import bagaev_component_edit as edit
def sha(b):return hashlib.sha256(b).hexdigest()
frozen=json.loads((D/'inputs.json').read_bytes())
for n,h in frozen['sha256'].items():assert sha((D/n).read_bytes())==h
suite=json.loads((D/'cases.json').read_bytes());policy=edit.canonical(suite['policy']);
parser=argparse.ArgumentParser(description='Explicit component context with separately reviewed host executables.')
parser.add_argument('--reader',required=True,type=Path);parser.add_argument('--reader-sha256',required=True);parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();reader=args.reader;R=args.output
assert reader.is_absolute() and reader.is_file() and not reader.is_symlink();assert re.fullmatch('[0-9a-f]{64}',args.reader_sha256) and sha(reader.read_bytes())==args.reader_sha256
assert R.is_absolute() and R.parent.is_dir() and not R.exists();R.mkdir();calls=[];rows=[]
def wire_checker(source,policy_bytes):
 n=len(calls)+1;f=R/f'{n:03d}.source.json';p=R/f'{n:03d}.policy.json';f.write_bytes(source);p.write_bytes(policy_bytes);q=subprocess.run([str(reader),'policy',str(f),str(p)],capture_output=True,timeout=10);(R/f'{n:03d}.stdout').write_bytes(q.stdout);(R/f'{n:03d}.stderr').write_bytes(q.stderr);assert q.returncode==0 and not q.stderr and f.read_bytes()==source and p.read_bytes()==policy_bytes;calls.append({'source_sha256':sha(source),'output_sha256':sha(q.stdout)});return json.loads(q.stdout)
def checker(programme):
 try:edit.checked(programme,policy,wire_checker,'context')
 except edit.ComponentRefused as e:raise context.ComponentRefusal(e.reason,'') from None
 except edit.CheckerUnavailable as e:raise context.ContextUnavailable(str(e)) from None
 return edit.canonical(programme)
def substitute(programme):checker(programme);return b'{}'
for case in suite['cases']:
 selected={'actual':checker,'missing':None,'substitute':substitute}[case['checker']];before=len(calls)
 try:
  if case['legacy']:actual=legacy.inspect(edit.canonical(case['context']),edit.canonical(case['expectation']),kernel_checker=selected)
  else:actual=context.inspect(edit.canonical(case['context']),edit.canonical(case['expectation']),component_checker=selected)
 except context.ContextError as e:actual={'error':e.code,'location':e.location}
 except context.ContextUnavailable:actual={'error':'ContextUnavailable'}
 except context.ComponentRefusal as e:actual={'error':'ComponentRefusal','code':e.code,'location':e.location}
 except edit.form.FormError as e:actual={'error':e.code}
 rows.append({'id':case['id'],'actual':actual,'expected':case['expected'],'matched':edit.canonical(actual)==edit.canonical(case['expected']),'data_checker_calls':len(calls)-before})
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASSED' if all(x['matched'] for x in rows) else 'FAILED','rows':rows,'data_checker_calls':calls,'scope':'New explicit component-context inspection with actual source/policy checker. No programme/model execution, capability restoration or admission.'};(R/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({'status':result['status'],'matched':sum(x['matched'] for x in rows),'requested':len(rows),'data_checker_calls':len(calls),'failures':[x for x in rows if not x['matched']]});assert result['status']=='PASSED'
