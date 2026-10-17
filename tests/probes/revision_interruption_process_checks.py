"""Six bounded data-only revision processes; one instrumented output interruption."""
import hashlib,json,os,selectors,stat,subprocess,sys,time
from pathlib import Path
T=Path(__file__).resolve().parents[2];SELF=Path(__file__).resolve()
WORK_NAME='revision-interruption-r2'
GOLD='5733b994ab4612b572e7b42d848e3849a97ee165a826e51ca081d3b1e2946488'
PINS={
 'src/bagaev_component_form.py':'5d8c367a697f5a336f1a61546823fd39cc261bf0dd8f387903873e8ed1a28246',
 'src/bagaev_component_outcome_form.py':'017afb470651a73866dd547afd409cf6f3ab91255c25bcd094508c623fd8d7fc',
 'src/bagaev_component_record_list_form.py':'ac1864840ad0b7f1eb3d3f5a4f2196d13cff9a4b3055e7102a89c2575b66742b',
 'src/bagaev_record_draft.py':'4c10d57f746462fb2d52cd61107213b80d16c04804ff9d5f8664b8c0a3c98671',
 'src/bagaev_record_form.py':'2071ecfce2f9adc5a34d47965b5bb2963238d9dfd2ef5eebbf0c15095a8969ae',
 'src/bagaev_record_revisions.py':'d8be08853e199f8cadd1de5047c028c68c775f85ee293916d2580f8dead7f401',
 'src/bagaev_record_wide_form.py':'a631131d5e475b35adb9dd7c46a270ae82e0c890cac0fd44b0d24f0f6b593767',
 'tools/record_revisions.py':'60afd3302fab26a53fb25908bb672a7edbeda2bae491d68729bd5b14cb703a2b',
 'tools/record_text.py':'309a9fc8b705b3c73629045e74387f341ed885d7b9769e48694e10679c2dfffb'}
MODES=('init','append-stop','inspect-partial','append-occupied','append-recover','checkout')
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
held={};allowed_command=None;spawned=0;blocked=[]

def read(path):
    for parent in path.parents:assert stat.S_ISDIR(parent.lstat().st_mode)
    st=path.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=1048576
    with path.open('rb') as stream:raw=stream.read(1048577)
    assert len(raw)==st.st_size and len(raw)<=1048576
    return raw

def inventory(work):
    found=set()
    with os.scandir(work) as entries:
        for entry in entries:
            assert len(found)<32 and entry.name not in found
            st=entry.stat(follow_symlinks=False)
            assert stat.S_ISREG(st.st_mode) and st.st_nlink==1
            found.add(entry.name)
    return found

def preflight():
    assert __debug__ and sys.dont_write_bytecode and sys.flags.no_site
    for folder in ('src','tools'):assert not (T/folder/'__pycache__').exists()
    for name,pin in PINS.items():
        raw=read(T/name);assert sha(raw)==pin;held[T/name]=raw
    held[SELF]=read(SELF)
    path=T/'examples/probes/record-revisions/inventory-history.json'
    raw=read(path);assert len(raw)==5433 and sha(raw)==GOLD;held[path]=raw
    package=json.loads(raw);assert canonical(package)==raw and len(package['revisions'])==2
    assert set(package)=={'schema','form','head','revisions','semantic_check','execution_admission'}
    assert package['schema']=='bagaev-record-revisions/1' and package['form']=='record-form/5'
    assert package['semantic_check'] is False and package['execution_admission'] is False
    first,second=package['revisions']
    assert first['parent'] is None and second['parent']==first['id'] and package['head']==second['id']
    for item in (first,second):
        assert sha(item['source'].encode())==item['source_sha256']
        preimage={key:item[key] for key in ('parent','source_sha256','program_sha256')}
        assert sha(canonical(preimage))==item['id']
    predecessor={**package,'revisions':[first],'head':first['id']}
    return raw,first,second,canonical(predecessor)

def install_audit(work,child):
    stdlib=Path(os.__file__).resolve().parent
    def audit(event,args):
        global spawned
        if event=='subprocess.Popen':
            assert not child and allowed_command is not None
            assert args[0]==sys.executable and list(args[1])==allowed_command
            assert args[2]==str(work.parent) and args[3] is None
            spawned+=1;assert spawned<=6
        elif event.startswith(('subprocess.','os.exec','os.spawn','socket.','sqlite3.')):
            blocked.append(event);raise AssertionError(event)
        elif event=='exec':
            name=args[0].co_filename
            if name.startswith('<frozen '):return
            if name=='<string>':
                caller=sys._getframe(1)
                if caller.f_code.co_name=='namedtuple' and Path(caller.f_code.co_filename).absolute()==stdlib/'collections/__init__.py':return
            path=Path(name).absolute()
            if path.is_relative_to(stdlib):return
            if path not in held:blocked.append(name)
            assert path in held and read(path)==held[path],'Unpinned code'
    def profile(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('evaluate','_drive','run_flow'):
            blocked.append(frame.f_code.co_name);raise AssertionError('No application evaluation')
    sys.addaudithook(audit);sys.setprofile(profile)

def child(mode,work):
    assert mode in MODES and work.name==WORK_NAME and work.parent==Path.cwd()
    gold,first,second,pred=preflight();install_audit(work,True)
    sys.path.insert(0,str(T/'tools'))
    import record_revisions as cli
    if mode=='init':
        args=['init',str(work/'original.bagaev'),'--output',str(work/'first.json'),
              '--source-sha256',first['source_sha256'],'--program-sha256',first['program_sha256']]
    elif mode.startswith('append-'):
        output=work/('recovered.json' if mode=='append-recover' else 'partial.json')
        args=['append',str(work/'first.json'),'--source',str(work/'successor.bagaev'),
              '--output',str(output),'--package-sha256',sha(pred),'--head',first['id'],
              '--source-sha256',second['source_sha256'],'--program-sha256',second['program_sha256']]
        if mode=='append-stop':
            original_open=Path.open
            class InterruptedStream:
                def __init__(self,stream):self.stream=stream
                def __enter__(self):return self
                def __exit__(self,*args):self.stream.close()
                def write(self,raw):
                    assert type(raw) is bytes and len(raw)>=17
                    assert self.stream.write(raw[:17])==17
                    self.stream.flush()
                    assert blocked==[] and spawned==0
                    os._exit(73)
            def intercepted(path,*args,**kwargs):
                if path==output:
                    assert args==('xb',) and kwargs=={}
                    return InterruptedStream(original_open(path,*args,**kwargs))
                return original_open(path,*args,**kwargs)
            Path.open=intercepted
    elif mode=='inspect-partial':
        args=['inspect',str(work/'partial.json'),'--output',str(work/'inspection.json')]
    else:
        args=['checkout',str(work/'recovered.json'),'--revision',second['id'],
              '--output',str(work/'restored.bagaev')]
    code=cli.main(args)
    assert blocked==[] and spawned==0
    for path,raw in held.items():assert read(path)==raw
    raise SystemExit(code)

def capture(command,work):
    proc=subprocess.Popen(command,cwd=str(work.parent),stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    buffers={'stdout':bytearray(),'stderr':bytearray()};error=None
    try:
        deadline=time.monotonic()+20
        with selectors.DefaultSelector() as selector:
            for name,stream in (('stdout',proc.stdout),('stderr',proc.stderr)):
                os.set_blocking(stream.fileno(),False)
                selector.register(stream,selectors.EVENT_READ,name)
            while selector.get_map():
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('child deadline')
                for key,_ in selector.select(min(remaining,1)):
                    available=4096-len(buffers[key.data])
                    chunk=os.read(key.fileobj.fileno(),min(4096,available+1))
                    if not chunk:selector.unregister(key.fileobj);continue
                    buffers[key.data].extend(chunk[:available])
                    if len(chunk)>available:raise RuntimeError('capture limit: '+key.data)
            proc.wait(timeout=max(.01,deadline-time.monotonic()))
    except BaseException as caught:
        error=type(caught).__name__+': '+str(caught)
        try:proc.kill()
        except ProcessLookupError:pass
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:error+='; owned-child termination not confirmed'
    finally:
        proc.stdout.close();proc.stderr.close()
    return proc.returncode,bytes(buffers['stdout']),bytes(buffers['stderr']),error

def main():
    global allowed_command
    gold,first,second,pred=preflight()
    cwd=Path.cwd();assert not cwd.is_relative_to(T)
    work=cwd/WORK_NAME;assert not work.exists() and not work.is_symlink()
    work.mkdir();tracked={};protected={};verified={};rows=[];failure=None
    def save(name,raw):
        assert len(raw)<=1048576 and len(tracked)<32 and sum(map(len,tracked.values()))+len(raw)<=2097152
        path=work/name
        with path.open('xb') as stream:assert stream.write(raw)==len(raw)
        assert read(path)==raw;tracked[name]=raw;protected[name]=raw
    def snapshot():
        actual={};total=0
        for name in inventory(work):
            raw=read(work/name);total+=len(raw);assert total<=2097152
            actual[name]=raw
        tracked.clear();tracked.update(actual)
    def preserve():
        for path,raw in held.items():assert read(path)==raw
        for name,raw in protected.items():assert read(work/name)==raw
        for name,raw in tracked.items():assert read(work/name)==raw
        assert inventory(work)==set(tracked)
    def verify_artifact(name,expected):
        assert tracked[name]==expected,name
        protected[name]=expected;verified[name]=sha(expected)
    save('original.bagaev',first['source'].encode());save('successor.bagaev',second['source'].encode())
    install_audit(work,False)
    expected_codes=(0,73,1,1,0,0)
    expected_errors=(b'',b'',b'REVISION_JSON\n',b'RECORD_PATH\n',b'',b'')
    try:
        for mode,code,error in zip(MODES,expected_codes,expected_errors):
            allowed_command=[sys.executable,'-B','-S',str(SELF),'--child',mode,str(work)]
            status,out,err,capture_error=capture(allowed_command,work)
            allowed_command=None
            save(mode+'.stdout',out);save(mode+'.stderr',err)
            snapshot()
            rows.append({'mode':mode,'returncode':status,'stdout_sha256':sha(out),
                         'stderr_sha256':sha(err),'capture_error':capture_error,
                         'streams_complete':capture_error is None,
                         'observed_artifacts':{n:sha(b) for n,b in tracked.items()}})
            assert capture_error is None,(mode,capture_error)
            assert (status,out,err)==(code,b'',error),mode
            if mode=='init':verify_artifact('first.json',pred)
            elif mode=='append-stop':verify_artifact('partial.json',gold[:17])
            elif mode=='append-recover':verify_artifact('recovered.json',gold)
            elif mode=='checkout':verify_artifact('restored.bagaev',second['source'].encode())
            assert not (work/'inspection.json').exists();preserve()
        assert spawned==6 and blocked==[]
    except BaseException as error:
        allowed_command=None;failure={'type':type(error).__name__,'message':str(error)}
    snapshot_complete=True;preserved=True
    try:snapshot();preserve()
    except BaseException as error:
        snapshot_complete=False;preserved=False
        failure=failure or {'type':type(error).__name__,'message':str(error)}
    save('evidence.json',canonical({'status':'FAIL' if failure else 'PASS','failure':failure,'calls':rows,
         'child_processes':spawned,'fault':'exact output stream writes and flushes17 bytes, then os._exit(73)',
         'expected_partial_sha256':sha(gold[:17]),'expected_recovered_package_sha256':GOLD,
         'expected_checkout_source_sha256':second['source_sha256'],
         'verified_at_creation':verified,'complete_artifact_snapshot':snapshot_complete,
         'inputs_and_prior_outputs_preserved':preserved,
         'application_evaluations':0,
         'parent_forbidden_attempts':blocked,'probe_sha256':sha(held[SELF]),'dependency_sha256':PINS,
         'durability_verified':False,'atomic_publication_verified':False}))
    save('manifest.json',canonical({'files':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in tracked.items()}}))
    preserve()
    if failure:raise RuntimeError('Preserved interrupted-revision test failure: '+failure['message'])
    print('PASS 6 fresh processes; retained17-byte partial; exact recovery')

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--child':child(sys.argv[2],Path(sys.argv[3]))
    else:assert len(sys.argv)==1;main()
