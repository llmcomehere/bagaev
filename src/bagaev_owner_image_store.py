"""Private fixed-row atomic image experiment. Payload semantics belong to its caller."""
from pathlib import Path
import hashlib,json,os,re,sqlite3,stat
MAX_IMAGE=2*1024*1024;MAX_FILE=32*1024*1024;MAX=(1<<63)-1
SQL='CREATE TABLE image (id INTEGER PRIMARY KEY CHECK(id=1), generation INTEGER NOT NULL, digest TEXT NOT NULL, payload BLOB NOT NULL)'
class StorageError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
 if not ok:raise StorageError(code)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def _pairs(items):
 result={}
 for k,v in items:
  if k in result:raise ValueError('duplicate')
  result[k]=v
 return result
def _no_number(_):raise ValueError('non-integer')
def validate(raw):
 need(type(raw)is bytes and len(raw)<=MAX_IMAGE,'STORAGE_BOUNDS')
 try:value=json.loads(raw.decode('utf8'),object_pairs_hook=_pairs,parse_float=_no_number,parse_constant=_no_number)
 except (ValueError,UnicodeError,RecursionError):raise StorageError('STORAGE_CANONICAL') from None
 need(type(value)is dict,'STORAGE_CANONICAL');stack=[(value,1)];count=0
 while stack:
  v,d=stack.pop();count+=1;need(d<=128 and count<=20000,'STORAGE_BOUNDS')
  if type(v)is dict:stack.extend((x,d+1) for x in v.values())
  elif type(v)is list:stack.extend((x,d+1) for x in v)
  elif type(v)is int:need(-(1<<63)<=v<=MAX,'STORAGE_BOUNDS')
 try:canonical=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
 except (ValueError,UnicodeError,RecursionError):raise StorageError('STORAGE_CANONICAL') from None
 need(canonical==raw,'STORAGE_CANONICAL');return raw
def _path(path):
 path=Path(path);need(path.is_absolute(),'STORAGE_PATH')
 try:s=path.lstat()
 except OSError:raise StorageError('STORAGE_PATH') from None
 need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid==os.getuid(),'STORAGE_PATH')
 need(s.st_size<=MAX_FILE,'STORAGE_BOUNDS');return path
def _connection(path):
 path=_path(path)
 try:
  c=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=1.0,isolation_level=None)
  # Inspect defaults only. No PRAGMA assignment or system setting change.
  need(c.execute('PRAGMA journal_mode').fetchone()==('delete',),'STORAGE_PROFILE')
  sync=c.execute('PRAGMA synchronous').fetchone();need(sync is not None and sync[0]>=2,'STORAGE_PROFILE')
  return c
 except StorageError:
  if 'c' in locals():c.close()
  raise
 except sqlite3.DatabaseError:
  if 'c' in locals():c.close()
  raise StorageError('STORAGE_UNAVAILABLE') from None
def _row(c):
 need(c.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()==[('table','image',SQL)],'STORAGE_SCHEMA')
 need(c.execute('PRAGMA quick_check').fetchall()==[('ok',)],'STORAGE_INTEGRITY')
 rows=c.execute('SELECT id,generation,digest,payload FROM image').fetchall()
 need(len(rows)==1,'STORAGE_INTEGRITY');i,g,h,raw=rows[0]
 need(i==1 and type(g)is int and 0<=g<=MAX and type(h)is str and re.fullmatch('[0-9a-f]{64}',h) and type(raw)is bytes,'STORAGE_INTEGRITY')
 validate(raw);need(digest(raw)==h,'STORAGE_INTEGRITY')
 return {'generation':g,'digest':h,'image':raw}
def create(path,raw):
 validate(raw);path=Path(path);need(path.is_absolute() and path.parent.is_dir() and not path.exists() and not path.is_symlink(),'STORAGE_PATH')
 try:
  with path.open('xb'):pass
 except OSError:raise StorageError('STORAGE_PATH') from None
 c=_connection(path)
 try:
  c.execute('BEGIN IMMEDIATE');c.execute(SQL);c.execute('INSERT INTO image VALUES (1,0,?,?)',(digest(raw),raw));c.execute('COMMIT')
 except sqlite3.DatabaseError:raise StorageError('STORAGE_UNAVAILABLE') from None
 finally:c.close()
 return read(path)
def read(path):
 c=_connection(path)
 try:c.execute('BEGIN');value=_row(c);c.execute('COMMIT');return value
 except sqlite3.DatabaseError:raise StorageError('STORAGE_UNAVAILABLE') from None
 finally:c.close()
def compare_and_swap(path,expected_generation,expected_digest,raw):
 validate(raw)
 need(type(expected_generation)is int and 0<=expected_generation<=MAX and type(expected_digest)is str and re.fullmatch('[0-9a-f]{64}',expected_digest),'STORAGE_EXPECTATION')
 c=_connection(path)
 try:
  c.execute('BEGIN IMMEDIATE');old=_row(c)
  need(old['generation']==expected_generation and old['digest']==expected_digest,'STORAGE_CONFLICT')
  if raw==old['image']:c.execute('COMMIT');return {**old,'changed':False}
  need(old['generation']<MAX,'STORAGE_GENERATION');g=old['generation']+1;h=digest(raw)
  c.execute('UPDATE image SET generation=?,digest=?,payload=? WHERE id=1',(g,h,raw));c.execute('COMMIT')
  return {'generation':g,'digest':h,'image':raw,'changed':True}
 except sqlite3.DatabaseError:raise StorageError('STORAGE_UNAVAILABLE') from None
 finally:c.close()
