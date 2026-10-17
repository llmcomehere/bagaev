"""Portable retained-run checks using separately authorized pinned references."""
import argparse,hashlib,json,stat,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser()
for profile in ('11','12'):
    p.add_argument('--reference'+profile,type=Path,required=True)
    p.add_argument('--reference'+profile+'-sha256',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();out=a.output.absolute()
assert not out.resolve().is_relative_to(ROOT.resolve());out.mkdir()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canon=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
references={11:a.reference11.absolute(),12:a.reference12.absolute()}
pins={11:a.reference11_sha256,12:a.reference12_sha256}
assert all(stat.S_ISREG(path.lstat().st_mode) and sha(path.read_bytes())==pins[profile] for profile,path in references.items())
fixture_pins={'source-run-flow':'366cfe976c889a0c2b92cd55bd24a0e07441a458819547f392ebd36d94fd829a',
 'source-run-form6':'5dd8ec793309056d0d27f99b5b8b276d3cf16371e6067104892b50d1ceae9ed6'}
data={}
for name,pin in fixture_pins.items():
    raw=(ROOT/'examples/probes'/name/'cases.json').read_bytes();assert sha(raw)==pin;data[name]=json.loads(raw)
assert sha((ROOT/'tools/record_source_run.py').read_bytes())=='4bf78e4f6026d12a5b60db7e3d1cdf8654f31ad85f979f149b9334611bb3cc3a'
assert sha((ROOT/'tools/record_run_verify.py').read_bytes())=='f505e8f99925de4b556c2505592d0c66e537a46994869bb67383d8c0083739aa'
before={path:path.read_bytes() for path in ROOT.rglob('*') if path.is_file()}
assert not any(path.is_symlink() for path in ROOT.rglob('*'))
protected={};calls=[];default_outputs={};bundle_files={}
def save(path,raw):
    with path.open('xb') as stream:stream.write(raw)
    protected[path]=raw
def call(label,tool,args,stdout):
    command=[sys.executable,'-B','-S',str(ROOT/'tools'/tool),*map(str,args)]
    cp=subprocess.run(command,cwd=out,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    save(out/(label+'-command.json'),canon({'argv':command,'returncode':cp.returncode}))
    save(out/(label+'-stdout'),cp.stdout);save(out/(label+'-stderr'),cp.stderr)
    assert (cp.returncode,cp.stdout,cp.stderr)==(0,stdout,b''),(label,cp.returncode,cp.stderr)
    calls.append(label)
for mode,form,profile,cases in [('default5',None,11,data['source-run-flow']['real_cases']),
 ('explicit5','5',11,data['source-run-flow']['real_cases']),('explicit6','6',12,data['source-run-form6']['cases'])]:
    for case in cases:
        label=mode+'-'+case['name'];source=out/(label+'.bagaev');arguments=out/(label+'-arguments.json')
        save(source,case['source'].encode());save(arguments,case['arguments'].encode())
        program=canon(case['program']);result=case['expected'];stdout=canon(result)+b'\n'
        invocation=b'{"schema":"bagaev-typed-record-invocation/'+str(profile).encode()+b'","program":'+program+b',"arguments":'+arguments.read_bytes()+b'}'
        receipt={'schema':'bagaev-record-source-run/'+('1' if profile==11 else '2'),'status':'completed',
         'source_sha256':sha(source.read_bytes()),'arguments_sha256':sha(arguments.read_bytes()),
         'program_sha256':sha(program),'invocation_sha256':sha(invocation),'result_sha256':sha(stdout),
         'reference_sha256':pins[profile],'runtime_status':result['status'],'reason':result['reason'],
         'location':result['location'],'work':result['work'],'reference_invoked':True,
         'execution_admission':False,'result_authentication':False,'application_expectation_checked':False}
        if profile==12:receipt['form']='record-form/6'
        target=out/(label+'-bundle');args=[source,'--source-sha256',receipt['source_sha256'],
          '--arguments',arguments,'--arguments-sha256',receipt['arguments_sha256'],
          '--reference',references[profile],'--reference-sha256',pins[profile],'--output',target]
        if form:args+=['--form',form]
        call(label+'-run','record_source_run.py',args,canon(receipt)+b'\n')
        files={'source.bagaev':source.read_bytes(),'arguments.json':arguments.read_bytes(),'program.json':program,
          'invocation.json':invocation,'reference.stdout':stdout,'reference.stderr':b'','receipt.json':canon(receipt)}
        assert {path.name for path in target.iterdir()}==set(files)
        bundle_files[target]=files
        for member,raw in files.items():
            path=target/member;assert stat.S_ISREG(path.lstat().st_mode) and path.read_bytes()==raw;protected[path]=raw
        if mode=='default5':default_outputs[case['name']]=files
        if mode=='explicit5':assert files==default_outputs[case['name']]
        report={'schema':'bagaev-record-run-verification/'+('1' if profile==11 else '2'),'status':'consistent',
          'receipt_sha256':sha(files['receipt.json']),**{key:receipt[key] for key in ('source_sha256','arguments_sha256','program_sha256','invocation_sha256','result_sha256')},
          'claimed_reference_sha256':pins[profile],'runtime_status':result['status'],'reason':result['reason'],
          'location':result['location'],'work':result['work'],'fresh_run':False,'reference_invoked':False,
          'result_authentication':False,'execution_admission':False,'application_expectation_checked':False}
        if profile==12:report['form']='record-form/6'
        report_path=out/(label+'-verified.json')
        call(label+'-verify','record_run_verify.py',[target,'--receipt-sha256',report['receipt_sha256'],'--output',report_path],b'')
        assert report_path.read_bytes()==canon(report);protected[report_path]=report_path.read_bytes()
assert len(calls)==82 and len(default_outputs)==7
assert all(stat.S_ISREG(path.lstat().st_mode) and path.read_bytes()==raw for path,raw in {**before,**protected}.items())
for directory,expected in bundle_files.items():
    assert stat.S_ISDIR(directory.lstat().st_mode)
    assert {path.name for path in directory.iterdir()}==set(expected)
    assert all(stat.S_ISREG((directory/name).lstat().st_mode) and (directory/name).read_bytes()==raw for name,raw in expected.items())
assert not any(path.is_symlink() for path in ROOT.rglob('*'))
assert {path for path in ROOT.rglob('*') if path.is_file()}==set(before)
assert all(stat.S_ISREG(path.lstat().st_mode) and sha(path.read_bytes())==pins[profile] for profile,path in references.items())
save(out/'evidence.json',canon({'status':'PASS','cli_calls':82,'reference_calls':41,'profile11_calls':14,
 'profile12_calls':27,'offline_verifications':41,'default_explicit_form5_identical':True,
 'source_and_inputs_preserved':True,'scope':'Selected functional replay; counts follow inspected routing, no timing, authentication, admission or universal equivalence claim.'}))
print('PASS 82 CLI;41 reference calls and41 offline verifications')
