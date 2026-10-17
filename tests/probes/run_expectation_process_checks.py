"""Portable single-case expectation controls with synthetic fixtures. No runtime calls."""
import argparse,contextlib,copy,hashlib,io,json,stat,subprocess,sys
from pathlib import Path
from unittest.mock import patch
candidate=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
out=parser.parse_args().output.absolute()
assert not out.resolve().is_relative_to(candidate.resolve())
source=candidate/'tools/record_run_expectation.py';assert hashlib.sha256(source.read_bytes()).hexdigest()=='b83be5be989b591ac2e43ad9de1a4af6cc24ab9681b7104d7d9db1c003fecda8'
sha=lambda b:hashlib.sha256(b).hexdigest();canon=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
frozen=candidate/'examples/probes/run-expectations';fixtures=json.loads((frozen/'cases.json').read_bytes())
# Exact frozen hashes are added after separately reviewed data-only freeze.
assert sha((frozen/'cases.json').read_bytes())=='4c83df9ed7a63361bcaf1e2ca34c6266eb165ee63d34aa7d2ecfc08a36fb568c'
frozen_before={p:p.read_bytes() for p in frozen.iterdir()}
closure={p:p.read_bytes() for p in candidate.rglob('*') if p.is_file()};assert not any(p.is_symlink() for p in candidate.rglob('*'))
source_dirs={p for p in candidate.rglob('*') if p.is_dir()}
out.mkdir();directories={out};protected={};calls=[];controls=[];bundle_names={};links={}
def save(path,raw):
 with path.open('xb') as f:f.write(raw)
 protected[path]=raw
sys.path.insert(0,str(candidate/'tools'));sys.path.insert(0,str(candidate/'src'))
import record_run_expectation as tool

def prepare(row,name):
 d=out/name;d.mkdir();b=d/'bundle';b.mkdir();directories.update((d,b))
 for filename,value in row['bundle'].items():save(b/filename,value.encode())
 bundle_names[b]=set(row['bundle'])
 spec=d/'expectations.json';save(spec,canon(row['expectation']))
 return d,b,spec
prepared=[]
for i,row in enumerate(fixtures):
 d,b,spec=prepare(row,'case'+str(i));prepared.append((row,d,b,spec))
 args=[str(b),'--receipt-sha256',sha((b/'receipt.json').read_bytes()),'--expectations',str(spec),'--expectation-sha256',sha(spec.read_bytes()),'--case',row['expected_report']['case'],'--output',str(d/'report.json')]
 command=[sys.executable,'-B','-S',str(source),*args]
 cp=subprocess.run(command,cwd=d,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 save(d/'command.json',canon({'argv':command,'returncode':cp.returncode}));save(d/'stdout',cp.stdout);save(d/'stderr',cp.stderr)
 assert cp.returncode==0 and cp.stdout==cp.stderr==b''
 actual=(d/'report.json').read_bytes();assert actual==canon(row['expected_report']);protected[d/'report.json']=actual;calls.append(row['name'])
row,d,b,spec=prepared[0];receipt=sha((b/'receipt.json').read_bytes());base=row['expectation']
def invoke(document=None,raw=None,code=None,case=None,pin=None,receipt_pin=None,output=None,bundle_path=None,label='control',expected_status='matched'):
 index=len(controls);path=out/('input'+str(index)+'.json')
 if raw is None:raw=canon(base if document is None else document)
 save(path,raw);target=out/('report-control'+str(index)+'.json') if output is None else output
 arguments=[str(b if bundle_path is None else bundle_path),'--receipt-sha256',receipt if receipt_pin is None else receipt_pin,'--expectations',str(path),'--expectation-sha256',sha(raw) if pin is None else pin,'--case',base['cases'][0]['id'] if case is None else case,'--output',str(target)]
 stdout=io.StringIO();stderr=io.StringIO()
 with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):status=tool.main(arguments)
 if code is not None:
  assert (status,stdout.getvalue(),stderr.getvalue())==(1,'',code+'\n'),(label,status,stderr.getvalue())
  if output is None:assert not target.exists()
 else:
  assert (status,stdout.getvalue(),stderr.getvalue())==(0,'',''),(label,stderr.getvalue())
  report=json.loads(target.read_bytes());assert report['status']==expected_status;protected[target]=target.read_bytes()
 controls.append(label)
 return target

with patch.object(subprocess,'Popen',side_effect=AssertionError('no subprocess')),patch.object(subprocess,'run',side_effect=AssertionError('no subprocess')):
 invoke(code='EXPECT_PIN',pin='bad',label='malformed-pin')
 invoke(code='EXPECT_DIGEST',pin='0'*64,label='wrong-expectation-pin')
 invoke(code='EXPECT_CASE',case='!',label='bad-case-id')
 invoke(code='EXPECT_CASE',case='missing',label='absent-case')
 altered=copy.deepcopy(base);altered['form']='record-form/6';invoke(altered,code='EXPECT_FORM',label='wrong-form')
 altered=copy.deepcopy(base);altered['cases'][0]['arguments']=[1];invoke(altered,code='EXPECT_ARGUMENTS',label='wrong-arguments')
 altered=copy.deepcopy(base);altered['cases'].append({'id':'later','arguments':[],'expected':{}});invoke(altered,code='EXPECT_DOCUMENT',label='malformed-unselected')
 altered=copy.deepcopy(base);altered['cases']*=2;invoke(altered,code='EXPECT_DOCUMENT',label='duplicate-id')
 altered=copy.deepcopy(base);altered['cases']=[];invoke(altered,code='EXPECT_DOCUMENT',label='empty-cases')
 altered=copy.deepcopy(base);altered['cases']=[dict(copy.deepcopy(base['cases'][0]),id='case'+str(i)) for i in range(256)];invoke(altered,case='case255',label='256-cases')
 altered['cases'].append(dict(copy.deepcopy(base['cases'][0]),id='case256'));invoke(altered,code='EXPECT_DOCUMENT',label='257-cases')
 altered=copy.deepcopy(base);altered['cases'][0]['expected']={'status':'invalid-ir','value_type':None,'value':None,'reason':'RR_TYPE','location':''};invoke(altered,code='EXPECT_DOCUMENT',label='invalid-ir-expectation')
 invoke(raw=canon(base).replace(b'"schema":',b'"schema":"duplicate","schema":',1),code='EXPECT_DOCUMENT',label='duplicate-json-key')
 invoke(raw=canon(base).replace(b'"value":1',b'"value":1.0'),code='EXPECT_DOCUMENT',label='float-expectation')
 altered=copy.deepcopy(base);later=copy.deepcopy(base['cases'][0]);later['id']='later';later['arguments']=['\ud800'];altered['cases'].append(later)
 invoke(raw=json.dumps(altered,ensure_ascii=True).encode(),code='EXPECT_DOCUMENT',label='unselected-surrogate')
 for depth in (128,129):
  altered=copy.deepcopy(base);later=copy.deepcopy(base['cases'][0]);later['id']='later';nested=0
  for _ in range(depth-4):nested=[nested]
  later['arguments']=[nested];altered['cases'].append(later)
  invoke(altered,code=None if depth==128 else 'EXPECT_DOCUMENT',label='depth'+str(depth))
 for value in (-9223372036854775808,9223372036854775807):
  altered=copy.deepcopy(base);later=copy.deepcopy(base['cases'][0]);later['id']='later';later['arguments']=[value];altered['cases'].append(later);invoke(altered,label='int64-endpoint'+str(value))
 altered=copy.deepcopy(base);later=copy.deepcopy(base['cases'][0]);later['id']='later';later['arguments']=[9223372036854775808];altered['cases'].append(later);invoke(altered,code='EXPECT_DOCUMENT',label='integer-out-of-range')
 invoke(raw=json.dumps(base,indent=2).encode(),label='pretty-json')
 invoke(raw=canon(base)+b' '*(1048576-len(canon(base))),label='inclusive-input')
 for token in (b'1e0',b'NaN',b'-9223372036854775809'):
  invoke(raw=canon(base).replace(b'"value":1',b'"value":'+token),code='EXPECT_DOCUMENT',label='expectation-number-'+token.decode())
 for member in ('arguments.json','reference.stdout'):
  original=tool.bundle.read;count=[0]
  def changed(path,limit):
   raw=original(path,limit)
   if path.name==member:
    count[0]+=1
    if count[0]==2:return raw+b' '
   return raw
  with patch.object(tool.bundle,'read',side_effect=changed):invoke(code='EXPECT_CHANGED',label='changed-'+member)
 occupied=out/'occupied';save(occupied,b'keep');invoke(code='EXPECT_OUTPUT',output=occupied,label='occupied-output')
 invoke(code='EXPECT_OUTPUT',output=b/'new-report',label='inside-output')
 invoke(raw=b' '*(1048576+1),code='EXPECT_BOUNDS',label='oversized-expectation')
 link=out/'expectation-link';link.symlink_to(spec)
 links[link]=spec
 try:tool.verify(b,receipt,link,sha(spec.read_bytes()),base['cases'][0]['id'])
 except tool.ExpectError as error:assert error.code=='EXPECT_PATH'
 else:raise AssertionError('symlink accepted')
 assert link.is_symlink() and link.readlink()==spec;controls.append('symlink-expectation')
 output_link=out/'output-link';output_link.symlink_to(out/'absent');links[output_link]=out/'absent'
 invoke(code='EXPECT_OUTPUT',output=output_link,label='symlink-output')
 with patch.object(tool.transport,'write_output',side_effect=tool.transport.Refusal('RECORD_IO')):
  invoke(code='EXPECT_OUTPUT',label='output-io-seam')
 with patch.object(tool,'verify',return_value={'large':'x'*1048576}):
  invoke(code='EXPECT_BOUNDS',label='output-bound-seam')
 large_report={'status':'matched','large':''};large_report['large']='x'*(1048576-len(canon(large_report)))
 assert len(canon(large_report))==1048576
 with patch.object(tool,'verify',return_value=large_report):invoke(label='inclusive-output-seam')
 large_report['large']+='x'
 with patch.object(tool,'verify',return_value=large_report):invoke(code='EXPECT_BOUNDS',label='output-plus-one-seam')
 invoke(pin='bad',output=b/'inside',code='EXPECT_PIN',label='precedence-pin-before-output')
 invoke(raw=b'bad',output=occupied,code='EXPECT_OUTPUT',label='precedence-output-before-document')
 altered=copy.deepcopy(base);altered['cases'].append({'id':'bad'});invoke(altered,case='missing',code='EXPECT_DOCUMENT',label='precedence-document-before-selection')
 invoke(receipt_pin='0'*64,code='RUN_VERIFY_PIN',label='receipt-pin-passthrough')
 original=tool.bundle.read;count=[0]
 def changed_wrong_form(path,limit):
  raw=original(path,limit)
  if path.name=='reference.stdout':
   count[0]+=1
   if count[0]==2:return raw+b' '
  return raw
 altered=copy.deepcopy(base);altered['form']='record-form/6'
 with patch.object(tool.bundle,'read',side_effect=changed_wrong_form):invoke(altered,code='EXPECT_CHANGED',label='precedence-changed-before-form')
 # Valid wider transport is retained, but this comparator explicitly refuses it.
 for number in ('1e0','1.0','9223372036854775808'):
  nrow=copy.deepcopy(fixtures[2]);bb=nrow['bundle'];arg='['+number+']';bb['arguments.json']=arg
  inv=json.loads(bb['invocation.json']);bb['invocation.json']='{"schema":"bagaev-typed-record-invocation/12","program":'+bb['program.json']+',"arguments":'+arg+'}'
  receipt_doc=json.loads(bb['receipt.json']);receipt_doc['arguments_sha256']=sha(arg.encode());receipt_doc['invocation_sha256']=sha(bb['invocation.json'].encode());bb['receipt.json']=canon(receipt_doc).decode()
  nd,nb,ns=prepare(nrow,'numeric'+str(len(controls)));invoke(document=nrow['expectation'],bundle_path=nb,receipt_pin=sha(bb['receipt.json'].encode()),case=nrow['expected_report']['case'],code='EXPECT_ARGUMENTS_DOMAIN',label='numeric-domain-'+number)
 # Synthetic internally consistent controls establish comparison behavior only.
 for mode in ('invalid-ir','nested-bool-int','arguments-bool-int','wrong-failure-location'):
  nrow=copy.deepcopy(fixtures[5] if mode=='wrong-failure-location' else fixtures[2] if mode=='arguments-bool-int' else fixtures[0]);bb=nrow['bundle']
  observed=json.loads(bb['reference.stdout']);receipt_doc=json.loads(bb['receipt.json'])
  if mode=='invalid-ir':observed.update(status='invalid-ir',value_type=None,value=None,reason='RR_TYPE',location='',work=0)
  elif mode=='nested-bool-int':
   observed.update(value_type='Record:Example',value={'flag':True})
   nrow['expectation']['cases'][0]['expected'].update(value_type='Record:Example',value={'flag':1})
  elif mode=='arguments-bool-int':
   bb['arguments.json']='[true]';bb['invocation.json']='{"schema":"bagaev-typed-record-invocation/12","program":'+bb['program.json']+',"arguments":[true]}'
   receipt_doc['arguments_sha256']=sha(bb['arguments.json'].encode());receipt_doc['invocation_sha256']=sha(bb['invocation.json'].encode())
   nrow['expectation']['cases'][0]['arguments']=[1]
  else:nrow['expectation']['cases'][0]['expected']['location']='/program/functions/other/body'
  bb['reference.stdout']=canon(observed).decode()+'\n';receipt_doc['result_sha256']=sha(bb['reference.stdout'].encode())
  for field in ('status','reason','location','work'):receipt_doc['runtime_status' if field=='status' else field]=observed[field]
  bb['receipt.json']=canon(receipt_doc).decode();nd,nb,ns=prepare(nrow,'synthetic'+str(len(controls)))
  invoke(document=nrow['expectation'],bundle_path=nb,receipt_pin=sha(bb['receipt.json'].encode()),case=nrow['expected_report']['case'],code='EXPECT_ARGUMENTS' if mode=='arguments-bool-int' else None,expected_status='mismatched',label=mode)
 # No source execution is reached even on forged consistent evidence.
 for row,directory,bundle,spec in prepared:
  actual=tool.verify(bundle,sha((bundle/'receipt.json').read_bytes()),spec,sha(spec.read_bytes()),row['expected_report']['case'])
  assert actual==row['expected_report']

assert {p for p in candidate.rglob('*') if p.is_file()}==set(closure)
assert set(candidate.rglob('*'))==set(closure)|source_dirs
assert all(stat.S_ISREG(p.lstat().st_mode) and p.read_bytes()==raw for p,raw in {**closure,**protected}.items())
assert not any(p.is_symlink() for p in candidate.rglob('*'))
assert {p for p in candidate.rglob('*') if p.is_dir()}==source_dirs
assert all(stat.S_ISDIR(p.lstat().st_mode) for p in directories|source_dirs|{candidate,frozen})
for bundle,names in bundle_names.items():assert {p.name for p in bundle.iterdir()}==names
assert all(p.is_symlink() and p.readlink()==target for p,target in links.items())
assert set(out.rglob('*'))==set(protected)|set(links)|(directories-{out})
assert set(frozen.iterdir())==set(frozen_before) and all(p.read_bytes()==raw for p,raw in frozen_before.items())
assert len(calls)==8 and len(controls)>=28
save(out/'evidence.json',canon({'status':'PASS','cli_calls':len(calls),'direct_controls':controls,'runtime_calls':0,'checker_calls':0,'application_cases':0,'scope':'Offline supplied-expectation checks; synthetic fixtures not authenticated.'}))
print(json.dumps({'status':'PASS','cli_calls':len(calls),'controls':len(controls)}))
