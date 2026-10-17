#!/usr/bin/env python3
"""Run only a separately authorized pinned source checker; never evaluate source."""
import hashlib,json,os,re,selectors,stat,subprocess,sys,time
from pathlib import Path
import record_text as transport
import bagaev_record_check_location as location
from bagaev_record_draft import DraftError

class FlowError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise FlowError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def binary_bytes(path):
    try:
        need(stat.S_ISREG(path.lstat().st_mode),'CHECK_FLOW_PIN')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            need(stat.S_ISREG(os.fstat(f.fileno()).st_mode),'CHECK_FLOW_PIN')
            raw=f.read(33554433)
        need(len(raw)<=33554432,'CHECK_FLOW_PIN');return raw
    except OSError:raise FlowError('CHECK_FLOW_PIN') from None

def capture(argv,timeout=15):
    """Bound direct-child pipe capture; caller supplies execution authority."""
    try:child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except OSError:raise FlowError('CHECK_FLOW_PROCESS') from None
    deadline=time.monotonic()+timeout;parts=[bytearray(),bytearray()]
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ,0)
            selector.register(child.stderr,selectors.EVENT_READ,1)
            while selector.get_map():
                remaining=deadline-time.monotonic();need(remaining>0,'CHECK_FLOW_PROCESS')
                for key,_ in selector.select(remaining):
                    chunk=os.read(key.fileobj.fileno(),65536)
                    if not chunk:selector.unregister(key.fileobj);continue
                    index=key.data;limit=1048576 if index==0 else 4096
                    need(len(parts[index])+len(chunk)<=limit,
                         'CHECK_FLOW_RESULT' if index==0 else 'CHECK_FLOW_PROCESS')
                    parts[index].extend(chunk)
            remaining=deadline-time.monotonic();need(remaining>0,'CHECK_FLOW_PROCESS')
            code=child.wait(timeout=remaining)
        return code,bytes(parts[0]),bytes(parts[1])
    except (OSError,subprocess.TimeoutExpired):raise FlowError('CHECK_FLOW_PROCESS') from None
    finally:
        for pipe in (child.stdout,child.stderr):
            try:pipe.close()
            except OSError:pass
        if child.poll() is None:
            try:child.kill();child.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):raise FlowError('CHECK_FLOW_PROCESS') from None

def run_flow(source,checker,checker_sha256,output,form='5'):
    need(form in ('5','6'),'TOOL_USAGE')
    need(type(checker_sha256) is str and re.fullmatch('[0-9a-f]{64}',checker_sha256),'CHECK_FLOW_PIN')
    source,checker,out=map(lambda p:Path(p).absolute(),(source,checker,output))
    need(sha(binary_bytes(checker))==checker_sha256,'CHECK_FLOW_PIN')
    try:
        raw=transport.read_input(str(source))
        if form=='6':
            import bagaev_record_json_bool_form as codec
        else:codec=location.form
        program=canonical(codec.decode(raw))
        need(len(program)<=1048576,'CHECK_FLOW_SOURCE')
    except (transport.Refusal,location.form.FormError):raise FlowError('CHECK_FLOW_SOURCE') from None
    try:out.mkdir()
    except OSError:raise FlowError('CHECK_FLOW_OUTPUT') from None
    retained={}
    def write(name,data):
        try:
            with (out/name).open('xb') as f:f.write(data)
        except OSError:raise FlowError('CHECK_FLOW_OUTPUT') from None
        retained[name]=data
    write('source.bagaev',raw);write('program.json',program)
    profile='12' if form=='6' else '11'
    argv=[str(checker),'check']+(['--profile','12'] if form=='6' else [])+['--input',str(out/'program.json')]
    code,stdout,stderr=capture(argv)
    need(len(stdout)<=1048576,'CHECK_FLOW_RESULT');need(len(stderr)<=4096,'CHECK_FLOW_PROCESS')
    write('checker.stdout',stdout);write('checker.stderr',stderr)
    need(type(code) is int and code==0 and stderr==b'','CHECK_FLOW_PROCESS')
    try:result=location._json(location._raw(stdout))
    except DraftError:raise FlowError('CHECK_FLOW_RESULT') from None
    need(type(result) is dict and set(result)=={'schema','status','input_sha256','program_sha256','reason','location','execution_admission'},'CHECK_FLOW_RESULT')
    need(result['schema']=='bagaev-record-source-check/'+profile and result['input_sha256']==sha(program)
         and result['execution_admission'] is False,'CHECK_FLOW_RESULT')
    if result['status']=='checked':
        need(result['program_sha256']==sha(program) and result['reason'] is None and result['location'] is None,'CHECK_FLOW_RESULT')
    elif result['status']=='refused':
        try:
            mapper=location.locate_form6 if form=='6' else location.locate
            mapped=mapper(raw,program,stdout,source_sha256=sha(raw),program_sha256=sha(program),
                          input_sha256=sha(program),result_sha256=sha(stdout))
        except (DraftError,location.form.FormError):raise FlowError('CHECK_FLOW_RESULT') from None
        write('location.json',canonical(mapped))
    else:raise FlowError('CHECK_FLOW_RESULT')
    try:need(transport.read_input(str(source))==raw,'CHECK_FLOW_SOURCE')
    except transport.Refusal:raise FlowError('CHECK_FLOW_SOURCE') from None
    need(sha(binary_bytes(checker))==checker_sha256,'CHECK_FLOW_PIN')
    for name,expected in retained.items():
        try:need(transport.read_input(str(out/name))==expected,'CHECK_FLOW_OUTPUT')
        except transport.Refusal:raise FlowError('CHECK_FLOW_OUTPUT') from None
    receipt={'schema':'bagaev-record-check-flow/1','status':result['status'],'form':'record-form/'+form,
        'source_sha256':sha(raw),'program_sha256':sha(program),'input_sha256':sha(program),
        'result_sha256':sha(stdout),'checker_sha256':checker_sha256,'checker_invoked':True,'execution_admission':False}
    write('receipt.json',canonical(receipt));return receipt

def main(argv=None):
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False)
        p.add_argument('source');p.add_argument('--checker',required=True);p.add_argument('--checker-sha256',required=True)
        p.add_argument('--output',required=True);p.add_argument('--form',choices=('5','6'),default='5')
        a=p.parse_args(argv);result=run_flow(a.source,a.checker,a.checker_sha256,a.output,a.form)
        try:print(json.dumps(result,sort_keys=True,separators=(',',':')),flush=True)
        except OSError:raise FlowError('CHECK_FLOW_DELIVERY') from None
        return 0
    except (transport.Refusal,FlowError) as error:
        print(error.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
