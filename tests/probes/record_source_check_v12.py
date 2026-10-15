"""Explicit /12 checker qualification plus byte-identical /11 default replay."""
from pathlib import Path
import argparse,copy,hashlib,json,re,subprocess,sys
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description='Requires separate checker review/execution authority.')
parser.add_argument('--checker',type=Path,required=True)
parser.add_argument('--checker-sha256',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();binary=args.checker.resolve();out=args.output.resolve()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
assert binary.is_file() and binary.stat().st_size<=33554432
assert re.fullmatch('[0-9a-f]{64}',args.checker_sha256)
pin=sha(binary.read_bytes());assert pin==args.checker_sha256
out.mkdir(exist_ok=False)
def run(args,name,timeout=20):
    z=subprocess.run(list(map(str,args)),capture_output=True,timeout=timeout)
    for suffix,data in [('stdout',z.stdout),('stderr',z.stderr)]:
        with (out/(name+'.'+suffix)).open('xb') as f:f.write(data)
    assert z.returncode==0,(name,z.returncode,z.stderr[-2000:])
    if name!='build':assert not z.stderr
    return z.stdout
run([sys.executable,'-B','-S',root/'tests/probes/record_source_check_v11.py',
    '--checker',binary,'--checker-sha256',pin,'--output',out/'old-default'],'old-default',90)
base={'schema':'bagaev-typed-record/12','records':{},'lists':{},'variants':{},'entry':'main',
      'functions':{'main':{'params':[['x','Json']],'result':'Bool','body':['json.bool_or',['arg','x'],['bool',False]]}}}
cases=[]
def add(name,program,profile=12,reason=None,location=None):cases.append((name,program,profile,reason,location))
add('bool-projection',base)
add('wrong-default',base,11,'RR_VERSION','/schema')
old=copy.deepcopy(base);old['schema']='bagaev-typed-record/11'
add('wrong-explicit',old,12,'RR_VERSION','/schema')
add('unsupported-old-op',old,11,'RR_SHAPE','/functions/main/body')
bad=copy.deepcopy(base);bad['functions']['main']['body'][2]=['int',0]
add('fallback-type',bad,12,'RR_TYPE','/functions/main/body/2')
bad=copy.deepcopy(base);bad['functions']['bad']={'params':[],'result':'Int64','body':['bool',True]}
add('unused-type',bad,12,'RR_TYPE','/functions/bad/body')
integer=copy.deepcopy(base);integer['functions']={'main':{'params':[['n','Int64']],'result':'Int64','body':['arg','n']}}
add('non-json-signature',integer)
sys.path.insert(0,str(root/'src'))
import bagaev_record_json_bool_form as form
source=root/'examples/probes/json-active-total/ActiveJson.bagaev'
raw=source.read_bytes();assert sha(raw)=='379ccce2b4f6bb0125ef73eed18eacac50b48b5419a55d0178a0a6b98de7a363'
add('active-json',form.decode(raw))
rows=[]
for name,program,profile,reason,location in cases:
    raw_program=canon(program);path=out/(name+'.json')
    with path.open('xb') as f:f.write(raw_program)
    args=[binary,'check']+(['--profile','12'] if profile==12 else [])+['--input',path]
    actual=run(args,name)
    expected={'execution_admission':False,'input_sha256':sha(raw_program),'location':location,
              'program_sha256':None if reason else sha(raw_program),'reason':reason,
              'schema':'bagaev-record-source-check/'+str(profile),'status':'refused' if reason else 'checked'}
    assert actual==canon(expected)+b'\n',(name,actual,expected)
    assert path.read_bytes()==raw_program
    rows.append({'case':name,'status':'PASS'})
assert source.read_bytes()==raw and sha(binary.read_bytes())==pin
result={'status':'PASS','profile_cases':rows,'old_default_verdicts':13,'old_default_io_controls':2,
        'binary_sha256':pin,'source_evaluations':0}
with (out/'evidence.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
