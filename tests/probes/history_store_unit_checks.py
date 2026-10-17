"""Retained logical/guard/fault controls on disposable own stores; no source evaluation."""
import argparse,contextlib,copy,errno,hashlib,io,json,os,sqlite3,sys
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2];p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.absolute();out.mkdir()
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'src'))
sha=lambda b:hashlib.sha256(b).hexdigest();canon=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
source=ROOT/'tools/record_history_store.py';assert sha(source.read_bytes())=='0d4ddfbe178894d824199905c52aeafd84f3581cce182a9995966a0ed4f9b666'
oracle=ROOT/'examples/probes/history-store/cases.json';raw=oracle.read_bytes();assert sha(raw)=='1962046658cf3908cd5b16163ee361086feda5d876fd87af1271c31d3e180dea'
review_path=ROOT/'examples/probes/history-store/review-controls.json';review_raw=review_path.read_bytes();assert sha(review_raw)=='aa0b529ca95f4d78a1e53b2405dfb9a336fa533bfe12174c12aa9b3ae74e6414'
import record_history_store as store
contract_bounds=json.loads(review_raw)['bounds']
assert (store.LIMIT,store.DB_LIMIT,store.JOURNAL_LIMIT)==(contract_bounds['source'],contract_bounds['database'],contract_bounds['journal'])
assert store.MAGIC==bytes.fromhex('d9d505f920a163d7')
assert store.SQL=="CREATE TABLE state (id INTEGER PRIMARY KEY CHECK (id = 1), schema TEXT NOT NULL CHECK (schema = 'bagaev-record-history-store/1'), payload BLOB NOT NULL)"
fixture=json.loads(raw);case=fixture['cases'][0];rows=case['appended']['revisions'];observations=[];covered=set()
def save(path,data):
 with path.open('xb') as f:f.write(data)
def snap(directory):
 return {str(p.relative_to(directory)):('link',str(p.readlink())) if p.is_symlink() else ('file',p.read_bytes()) if p.is_file() else ('dir',None) for p in directory.rglob('*')}
def fresh(name):
 d=out/name;d.mkdir();return d
original=out/'original.bagaev';candidate=out/'candidate.bagaev';save(original,rows[0]['source'].encode());save(candidate,rows[1]['source'].encode());base=out/'baseline'
assert store.initialize(base,'5',original,rows[0]['source_sha256'],rows[0]['program_sha256'])==case['initial_report']
assert store.snapshot(base,'5')==case['initial'];base_raw=(base/'store.sqlite3').read_bytes()
def clone(name):
 d=fresh(name);s=d/'store';s.mkdir();save(s/'store.sqlite3',base_raw);return d,s

def append(s,**changes):
 opts={'directory':s,'form':'5','package_sha256':case['initial_report']['package_sha256'],'head':rows[0]['id'],'source':candidate,'source_sha256':rows[1]['source_sha256'],'program_sha256':rows[1]['program_sha256']};opts.update(changes);return store.append(**opts)
def refuse(name,fn,code):
 try:fn()
 except (store.StoreError,store.legacy.RevisionError) as error:assert error.code==code,(name,error.code,code)
 else:raise AssertionError((name,'unexpected success'))
 observations.append({'case':name,'error':code,'status':'PASS'});covered.add(name)
for control in fixture['refusals']:
 name=control['case'];code=control['error'];d,s=clone(name)
 if name=='invalid-form':refuse(name,lambda:store.snapshot(s,'7'),code)
 elif name=='bad-source-pin-syntax':refuse(name,lambda:append(s,source_sha256='X'*64),code)
 elif name=='occupied-init':refuse(name,lambda:store.initialize(s,'5',original,rows[0]['source_sha256'],rows[0]['program_sha256']),code)
 elif name=='missing-store':refuse(name,lambda:store.snapshot(d/'absent','5'),code)
 elif name=='wrong-source-pin':refuse(name,lambda:append(s,source_sha256='0'*64),code)
 elif name=='stale-package':refuse(name,lambda:append(s,package_sha256='0'*64,source=d/'absent'),code)
 elif name=='stale-head':refuse(name,lambda:append(s,head='0'*64,source=d/'absent'),code)
 elif name=='unchanged-program':refuse(name,lambda:append(s,source=original,source_sha256=rows[0]['source_sha256'],program_sha256=rows[0]['program_sha256']),code)
 elif name=='wrong-form':refuse(name,lambda:store.snapshot(s,'6'),code)
 elif name=='unknown-revision':refuse(name,lambda:store.legacy.checkout(store.snapshot(s,'5'),'f'*64),code)
 elif name in ('occupied-output','inside-output'):
  target=d/'occupied' if name=='occupied-output' else s/'output.json'
  if name=='occupied-output':save(target,b'preserve')
  stderr=io.StringIO();before=snap(s)
  with contextlib.redirect_stderr(stderr):status=store.main(['export',str(s),'--form','5','--output',str(target)])
  assert (status,stderr.getvalue())==(1,code+'\n') and snap(s)==before
  if name=='occupied-output':assert target.read_bytes()==b'preserve'
  else:assert not target.exists()
  observations.append({'case':name,'error':code,'status':'PASS'});covered.add(name)
 elif name in ('restore-wrong-pin','restore-corrupt-history'):
  package=copy.deepcopy(case['appended'])
  if name=='restore-corrupt-history':package['revisions'][1]['source']+=' '
  imported=d/'import.json';save(imported,canon(package));pin='0'*64 if name=='restore-wrong-pin' else case['appended_report']['package_sha256']
  refuse(name,lambda:store.restore(d/'new','5',imported,pin),code);assert not (d/'new').exists()
 elif name in ('extra-schema','noncanonical-stored-history'):
  conn=sqlite3.connect(s/'store.sqlite3',isolation_level=None)
  try:
   conn.execute('BEGIN IMMEDIATE')
   if name=='extra-schema':conn.execute('CREATE TABLE unexpected (value TEXT)')
   else:conn.execute('UPDATE state SET payload=? WHERE id=1',(json.dumps(case['initial'],indent=2).encode(),))
   conn.execute('COMMIT')
  finally:conn.close()
  before=snap(s);refuse(name,lambda:store.snapshot(s,'5'),code);assert snap(s)==before
 elif name=='extra-row-seam':
  conn=Mock();schema=Mock();schema.fetchall.return_value=[('table','state',store.SQL)];quick=Mock();quick.fetchmany.return_value=[('ok',)];size=Mock();size.fetchall.return_value=[(1,store.SCHEMA,1,'blob'),(1,store.SCHEMA,1,'blob')];conn.execute.side_effect=[schema,quick,size]
  refuse(name,lambda:store._snapshot(conn,'5'),code)
 elif name=='extra-member':save(s/'unexpected',b'x');refuse(name,lambda:store.snapshot(s,'5'),code)
 elif name=='symlink-store':link=d/'link';link.symlink_to(s);refuse(name,lambda:store.snapshot(link,'5'),code)
 elif name=='symlink-database':
  target=d/'retained.sqlite3';(s/'store.sqlite3').rename(target);(s/'store.sqlite3').symlink_to(target);refuse(name,lambda:store.snapshot(s,'5'),code);assert target.read_bytes()==base_raw
 elif name=='hardlink-database':os.link(s/'store.sqlite3',d/'retained-link');refuse(name,lambda:store.snapshot(s,'5'),code);assert (d/'retained-link').read_bytes()==base_raw
 elif name in ('journal-footer','wal-header-without-sidecars','bad-database-header'):
  if name=='journal-footer':
   sentinel=d/'outside-sentinel';save(sentinel,b'untouched');save(s/'store.sqlite3-journal',str(sentinel).encode()+b'\0'*8+store.MAGIC)
  else:
   data=bytearray(base_raw)
   if name=='wal-header-without-sidecars':data[18:20]=b'\x02\x02'
   else:data[:3]=b'bad'
   (s/'store.sqlite3').write_bytes(data)
  before=snap(d)
  with patch.object(store,'_connect',side_effect=AssertionError('connect forbidden')):refuse(name,lambda:store.recover(s,'5'),code)
  assert snap(d)==before
 elif name=='oversized-database':
  with (s/'store.sqlite3').open('r+b') as f:f.truncate(store.DB_LIMIT+1)
  with patch.object(store,'_connect',side_effect=AssertionError('connect forbidden')):refuse(name,lambda:store.snapshot(s,'5'),code)
 elif name=='oversized-source':large=d/'large.bagaev';save(large,b' '* (store.LIMIT+1));refuse(name,lambda:append(s,source=large),code)
 elif name=='busy-writer':
  lock=sqlite3.connect(s/'store.sqlite3',isolation_level=None);lock.execute('BEGIN IMMEDIATE')
  try:refuse(name,lambda:append(s),code)
  finally:lock.execute('ROLLBACK');lock.close()
  assert store.snapshot(s,'5')==case['initial']
 elif name=='unsuitable-defaults-seam':
  conn=Mock();cursor=Mock();cursor.fetchmany.return_value=[('wal',)];conn.execute.return_value=cursor
  with patch.object(store,'_connect',return_value=conn):refuse(name,lambda:store._open(s,False),code)
  conn.close.assert_called_once()
 elif name=='commit-error-seam':
  real=store._open(s,True)
  class Fault:
   @property
   def in_transaction(self):return real.in_transaction
   def close(self):real.close()
   def execute(self,sql,*args):
    if sql=='COMMIT':raise sqlite3.OperationalError('injected commit fault')
    return real.execute(sql,*args)
  with patch.object(store,'_open',return_value=Fault()):refuse(name,lambda:append(s),code)
  assert store.snapshot(s,'5')==case['initial']
 elif name=='stdout-error-seam':
  stream=Mock();stream.write.side_effect=BrokenPipeError(errno.EPIPE,'closed');stderr=io.StringIO();args=['append',str(s),'--form','5','--package-sha256',case['initial_report']['package_sha256'],'--head',rows[0]['id'],'--source',str(candidate),'--source-sha256',rows[1]['source_sha256'],'--program-sha256',rows[1]['program_sha256']]
  with patch.object(sys,'stdout',stream),contextlib.redirect_stderr(stderr):status=store.main(args)
  assert (status,stderr.getvalue())==(1,code+'\n');stream.close.assert_called_once();assert store.snapshot(s,'5')==case['appended']
  observations.append({'case':name,'error':code,'status':'PASS'});covered.add(name)
 elif name=='readonly-rollback-seam':
  error=sqlite3.OperationalError('recovery required');error.sqlite_errorcode=getattr(sqlite3,'SQLITE_READONLY_ROLLBACK',776)
  with patch.object(store,'_connect',side_effect=error):refuse(name,lambda:store.snapshot(s,'5'),code)
 else:raise AssertionError(name)
 if name in {'invalid-form','bad-source-pin-syntax','occupied-init','missing-store','wrong-source-pin','stale-package','stale-head','unchanged-program','wrong-form','unknown-revision','occupied-output','inside-output','restore-wrong-pin','restore-corrupt-history','oversized-source','busy-writer','commit-error-seam'}:
  assert canon(store.snapshot(s,'5'))==canon(case['initial']),name
assert covered=={c['case'] for c in fixture['refusals']}
# Independent-review fault additions, kept distinct from the frozen31 transitions.
for name,target,fn in [('read-eio','lstat',lambda:store.read_file(original)),('guard-eio','lstat',lambda:store._guard(base)),('install-eio','mkdir',lambda:store._install(out/'not-created','5',case['initial']))]:
 with patch.object(Path,target,side_effect=OSError(errno.EIO,'injected IO')):refuse(name,fn,'HSTORE_IO')
stream=Mock();stream.write.side_effect=BrokenPipeError(errno.EPIPE,'closed')
with patch.object(sys,'stderr',stream):assert store.main([])==1
stream.close.assert_called_once();observations.append({'case':'stderr-unwritable','status':'PASS','exit':1})
d,s=clone('oversized-stored-payload');conn=sqlite3.connect(s/'store.sqlite3',isolation_level=None)
try:conn.execute('UPDATE state SET payload=? WHERE id=1',(b' '* (store.LIMIT+1),))
finally:conn.close()
refuse('oversized-stored-payload',lambda:store.snapshot(s,'5'),'HSTORE_BOUNDS')
# Inclusive input guard only, not a claim that arbitrary1MiBtext is valid source.
boundary=out/'inclusive-input';save(boundary,b' '*store.LIMIT);assert store.read_file(boundary)==b' '*store.LIMIT
assert (base/'store.sqlite3').read_bytes()==base_raw and store.snapshot(base,'5')==case['initial']
assert original.read_bytes()==rows[0]['source'].encode() and candidate.read_bytes()==rows[1]['source'].encode() and oracle.read_bytes()==raw
assert review_path.read_bytes()==review_raw and sha(source.read_bytes())=='0d4ddfbe178894d824199905c52aeafd84f3581cce182a9995966a0ed4f9b666'
assert {c['case'] for c in json.loads(review_raw)['cases']} <= {r['case'] for r in observations}
conn=store._open(base,False)
try:defaults={key:conn.execute('PRAGMA '+key).fetchone()[0] for key in ('journal_mode','synchronous','locking_mode','page_size')}
finally:conn.close()
result={'status':'PASS','frozen_refusal_controls':31,'review_controls':5,'inclusive_read_guard':True,'sqlite_version':sqlite3.sqlite_version,'defaults':defaults,'observations':observations,'reference_calls':0,'checker_calls':0,'hot_journal_recovery_claim':False}
save(out/'evidence.json',canon(result));print(json.dumps(result))
