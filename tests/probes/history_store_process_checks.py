"""Actual local CLI state transitions, deterministic child exits and closed pipes."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();out.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest();canon=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
cli=ROOT/'tools/record_history_store.py';source=ROOT/'tools/record_history_store.py';worker=ROOT/'tests/probes/history_store_exit_worker.py';oracle=ROOT/'examples/probes/history-store/cases.json'
assert sha(cli.read_bytes())=='0d4ddfbe178894d824199905c52aeafd84f3581cce182a9995966a0ed4f9b666'
assert sha(source.read_bytes())=='0d4ddfbe178894d824199905c52aeafd84f3581cce182a9995966a0ed4f9b666'
assert sha(worker.read_bytes())=='6e80482646bef31f0884c26d3c123ff27526572d6b9b0cc662bd11dd0a795420'
raw=oracle.read_bytes();assert sha(raw)=='1962046658cf3908cd5b16163ee361086feda5d876fd87af1271c31d3e180dea';cases=json.loads(raw)['cases']
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'src'));import record_history_store as store
held_sources={p:p.read_bytes() for p in ROOT.rglob('*') if p.is_file()};assert not any(p.is_symlink() or p.suffix=='.pyc' for p in ROOT.rglob('*'))
commands=[];outputs={};store_rows=[];crashes=[]
def save(path,data):
 with path.open('xb') as f:f.write(data)
 outputs[path]=data

def record(label,argv,code,stdout,stderr):
 save(out/(label+'.stdout'),stdout);save(out/(label+'.stderr'),stderr)
 row={'label':label,'argv':argv,'cwd':str(out),'returncode':code};commands.append(row);save(out/(label+'.command.json'),canon(row))
def call(label,args,stdout=b''):
 argv=[sys.executable,'-B','-S',str(cli),*map(str,args)]
 z=subprocess.run(argv,cwd=out,capture_output=True,timeout=20);record(label,argv,z.returncode,z.stdout,z.stderr)
 assert z.returncode==0 and z.stdout==stdout and z.stderr==b'',(label,z.returncode,z.stdout,z.stderr)
 assert all(p.read_bytes()==data for p,data in outputs.items())

def expect_file(path,data):assert path.read_bytes()==data;outputs[path]=data
def communicate(child):
 try:return child.communicate(timeout=20)
 except subprocess.TimeoutExpired:
  child.kill();child.communicate(timeout=2)
  raise AssertionError('own child timed out and was killed')
for case in cases:
 form=case['form'];name=case['name'];d=out/name;d.mkdir();rows=case['appended']['revisions'];original=d/'original.bagaev';candidate=d/'candidate.bagaev';save(original,rows[0]['source'].encode());save(candidate,rows[1]['source'].encode());s=d/'store'
 call(name+'-init',['init',s,'--form',form,'--source',original,'--source-sha256',rows[0]['source_sha256'],'--program-sha256',rows[0]['program_sha256']],canon(case['initial_report'])+b'\n')
 for op,filename,expected in [('inspect','initial-report.json',canon(case['initial_report'])),('export','initial.json',canon(case['initial']))]:
  target=d/filename;call(name+'-'+op+'-initial',[op,s,'--form',form,'--output',target]);expect_file(target,expected)
 call(name+'-append',['append',s,'--form',form,'--package-sha256',case['initial_report']['package_sha256'],'--head',rows[0]['id'],'--source',candidate,'--source-sha256',rows[1]['source_sha256'],'--program-sha256',rows[1]['program_sha256']],canon(case['appended_report'])+b'\n')
 exported=d/'appended.json';call(name+'-export-appended',['export',s,'--form',form,'--output',exported]);expect_file(exported,canon(case['appended']))
 for i,row in enumerate(rows):
  target=d/('checkout'+str(i)+'.bagaev');call(name+'-checkout'+str(i),['checkout',s,'--form',form,'--revision',row['id'],'--output',target]);expect_file(target,row['source'].encode())
 imported=d/'pretty.json';save(imported,json.dumps(case['appended'],indent=2).encode());restored=d/'restored'
 call(name+'-restore',['restore',restored,'--form',form,'--input',imported,'--package-sha256',case['appended_report']['package_sha256']],canon(case['appended_report'])+b'\n')
 for op,filename,expected in [('inspect','restored-report.json',canon(case['appended_report'])),('export','restored.json',canon(case['appended']))]:
  target=d/filename;call(name+'-'+op+'-restored',[op,restored,'--form',form,'--output',target]);expect_file(target,expected)
 call(name+'-recover',['recover',s,'--form',form],canon(case['appended_report'])+b'\n')
 assert store.snapshot(s,form)==case['appended'] and store.snapshot(restored,form)==case['appended'];store_rows.extend([(s,form,case['appended']),(restored,form,case['appended'])])
 # Each child is awaited before another starts. No cache/SQLite setting changes.
 for stage,code,expected in [('before_commit',73,case['initial']),('after_commit',74,case['appended'])]:
  child_store=d/('exit-'+stage);assert store.initialize(child_store,form,original,rows[0]['source_sha256'],rows[0]['program_sha256'])==case['initial_report']
  control=d/(stage+'.json');save(control,canon({'directory':str(child_store),'form':form,'package_sha256':case['initial_report']['package_sha256'],'head':rows[0]['id'],'source':str(candidate),'source_sha256':rows[1]['source_sha256'],'program_sha256':rows[1]['program_sha256']}))
  argv=[sys.executable,'-B','-S',str(worker),str(control),'--output-root',str(out),'--stage',stage];z=subprocess.run(argv,cwd=out,capture_output=True,timeout=20);label=name+'-'+stage;record(label,argv,z.returncode,z.stdout,z.stderr);assert z.returncode==code and z.stdout==z.stderr==b''
  capture=d/('captured-'+stage);capture.mkdir()
  for path in child_store.iterdir():assert path.is_file() and not path.is_symlink();save(capture/path.name,path.read_bytes())
  needed=False
  def readonly_preserved():
   assert {p.name for p in child_store.iterdir()}=={p.name for p in capture.iterdir()}
   assert all(not p.is_symlink() and p.is_file() and p.read_bytes()==(capture/p.name).read_bytes() for p in child_store.iterdir())
  try:actual=store.snapshot(child_store,form)
  except store.StoreError as error:
   assert error.code=='HSTORE_RECOVERY';readonly_preserved();needed=True;store.recover(child_store,form);actual=store.snapshot(child_store,form)
  else:readonly_preserved()
  assert canon(actual)==canon(expected);store_rows.append((child_store,form,expected));crashes.append({'form':form,'stage':stage,'exit':code,'logical_state':'initial' if stage=='before_commit' else 'appended','recovery_required_observed':needed})
# Real no-reader stdout pipe after a committed init: exactexit1, retained state.
case=cases[0];rows=case['initial']['revisions'];d=out/'closed-pipes';d.mkdir();original=d/'source.bagaev';save(original,rows[0]['source'].encode());s=d/'store'
argv=[sys.executable,'-B','-S',str(cli),'init',str(s),'--form','5','--source',str(original),'--source-sha256',rows[0]['source_sha256'],'--program-sha256',rows[0]['program_sha256']]
r,w=os.pipe();os.close(r)
try:child=subprocess.Popen(argv,cwd=out,stdout=w,stderr=subprocess.PIPE)
finally:os.close(w)
stdout,stderr=communicate(child);record('closed-stdout',argv,child.returncode,b'',stderr);assert child.returncode==1 and stderr==b'HSTORE_UNCERTAIN\n';assert store.snapshot(s,'5')==case['initial'];store_rows.append((s,'5',case['initial']))
argv=[sys.executable,'-B','-S',str(cli)]
r,w=os.pipe();os.close(r)
try:child=subprocess.Popen(argv,cwd=out,stdout=subprocess.PIPE,stderr=w)
finally:os.close(w)
stdout,stderr=communicate(child);record('closed-stderr',argv,child.returncode,stdout,b'');assert child.returncode==1 and stdout==b''
assert len(commands)==28
assert all(canon(store.snapshot(path,form))==canon(expected) for path,form,expected in store_rows)
assert all(path.read_bytes()==data for path,data in outputs.items()) and all(path.read_bytes()==data for path,data in held_sources.items())
assert {p for p in ROOT.rglob('*') if p.is_file()}==set(held_sources) and not any(p.is_symlink() for p in ROOT.rglob('*'))
expected_files=set(outputs)|{p for directory,_,_ in store_rows for p in directory.iterdir()}
assert {p for p in out.rglob('*') if p.is_file()}==expected_files and not any(p.is_symlink() for p in out.rglob('*'))
expected_dirs={p for f in expected_files for p in f.parents if p!=out and p.is_relative_to(out)}
assert {p for p in out.rglob('*') if p.is_dir()}==expected_dirs
result={'status':'PASS','cli_calls':24,'controlled_exit_children':4,'total_child_processes':len(commands),'forms':2,'reference_calls':0,'checker_calls':0,'process_interruption_observations':crashes,'actual_closed_pipe_checks':2,'hot_journal_recovery_observed':any(c['recovery_required_observed'] for c in crashes),'power_loss_claim':False,'same_environment':True,'commands':commands}
save(out/'evidence.json',canon(result));print(json.dumps(result))
