"""Portable revision/decode/check/location process chain. Separate execution authority required."""
import argparse,copy,hashlib,json,re,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--checker',type=Path,required=True)
parser.add_argument('--checker-sha256',required=True)
parser.add_argument('--diagnostic-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();binary=args.checker.resolve();diagnostics=args.diagnostic_root.resolve()
out=args.output.resolve()
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
assert re.fullmatch('[0-9a-f]{64}',args.checker_sha256)
assert binary.is_file() and binary.stat().st_size<=33554432
assert sha(binary.read_bytes())==args.checker_sha256
assert (diagnostics/'tools/record_check_location.py').is_file()
out.mkdir(exist_ok=False);calls=[];preserved={}
def write(name,data):
    path=out/name
    with path.open('xb') as f:f.write(data)
    preserved[path]=data;return path
def run(name,argv,code=0,stderr=None):
    z=subprocess.run(list(map(str,argv)),capture_output=True,timeout=15)
    write(name+'.stdout',z.stdout);write(name+'.stderr',z.stderr)
    assert z.returncode==code,(name,z.returncode,z.stderr)
    if stderr is not None:assert z.stderr==stderr and not z.stdout
    else:assert not z.stderr
    calls.append(name);return z.stdout
def py(name,base,tool,argv,code=0,stderr=None):
    return run(name,[sys.executable,'-B','-S',base/'tools'/tool,*argv],code,stderr)
sources=[b'bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = json.bool_or(x, false); }',
         b'bagaev record-form/6; program { entry main; fn main(x: Json) -> Bool = json.bool_or(x, 0); }']
asts=[]
for literal in [['bool',False],['int',0]]:
    asts.append({'schema':'bagaev-typed-record/12','records':{},'lists':{},'variants':{},'entry':'main',
      'functions':{'main':{'params':[['x','Json']],'result':'Bool','body':['json.bool_or',['arg','x'],literal]}}})
paths=[write('first.bagaev',sources[0]),write('second.bagaev',sources[1])]
packages=[out/'first.package.json',out/'second.package.json'];ids=[]
for i in range(2):
    pins=['--source-sha256',sha(sources[i]),'--program-sha256',sha(canon(asts[i]))]
    argv=['init',paths[i]] if i==0 else ['append',packages[0],'--source',paths[1],
      '--package-sha256',sha(packages[0].read_bytes()),'--head',ids[0]]
    py('history-'+str(i),root,'record_revisions.py',argv+['--form','6','--output',packages[i],*pins])
    raw=packages[i].read_bytes();preserved[packages[i]]=raw
    identity={'form':'record-form/6','parent':None if i==0 else ids[0],
              'source_sha256':sha(sources[i]),'program_sha256':sha(canon(asts[i]))}
    ids.append(sha(canon(identity)));assert json.loads(raw)['head']==ids[i]
for i in range(2):
    selected=out/('checkout-'+str(i)+'.bagaev');program=out/('program-'+str(i)+'.json')
    py('checkout-'+str(i),root,'record_revisions.py',['checkout',packages[1],'--form','6','--revision',ids[i],'--output',selected])
    assert selected.read_bytes()==sources[i];preserved[selected]=sources[i]
    receipt=json.loads(py('decode-'+str(i),root,'record_text.py',['decode',selected,'--form','6','--output',program]))
    assert receipt['ok'] and receipt['result']['semantic_check'] is False
    assert program.read_bytes()==canon(asts[i]);preserved[program]=canon(asts[i])
    result=run('check-'+str(i),[binary,'check','--profile','12','--input',program])
    expected={'schema':'bagaev-record-source-check/12','status':'checked' if i==0 else 'refused',
        'input_sha256':sha(canon(asts[i])),'program_sha256':sha(canon(asts[i])) if i==0 else None,
        'reason':None if i==0 else 'RR_TYPE','location':None if i==0 else '/functions/main/body/2','execution_admission':False}
    assert result==canon(expected)+b'\n'
location=out/'location.json'
py('locate',diagnostics,'record_check_location.py',[out/'checkout-1.bagaev','--form','6',
    '--checked-input',out/'program-1.json','--result',out/'check-1.stdout','--output',location,
    '--source-sha256',sha(sources[1]),'--program-sha256',sha(canon(asts[1])),
    '--input-sha256',sha(canon(asts[1])),'--result-sha256',sha((out/'check-1.stdout').read_bytes())])
mapped=json.loads(location.read_bytes());preserved[location]=location.read_bytes();start=sources[1].index(b'0')
assert mapped['schema']=='bagaev-record-check-location/2' and mapped['status']=='mapped' and mapped['excerpt']=='0'
assert (mapped['location']['start_byte'],mapped['location']['end_byte'])==(start,start+1)
assert mapped['location']['precision']=='exact-expression'
for flag in ('semantic_check','result_authentication','execution_admission'):assert mapped[flag] is False
bad=copy.deepcopy(json.loads(packages[1].read_bytes()));bad['revisions'][1]['source']='tampered'
tampered=write('tampered.json',canon(bad));missing=out/'must-not-exist.bagaev'
py('late-tamper',root,'record_revisions.py',['checkout',tampered,'--form','6','--revision',ids[0],'--output',missing],1,b'REVISION_SOURCE_PIN\n')
assert not missing.exists()
py('existing-output',root,'record_revisions.py',['checkout',packages[1],'--form','6','--revision',ids[0],'--output',out/'checkout-0.bagaev'],1,b'RECORD_PATH\n')
assert all(path.read_bytes()==raw for path,raw in preserved.items())
assert sha(binary.read_bytes())==args.checker_sha256
evidence={'status':'PASS','process_calls':calls,'checker_calls':2,'source_evaluations':0,
          'revision_ids':ids,'checker_sha256':args.checker_sha256,
          'scope':'two portable revisions; checked versus type-refused source; actual diagnostic; late-tamper and existing-output refusals'}
write('evidence.json',json.dumps(evidence,indent=2).encode());print(json.dumps(evidence))
