"""Standalone compiler CLI checks. Does not execute generated artifacts."""
import argparse,hashlib,json,os,stat,subprocess,sys
from pathlib import Path
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--checker',required=True)
    parser.add_argument('--checker-sha256',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2];out=Path(args.output).absolute()
    assert not out.resolve().is_relative_to(root),'test output must be outside source tree'
    checker=Path(args.checker).absolute();assert stat.S_ISREG(checker.lstat().st_mode)
    checker_bytes=checker.read_bytes();assert sha(checker_bytes)==args.checker_sha256
    assert sys.dont_write_bytecode and not sys.flags.optimize
    paths=list(root.rglob('*'));kinds={p:stat.S_IFMT(p.lstat().st_mode) for p in paths}
    assert all(k in (stat.S_IFREG,stat.S_IFDIR) for k in kinds.values())
    held={p:p.read_bytes() for p in paths if p.is_file()}
    out.mkdir();empty=out/'empty';empty.mkdir();logs=out/'logs';logs.mkdir()
    protected={};directories={empty,logs};calls=[]
    def save(p,b):
        with p.open('xb') as f:f.write(b)
        protected[p]=b
    def call(label,arguments,code=0,stdout=None,stderr=b''):
        argv=[sys.executable,'-B','-S',str(root/'tools/record_cpython_compile.py'),*map(str,arguments)]
        cp=subprocess.run(argv,cwd=empty,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
        save(logs/(label+'.stdout'),cp.stdout);save(logs/(label+'.stderr'),cp.stderr)
        save(logs/(label+'.json'),canon({'returncode':cp.returncode}))
        assert cp.returncode==code and cp.stderr==stderr,(label,cp.returncode,cp.stderr)
        if stdout is not None:assert cp.stdout==stdout,(label,cp.stdout)
        calls.append(label);return cp.stdout
    help_raw=b'''Compile authored form5/profile11 source to a deterministic CPython artifact.
Usage: python -B -S tools/record_cpython_compile.py SOURCE --source-sha256 SHA256 --checker PATH --checker-sha256 SHA256 --output NEW_DIRECTORY
Requires a fresh Python process with -B -S and assertions enabled.
Compilation invokes the explicit pinned checker; generated Python is not executed.
Pins and retained receipts do not grant execution authority.
'''
    call('help',['--help'],stdout=help_raw)
    call('short-help',['-h'],stdout=help_raw)
    for label,argv in [('empty',[]),('unknown',['--execute']),('missing',['x']),('abbreviated',['x','--source-sha','0'*64,'--checker','x','--checker-sha256','0'*64,'--output',out/'unexpected'])]:
        call(label,argv,2,b'',b'CPY_USAGE\n')
    source=root/'examples/probes/cpython/constant.bagaev'
    refused=root/'examples/probes/cpython/type-refused.bagaev'
    def options(src,target,sp=None,cp=None):
        return [src,'--source-sha256',sp or sha(held[src]),'--checker',checker,
          '--checker-sha256',cp or args.checker_sha256,'--output',target]
    records=[]
    for label in ('compile-one','compile-two'):
        target=out/label;raw=call(label,options(source,target));receipt=json.loads(raw)
        directories.add(target)
        expected_members={'source.bagaev','program.json','checker.stdout','checker.stderr','artifact.json','receipt.json'}
        assert {p.name for p in target.iterdir()}==expected_members
        for p in target.iterdir():assert stat.S_ISREG(p.lstat().st_mode);protected[p]=p.read_bytes()
        assert (target/'source.bagaev').read_bytes()==held[source]
        program=canon({'schema':'bagaev-typed-record/11','records':{},'lists':{},'variants':{},'entry':'main',
          'functions':{'main':{'params':[],'result':'Int64','body':['int',7]}}})
        assert (target/'program.json').read_bytes()==program
        report=json.loads((target/'checker.stdout').read_bytes())
        assert report=={'schema':'bagaev-record-source-check/11','status':'checked','input_sha256':sha(program),
          'program_sha256':sha(program),'reason':None,'location':None,'execution_admission':False}
        assert (target/'checker.stderr').read_bytes()==b''
        artifact_raw=(target/'artifact.json').read_bytes();artifact=json.loads(artifact_raw)
        assert set(artifact)=={'schema','profile','program_sha256','generator_sha256','runtime_sha256','python'}
        assert artifact['schema']=='bagaev-record-cpython/1' and artifact['profile']=='bagaev-typed-record/11'
        assert artifact['program_sha256']==sha(program) and artifact_raw==canon(artifact)
        expected={'schema':'bagaev-record-cpython-compile/1','status':'compiled','form':'record-form/5',
          'source_sha256':sha(held[source]),'program_sha256':sha(program),'checker_sha256':args.checker_sha256,
          'artifact_sha256':sha(artifact_raw),'python_sha256':sha(artifact['python'].encode()),
          'generator_sha256':artifact['generator_sha256'],'runtime_sha256':artifact['runtime_sha256'],
          'checker_invoked':True,'generated_code_executed':False,'execution_admission':False}
        assert receipt==expected and raw==canon(expected)+b'\n' and (target/'receipt.json').read_bytes()==canon(expected)
        records.append((artifact_raw,raw))
    assert records[0]==records[1]
    for label,sp,cp in [('wrong-source','0'*64,None),('wrong-checker',None,'0'*64)]:
        target=out/label;call(label,options(source,target,sp,cp),1,b'',b'CPY_PIN\n');assert not target.exists()
    call('existing-output',options(source,out/'compile-one'),1,b'',b'CPY_OUTPUT\n')
    target=out/'type-refused';call('type-refused',options(refused,target),1,b'',b'CPY_CHECK_REFUSED\n')
    directories.add(target)
    assert {p.name for p in target.iterdir()}=={'source.bagaev','program.json','checker.stdout','checker.stderr'}
    for p in target.iterdir():assert stat.S_ISREG(p.lstat().st_mode);protected[p]=p.read_bytes()
    report=json.loads((target/'checker.stdout').read_bytes())
    assert report['status']=='refused' and report['reason']=='RR_TYPE' and report['location']=='/functions/main/body'
    assert report['program_sha256'] is None and report['input_sha256']==sha((target/'program.json').read_bytes())
    assert (target/'checker.stderr').read_bytes()==b''
    target=out/'broken-delivery'
    # Close the reader before spawning: receipt writes deterministically fail.
    reader,writer=os.pipe();os.close(reader)
    try:
        cp=subprocess.run([sys.executable,'-B','-S',str(root/'tools/record_cpython_compile.py'),*map(str,options(source,target))],
          cwd=empty,stdin=subprocess.DEVNULL,stdout=writer,stderr=subprocess.PIPE,timeout=45)
    finally:os.close(writer)
    assert cp.returncode==1 and cp.stderr==b'CPY_DELIVERY\n',(cp.returncode,cp.stderr)
    calls.append('broken-delivery');directories.add(target);save(logs/'broken-delivery.stderr',cp.stderr)
    assert {p.name for p in target.iterdir()}==expected_members
    for p in target.iterdir():
        assert stat.S_ISREG(p.lstat().st_mode) and p.read_bytes()==(out/'compile-one'/p.name).read_bytes()
        protected[p]=p.read_bytes()
    assert len(calls)==13
    assert {p:stat.S_IFMT(p.lstat().st_mode) for p in root.rglob('*')}==kinds
    assert all(p.read_bytes()==b for p,b in {**held,**protected}.items()) and checker.read_bytes()==checker_bytes
    assert not list(empty.iterdir()) and stat.S_ISDIR(out.lstat().st_mode)
    assert {p:stat.S_IFMT(p.lstat().st_mode) for p in out.rglob('*')}=={
      **{p:stat.S_IFDIR for p in directories},**{p:stat.S_IFREG for p in protected}}
    save(out/'evidence.json',canon({'status':'PASS','cli_cases':calls,'checker_calls':4,
      'generated_program_invocations':0,'source_preserved':True,
      'scope':'Two delivered deterministic compiles, one actual semantic refusal and one successful compile with broken stdout delivery; invocation counts follow inspected paths, not OS tracing. No generated execution or execution admission.'}))
    print('PASS 13 CLI cases,4 checker calls,0 generated execution')
if __name__=='__main__':main()
