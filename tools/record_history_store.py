#!/usr/bin/env python3
"""Bounded local candidate histories. No evaluator, admission or SQLite settings writes."""
import errno,json,os,re,sqlite3,stat,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import bagaev_record_revisions as legacy
import bagaev_record_revisions_form6 as six
import record_text as transport
LIMIT=1048576;DB_LIMIT=4194304;JOURNAL_LIMIT=8388608
SCHEMA='bagaev-record-history-store/1'
SQL="CREATE TABLE state (id INTEGER PRIMARY KEY CHECK (id = 1), schema TEXT NOT NULL CHECK (schema = 'bagaev-record-history-store/1'), payload BLOB NOT NULL)"
MAGIC=bytes.fromhex('d9d505f920a163d7')
class StoreError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise StoreError(code)
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def syntax(form,*pins):
    need(type(form) is str and form in ('5','6'),'HSTORE_PROFILE')
    need(all(type(p) is str and re.fullmatch('[0-9a-f]{64}',p) is not None for p in pins),'HSTORE_PIN')
def codec(form):return legacy if form=='5' else six
def _path_error(error):
    path_codes=(errno.ENOENT,errno.ENOTDIR,errno.EEXIST,errno.ELOOP,errno.EACCES,errno.EPERM,errno.ENAMETOOLONG)
    return StoreError('HSTORE_PATH' if isinstance(error,(TypeError,ValueError)) or getattr(error,'errno',None) in path_codes else 'HSTORE_IO')
def _mapped(error):
    if isinstance(error,sqlite3.Error):
        code=getattr(error,'sqlite_errorcode',0)
        if code==getattr(sqlite3,'SQLITE_READONLY_ROLLBACK',776):return StoreError('HSTORE_RECOVERY')
        if code&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):return StoreError('HSTORE_BUSY')
        if code&255 in (sqlite3.SQLITE_CORRUPT,sqlite3.SQLITE_NOTADB):return StoreError('HSTORE_CORRUPT')
        return StoreError('HSTORE_IO')
    if isinstance(error,OSError):return StoreError('HSTORE_IO')
    return error

def read_file(value,limit=LIMIT,member=False):
    try:
        path=Path(value);info=path.lstat()
        need(stat.S_ISREG(info.st_mode),'HSTORE_PATH')
        if member:need(info.st_uid==os.getuid() and info.st_nlink==1,'HSTORE_PATH')
        need(info.st_size<=limit,'HSTORE_BOUNDS')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            actual=os.fstat(stream.fileno());need(stat.S_ISREG(actual.st_mode),'HSTORE_PATH')
            need((actual.st_dev,actual.st_ino)==(info.st_dev,info.st_ino),'HSTORE_PATH')
            if member:need(actual.st_uid==os.getuid() and actual.st_nlink==1,'HSTORE_PATH')
            need(actual.st_size<=limit,'HSTORE_BOUNDS');raw=stream.read(limit+1)
        need(len(raw)<=limit,'HSTORE_BOUNDS');return raw
    except (OSError,TypeError,ValueError) as error:
        if isinstance(error,StoreError):raise
        raise _path_error(error) from None

def _guard(directory,new=False):
    try:
        path=Path(directory).absolute();info=path.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid(),'HSTORE_PATH')
        names=set()
        with os.scandir(path) as items:
            for item in items:
                names.add(item.name);need(len(names)<=2,'HSTORE_PATH')
        need('store.sqlite3' in names and names<={'store.sqlite3','store.sqlite3-journal'},'HSTORE_PATH')
        db=path/'store.sqlite3';raw=read_file(db,DB_LIMIT,True)
        if not(new and raw==b''):
            need(len(raw)>=100 and raw[:16]==b'SQLite format 3\0','HSTORE_CORRUPT')
            need(raw[16:18]==b'\x10\x00' and raw[18:20]==b'\x01\x01','HSTORE_ENVIRONMENT')
        if 'store.sqlite3-journal' in names:
            journal=read_file(path/'store.sqlite3-journal',JOURNAL_LIMIT,True)
            need(not journal.endswith(MAGIC),'HSTORE_JOURNAL')
        return db
    except (OSError,TypeError,ValueError) as error:
        if isinstance(error,StoreError):raise
        raise _path_error(error) from None

def _connect(db,write):
    return sqlite3.connect(db.as_uri()+('?mode=rw' if write else '?mode=ro'),uri=True,timeout=1.0,isolation_level=None)
def _open(directory,write,new=False):
    db=_guard(directory,new);connection=None
    try:
        connection=_connect(db,write)
        for query,allowed in [('journal_mode',[(('delete',),)]),('synchronous',[( (2,),),((3,),)]),('locking_mode',[(('normal',),)]),('page_size',[( (4096,),)])]:
            rows=tuple(connection.execute('PRAGMA '+query).fetchmany(2))
            need(rows in allowed,'HSTORE_ENVIRONMENT')
        return connection
    except BaseException as error:
        if connection is not None:
            try:connection.close()
            except BaseException:pass
        raise _mapped(error) from None

def _snapshot(connection,form):
    rows=connection.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name LIMIT 2').fetchall()
    need(rows==[('table','state',SQL)],'HSTORE_CORRUPT')
    need(connection.execute('PRAGMA quick_check(1)').fetchmany(2)==[('ok',)],'HSTORE_CORRUPT')
    rows=connection.execute('SELECT id,schema,length(payload),typeof(payload) FROM state LIMIT 2').fetchall()
    need(len(rows)==1 and rows[0][0]==1 and rows[0][1]==SCHEMA and rows[0][3]=='blob','HSTORE_CORRUPT')
    need(type(rows[0][2]) is int and 0<=rows[0][2]<=LIMIT,'HSTORE_BOUNDS')
    raw=connection.execute('SELECT payload FROM state WHERE id=1').fetchone()[0]
    try:
        try:package=legacy.loads(raw)
        except legacy.RevisionError as error:
            if error.code!='REVISION_PROFILE':raise
            package=six.loads(raw)
        need(legacy.canonical(package)==raw,'HSTORE_CORRUPT')
    except legacy.RevisionError:raise StoreError('HSTORE_CORRUPT') from None
    need(package['form']=='record-form/'+form,'HSTORE_PROFILE');return package

def _event(stage):
    """Internal deterministic test seam; CLI accepts no callback or fault option."""
    pass

def _transaction(connection,write,action,recovery=False):
    result=None;pending=None;committing=False;committed=False
    try:
        connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        result=action(connection)
        pages=connection.execute('PRAGMA page_count').fetchmany(2)
        need(len(pages)==1 and len(pages[0])==1 and type(pages[0][0]) is int and 0<=pages[0][0]*4096<=DB_LIMIT,'HSTORE_BOUNDS')
        if write:_event('before_commit')
        committing=True;connection.execute('COMMIT');committed=True;committing=False
        if write:_event('after_commit')
    except BaseException as error:
        uncertain=committing or ((write or recovery) and committed)
        try:
            if connection.in_transaction:connection.execute('ROLLBACK')
        except BaseException:uncertain=True
        pending=StoreError('HSTORE_UNCERTAIN') if uncertain else _mapped(error)
    finally:
        try:connection.close()
        except BaseException:
            if pending is None:pending=StoreError('HSTORE_UNCERTAIN' if (write or recovery) and committed else 'HSTORE_IO')
    if pending is not None:raise pending
    return result

def report(package):
    return {'schema':SCHEMA,'status':'ready','form':package['form'],'package_sha256':legacy.package_digest(package),'head':package['head'],'revision_count':len(package['revisions']),'semantic_check':False,'execution_admission':False}

def _install(directory,form,package):
    payload=legacy.canonical(package)
    try:
        path=Path(directory).absolute();path.mkdir(mode=0o700)
        fd=os.open(path/'store.sqlite3',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd)
    except (OSError,TypeError,ValueError) as error:raise _path_error(error) from None
    connection=_open(path,True,new=True)
    def action(conn):
        conn.execute(SQL);conn.execute('INSERT INTO state VALUES (1,?,?)',(SCHEMA,payload));return _snapshot(conn,form)
    return report(_transaction(connection,True,action))

def initialize(directory,form,source,source_sha256,program_sha256):
    syntax(form,source_sha256,program_sha256)
    package=codec(form).initialize(read_file(source),source_sha256=source_sha256,program_sha256=program_sha256)
    return _install(directory,form,package)

def restore(directory,form,input_path,package_sha256):
    syntax(form,package_sha256);package=codec(form).loads(read_file(input_path))
    need(legacy.package_digest(package)==package_sha256,'HSTORE_STALE_PACKAGE')
    return _install(directory,form,package)

def append(directory,form,package_sha256,head,source,source_sha256,program_sha256):
    syntax(form,package_sha256,head,source_sha256,program_sha256)
    def action(conn):
        current=_snapshot(conn,form)
        need(legacy.package_digest(current)==package_sha256,'HSTORE_STALE_PACKAGE')
        need(current['head']==head,'HSTORE_STALE_HEAD')
        updated=codec(form).append(current,read_file(source),expected_package_sha256=package_sha256,expected_head=head,source_sha256=source_sha256,program_sha256=program_sha256)
        conn.execute('UPDATE state SET payload=? WHERE id=1',(legacy.canonical(updated),));return updated
    return report(_transaction(_open(directory,True),True,action))

def snapshot(directory,form):
    syntax(form);return _transaction(_open(directory,False),False,lambda conn:_snapshot(conn,form))
def recover(directory,form):
    syntax(form);return report(_transaction(_open(directory,True),False,lambda conn:_snapshot(conn,form),recovery=True))

def _close_failed_stream(stream):
    # Avoid a second failing buffered flush during interpreter shutdown.
    try:stream.close()
    except (OSError,ValueError):pass

def main(argv=None):
    operation=None
    try:
        parser=transport.Parser(add_help=False,allow_abbrev=False)
        parser.add_argument('operation',choices=('init','append','inspect','export','checkout','restore','recover'));parser.add_argument('directory');parser.add_argument('--form',required=True)
        for name in ('source','source-sha256','program-sha256','package-sha256','head','input','revision','output'):parser.add_argument('--'+name)
        a=parser.parse_args(argv);operation=a.operation
        selected={k for k in ('source','source_sha256','program_sha256','package_sha256','head','input','revision','output') if getattr(a,k) is not None}
        expected={'init':{'source','source_sha256','program_sha256'},'append':{'source','source_sha256','program_sha256','package_sha256','head'},'inspect':{'output'},'export':{'output'},'checkout':{'revision','output'},'restore':{'input','package_sha256'},'recover':set()}[operation]
        if selected!=expected:raise transport.Refusal('TOOL_USAGE')
        syntax(a.form,*[getattr(a,k) for k in ('source_sha256','program_sha256','package_sha256','head','revision') if getattr(a,k) is not None])
        if a.output is not None:
            try:need(not Path(a.output).resolve().is_relative_to(Path(a.directory).resolve()),'HSTORE_OUTPUT')
            except (OSError,ValueError,RuntimeError) as error:
                if isinstance(error,StoreError):raise
                raise StoreError('HSTORE_OUTPUT') from None
        if operation=='init':result=initialize(a.directory,a.form,a.source,a.source_sha256,a.program_sha256)
        elif operation=='append':result=append(a.directory,a.form,a.package_sha256,a.head,a.source,a.source_sha256,a.program_sha256)
        elif operation=='restore':result=restore(a.directory,a.form,a.input,a.package_sha256)
        elif operation=='recover':result=recover(a.directory,a.form)
        else:
            package=snapshot(a.directory,a.form)
            raw=canonical(report(package)) if operation=='inspect' else legacy.canonical(package) if operation=='export' else codec(a.form).checkout(package,a.revision)
            try:transport.write_output(a.output,raw)
            except transport.Refusal:raise StoreError('HSTORE_OUTPUT') from None
            return 0
        try:sys.stdout.write(canonical(result).decode()+'\n');sys.stdout.flush()
        except (OSError,ValueError):
            _close_failed_stream(sys.stdout)
            raise StoreError('HSTORE_UNCERTAIN') from None
        return 0
    except (transport.Refusal,legacy.RevisionError,StoreError) as error:
        try:sys.stderr.write(error.code+'\n');sys.stderr.flush()
        except (OSError,ValueError):_close_failed_stream(sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
