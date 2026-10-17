"""Four frozen source workflows against a separately reviewed pinned checker."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--checker',type=Path,required=True);p.add_argument('--checker-sha256',required=True)
p.add_argument('--output',type=Path,required=True);args=p.parse_args()
binary=args.checker.resolve();out=args.output.resolve();out.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')).encode()
assert binary.is_file() and binary.stat().st_size<=33554432
assert sha(binary.read_bytes())==args.checker_sha256
cases=json.loads((root/'examples/probes/source-check-flow/cases.json').read_bytes());rows=[]
for case in cases:
    source=out/(case['name']+'.bagaev');source.write_bytes(case['source'].encode())
    target=out/case['name']
    z=subprocess.run([sys.executable,'-B','-S',str(root/'tools/record_source_check.py'),str(source),
        '--form',case['form'],'--checker',str(binary),'--checker-sha256',args.checker_sha256,'--output',str(target)],
        capture_output=True,timeout=25)
    for suffix,data in [('stdout',z.stdout),('stderr',z.stderr)]:
        with (out/(case['name']+'.'+suffix)).open('xb') as f:f.write(data)
    assert z.returncode==0 and not z.stderr,(case['name'],z.returncode,z.stderr)
    program=raw(case['ast']);verdict={'schema':'bagaev-record-source-check/'+('12' if case['form']=='6' else '11'),
        'status':case['status'],'input_sha256':sha(program),'program_sha256':sha(program) if case['status']=='checked' else None,
        'reason':case['reason'],'location':case['pointer'],'execution_admission':False}
    retained=raw(verdict)+b'\n'
    expected={'schema':'bagaev-record-check-flow/1','status':case['status'],'form':'record-form/'+case['form'],
        'source_sha256':sha(source.read_bytes()),'program_sha256':sha(program),'input_sha256':sha(program),
        'result_sha256':sha(retained),'checker_sha256':args.checker_sha256,'checker_invoked':True,'execution_admission':False}
    assert z.stdout==raw(expected)+b'\n' and (target/'receipt.json').read_bytes()==raw(expected)
    assert (target/'program.json').read_bytes()==program and (target/'checker.stdout').read_bytes()==retained
    assert (target/'checker.stderr').read_bytes()==b''
    assert source.read_bytes()==case['source'].encode()==(target/'source.bagaev').read_bytes()
    if case['status']=='refused':
        mapped=json.loads((target/'location.json').read_bytes());start=case['source'].index(case['excerpt'])
        assert mapped['excerpt']==case['excerpt'] and mapped['status']=='mapped'
        assert (mapped['location']['start_byte'],mapped['location']['end_byte'])==(start,start+len(case['excerpt']))
        assert mapped['location']['precision']=='exact-expression'
        for flag in ('semantic_check','result_authentication','execution_admission'):assert mapped[flag] is False
    else:assert not (target/'location.json').exists()
    rows.append({'case':case['name'],'status':'PASS'})
assert sha(binary.read_bytes())==args.checker_sha256
evidence={'status':'PASS','cases':rows,'workflow_processes':4,'source_only_checker_calls':4,
          'source_evaluations':0,'checker_sha256':args.checker_sha256,
          'count_scope':'one checker call per inspected successful workflow path; no independent dispatch counter'}
with (out/'evidence.json').open('x') as f:json.dump(evidence,f,indent=2)
print(json.dumps(evidence))
