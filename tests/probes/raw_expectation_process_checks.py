"""Frozen schema2 wire reports and refusal controls; no language execution."""
import argparse,contextlib,copy,hashlib,io,json,stat,subprocess,sys
from pathlib import Path
from unittest.mock import patch
candidate=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
out=parser.parse_args().output.absolute();assert not out.resolve().is_relative_to(candidate.resolve())
frozen=candidate/'examples/probes/raw-expectations'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
canon=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
assert sha((candidate/'tools/record_run_expectation.py').read_bytes())=='b83be5be989b591ac2e43ad9de1a4af6cc24ab9681b7104d7d9db1c003fecda8'
assert sha((candidate/'tools/record_expectation_set.py').read_bytes())=='a966453730be5a1c5176b604b5c33d334cf382fb32b0f630ecbec9738a7d4eb8'
index_raw=(frozen/'index.json').read_bytes();assert sha(index_raw)=='694ed1806e0dd390136324855a3b3f36f25fd060a5c1bbb1a0c5e71dd2ee428d'
index=json.loads(index_raw);originals={p:p.read_bytes() for p in frozen.iterdir()}
closure={p:p.read_bytes() for p in candidate.rglob('*') if p.is_file()}
assert not any(p.is_symlink() for p in candidate.rglob('*'))
source_dirs={p for p in candidate.rglob('*') if p.is_dir()}
out.mkdir();directories={out};protected={};calls=[];controls=[];prepared=[]
def mkdir(path):
    path.mkdir();directories.add(path)
def save(p,raw):
    with p.open('xb') as stream:stream.write(raw)
    protected[p]=raw
for aggregate,key in [(False,'cases'),(True,'aggregate_cases')]:
    for item in index[key]:
        raw=originals[frozen/item['file']];assert sha(raw)==item['sha256'];row=json.loads(raw)
        d=out/row['name'];mkdir(d);b=d/'bundles';mkdir(b)
        bundles=row['bundles'] if aggregate else {'single':row['bundle']}
        for name,members in bundles.items():
            child=b/name;mkdir(child)
            for member,value in members.items():save(child/member,value.encode())
        e=d/'expectations';save(e,row['expectations'].encode());target=d/'report.json'
        if aggregate:
            r=d/'runs';save(r,row['runs'].encode())
            args=[str(b),'--expectations',str(e),'--expectation-sha256',sha(e.read_bytes()),
               '--runs',str(r),'--runs-sha256',sha(r.read_bytes()),'--source-sha256',row['source_sha256'],
               '--program-sha256',row['program_sha256']];tool='record_expectation_set.py'
        else:
            b=b/'single'
            args=[str(b),'--receipt-sha256',sha((b/'receipt.json').read_bytes()),'--expectations',str(e),
                  '--expectation-sha256',sha(e.read_bytes()),'--case',row['case']['id']];tool='record_run_expectation.py'
            prepared.append((row,d,b,e,args))
        command=[sys.executable,'-B','-S',str(candidate/'tools'/tool),*args,'--output',str(target)]
        cp=subprocess.run(command,cwd=d,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        save(d/'command.json',canon({'argv':command,'returncode':cp.returncode}));save(d/'stdout',cp.stdout);save(d/'stderr',cp.stderr)
        assert (cp.returncode,cp.stdout,cp.stderr)==(0,b'',b''),(row['name'],cp.stderr)
        assert target.read_bytes()==canon(row['expected_report']),row['name'];protected[target]=target.read_bytes();calls.append(row['name'])
sys.path[:0]=[str(candidate/'tools'),str(candidate/'src')]
import record_run_expectation as single
row,d,b,e,args=prepared[0];base=json.loads(row['expectations'])
def document(label,raw,expected):
    try:value=single.document(raw)
    except single.ExpectError as error:assert error.code==expected,(label,error.code)
    else:assert expected=='accepted' and value['schema']=='bagaev-record-run-expectations/2',label
    controls.append(label)
def document_case(raw,count):
    value=copy.deepcopy(base);value['cases'][0].update(arguments_raw=raw,argument_count=count);return value
with patch.object(subprocess,'Popen',side_effect=AssertionError('no runtime dispatch')):
    for control in index['document_controls']:
        document(control['id'],canon(document_case(control['arguments_raw'],control['argument_count'])),control['expected'])
    for depth in (128,129):
        wire='['*depth+'null'+']'*depth
        document('raw-depth'+str(depth),canon(document_case(wire,1)),'accepted' if depth==128 else 'EXPECT_DOCUMENT')
    for size in (1048576,1048577):
        wire=' '*(size-len('[null]'))+'[null]'
        document('raw-byte-'+str(size),canon(document_case(wire,1)),'accepted' if size==1048576 else 'EXPECT_DOCUMENT')
    document('utf8-byte-not-char',canon(document_case('["'+'é'*524288+'"]',1)),'EXPECT_DOCUMENT')
    document('huge-valid-number',canon(document_case('['+'9'*10000+']',1)),'accepted')
    altered=copy.deepcopy(base);late=copy.deepcopy(altered['cases'][0]);late.update(id='late',arguments_raw='[NaN]');altered['cases'].append(late)
    document('late-malformed',canon(altered),'EXPECT_DOCUMENT')
    altered=copy.deepcopy(base);altered['cases'][0]['arguments']=[];document('mixed-fields',canon(altered),'EXPECT_DOCUMENT')
    altered=copy.deepcopy(base);altered['schema']='bagaev-record-run-expectations/1';document('old-schema-raw-fields',canon(altered),'EXPECT_DOCUMENT')
    document('invalid-outer-utf8',b'\xff','EXPECT_DOCUMENT')
    altered=document_case('\ud800',1);document('outer-surrogate',json.dumps(altered,ensure_ascii=True).encode(),'EXPECT_DOCUMENT')

    late_document=copy.deepcopy(base);late=copy.deepcopy(base['cases'][0])
    late.update(id='late',arguments_raw='[NaN]');late_document['cases'].append(late)
    for label,invalid in [('late-before-bundle',canon(late_document)),('pinned-invalid-utf8',b'\xff')]:
        path=out/(label+'.json');save(path,invalid)
        with patch.object(single.bundle,'verify',side_effect=AssertionError('bundle accessed before document refusal')):
            try:single.verify(b,sha((b/'receipt.json').read_bytes()),path,sha(invalid),row['case']['id'])
            except single.ExpectError as error:assert error.code=='EXPECT_DOCUMENT'
            else:raise AssertionError(label)
        controls.append(label)

    # File-level bounds use the real verifier, distinct from direct document helper tests.
    raw=canon(base)
    for size in (1048576,1048577):
        path=out/('outer-'+str(size));save(path,raw+b' '*(size-len(raw)))
        try:report=single.verify(b,sha((b/'receipt.json').read_bytes()),path,sha(path.read_bytes()),row['case']['id'])
        except single.ExpectError as error:assert size==1048577 and error.code=='EXPECT_BOUNDS'
        else:
            expected=copy.deepcopy(row['expected_report']);expected['expectation_sha256']=sha(path.read_bytes())
            assert size==1048576 and report==expected
        controls.append('outer-file-'+str(size))

    # Rebind synthetic constant-result bundles for both lexical sides; never claim a fresh run.
    for number,(left,right) in enumerate(index['unequal_pairs']):
        child=out/('lexical-'+str(number));mkdir(child)
        members=copy.deepcopy(row['bundle']);receipt=json.loads(members['receipt.json'])
        arguments=left.encode();program=members['program.json'].encode()
        invocation=b'{"schema":"bagaev-typed-record-invocation/12","program":'+program+b',"arguments":'+arguments+b'}'
        members['arguments.json']=left;members['invocation.json']=invocation.decode()
        receipt.update(arguments_sha256=sha(arguments),invocation_sha256=sha(invocation));members['receipt.json']=canon(receipt).decode()
        for name,value in members.items():save(child/name,value.encode())
        for label,wire in [('equal',left),('unequal',right)]:
            path=out/('lexical-'+str(number)+'-'+label+'.json');save(path,canon(document_case(wire,1)))
            try:report=single.verify(child,sha((child/'receipt.json').read_bytes()),path,sha(path.read_bytes()),row['case']['id'])
            except single.ExpectError as error:assert label=='unequal' and error.code=='EXPECT_ARGUMENTS'
            else:assert label=='equal' and report['status']=='matched' and report['argument_comparison']=='raw-utf8'
            controls.append('lexical-'+str(number)+'-'+label)

assert all(stat.S_ISREG(p.lstat().st_mode) and p.read_bytes()==raw for p,raw in {**protected,**originals,**closure}.items())
assert all(stat.S_ISDIR(p.lstat().st_mode) for p in directories|source_dirs|{candidate,frozen})
assert not any(p.is_symlink() for p in candidate.rglob('*'))
assert {p for p in candidate.rglob('*') if p.is_dir()}==source_dirs
assert {p for p in candidate.rglob('*') if p.is_file()}==set(closure)
assert set(candidate.rglob('*'))==set(closure)|source_dirs
assert set(frozen.iterdir())==set(originals)
assert set(out.rglob('*'))==(directories-{out})|set(protected)
save(out/'evidence.json',canon({'status':'PASS','cli_cases':calls,'controls':controls,'runtime_calls':0,
 'source_preserved':True,'frozen_inputs_preserved':True,'scope':'Public synthetic consistency fixtures, not new runtime execution or authentication'}))
print('PASS',len(calls),'CLI',len(controls),'controls')
