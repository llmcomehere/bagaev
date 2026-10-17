"""Fresh checked source execution, gated by caller-reviewed Python bytes."""
import sys
if sys.path: del sys.path[0]
import os
if (not __debug__ or not sys.dont_write_bytecode or not sys.flags.no_site
        or sys.flags.optimize or os.environ.get('PYTHONPATH') or os.environ.get('PYTHONHOME')):
    try: os.write(2, b'CPY_RUN_PROFILE\n')
    except OSError: pass
    raise SystemExit(1)
import argparse,hashlib,json,re,stat,types
from pathlib import Path
LIMIT=1048576
class RunError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise RunError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def read(path,limit,code):
    try:
        need(path.is_absolute() and '..' not in path.parts and len(path.parents)<=64,code)
        need(all(stat.S_ISDIR(p.lstat().st_mode) for p in path.parents),code)
        initial=path.lstat()
        need(stat.S_ISREG(initial.st_mode) and initial.st_nlink==1 and initial.st_size<=limit,code)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            current=os.fstat(f.fileno())
            need(stat.S_ISREG(current.st_mode) and current.st_nlink==1 and current.st_size<=limit
                 and (current.st_dev,current.st_ino)==(initial.st_dev,initial.st_ino),code)
            raw=f.read(limit+1)
        need(len(raw)<=limit,code);return raw
    except (OSError,ValueError) as e:
        if isinstance(e,RunError):raise
        raise RunError(code) from None
_RUNNER_FILE=Path(__file__).absolute()
_RUNNER_SOURCE=read(_RUNNER_FILE,LIMIT,'CPY_RUN_INPUT')
_NAME=re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}\Z')
_FAILURES={'integer-overflow':{'RR_OVERFLOW'},'list-index':{'RR_INDEX'},'work-limit':{'RR_WORK'},
 'record-list-bound':{'RR_RECORD_LIST_ITEMS'},'list-bound':{'RR_LIST_ITEMS','RR_LIST_BYTES'}}
def integer(value):return type(value) is int and -(2**63)<=value<2**63
def text(value):return type(value) is str and len(value)<=256 and len(value.encode('utf-8'))<=1024
def result_value(raw):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('duplicate')
            result[k]=v
        return result
    def bad(_):raise ValueError('not an integer')
    try:
        need(type(raw) is bytes and len(raw)<=8*LIMIT,'CPY_RUN_RESULT')
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_float=bad,parse_constant=bad)
        need(canonical(value)+b'\n'==raw,'CPY_RUN_RESULT')
        pending=[value]
        while pending:
            item=pending.pop()
            if type(item) is str:item.encode('utf-8')
            elif type(item) is int:need(integer(item),'CPY_RUN_RESULT')
            elif type(item) is list:pending.extend(item)
            elif type(item) is dict:pending.extend(item.keys());pending.extend(item.values())
        need(type(value) is dict and set(value)=={'schema','status','value_type','value','work','reason','location'},'CPY_RUN_RESULT')
        need(type(value['schema']) is str and value['schema']=='bagaev-typed-record-result/11'
          and type(value['status']) is str and type(value['work']) is int and 1<=value['work']<=65536,'CPY_RUN_RESULT')
        status=value['status'];payload=value['value'];tag=value['value_type']
        if status!='success':
            need(status in _FAILURES and type(value['reason']) is str and value['reason'] in _FAILURES[status]
              and type(value['location']) is str and value['location'].startswith('/program/functions/')
              and payload is None and tag is None,'CPY_RUN_RESULT');return value
        need(value['reason'] is None and value['location'] is None and type(tag) is str,'CPY_RUN_RESULT')
        if tag=='Int64':good=integer(payload)
        elif tag=='Bool':good=type(payload) is bool
        elif tag=='Text':good=text(payload)
        elif tag=='OptionInt64':good=payload is None or integer(payload)
        elif tag=='TextList':good=type(payload) is list and len(payload)<=64 and all(text(x) for x in payload) and sum(len(x.encode()) for x in payload)<=4096
        else:
            match=re.fullmatch(r'(Record|RecordList|Variant):([A-Za-z][A-Za-z0-9_]{0,31})',tag)
            need(match is not None,'CPY_RUN_RESULT')
            if match[1]=='Record':good=type(payload) is dict and len(payload)<=8
            elif match[1]=='RecordList':good=type(payload) is list and len(payload)<=16 and all(type(x) is dict and len(x)<=8 for x in payload)
            else:good=type(payload) is dict and set(payload)=={'case','value'} and type(payload['case']) is str and _NAME.fullmatch(payload['case']) is not None
        need(good,'CPY_RUN_RESULT');return value
    except (ValueError,UnicodeError,RecursionError,TypeError,KeyError) as e:
        if isinstance(e,RunError):raise
        raise RunError('CPY_RUN_RESULT') from None

def run_flow(source,arguments,checker,*,source_sha256,arguments_sha256,checker_sha256,python_sha256,output):
    for pin in (source_sha256,arguments_sha256,checker_sha256,python_sha256):
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}',pin) is not None,'CPY_RUN_PIN')
    try:source,arguments,checker,out=[Path(p).absolute() for p in (source,arguments,checker,output)]
    except (TypeError,ValueError):raise RunError('CPY_RUN_INPUT') from None
    held={}
    for path,limit,pin in ((source,LIMIT,source_sha256),(arguments,LIMIT,arguments_sha256),(checker,32*LIMIT,checker_sha256)):
        raw=read(path,limit,'CPY_RUN_INPUT');need(sha(raw)==pin,'CPY_RUN_PIN');held[path]=(raw,limit)
    need(sys.dont_write_bytecode and not sys.flags.optimize,'CPY_RUN_INPUT')
    need(read(_RUNNER_FILE,LIMIT,'CPY_RUN_CHANGED')==_RUNNER_SOURCE,'CPY_RUN_CHANGED')
    # Compiler enforces its existing fresh project-source load boundary.
    need('record_source_cpython' not in sys.modules,'CPY_RUN_INPUT')
    compiler_path=_RUNNER_FILE.parent/'record_source_cpython.py'
    compiler_raw=read(compiler_path,LIMIT,'CPY_RUN_INPUT')
    sys.path.insert(0,str(_RUNNER_FILE.parent))
    import record_source_cpython as compiler
    need(Path(compiler.__file__).absolute()==compiler_path and compiler.ROOT==_RUNNER_FILE.parent.parent,'CPY_RUN_INPUT')
    need(read(compiler_path,LIMIT,'CPY_RUN_CHANGED')==compiler_raw,'CPY_RUN_CHANGED')
    closure=compiler.loaded_closure()
    try:
        need('..' not in out.parts and len(out.parents)<=64,'CPY_RUN_OUTPUT')
        need(all(stat.S_ISDIR(p.lstat().st_mode) for p in out.parents),'CPY_RUN_OUTPUT')
        need(not out.exists() and not out.is_symlink(),'CPY_RUN_OUTPUT')
        need(not out.is_relative_to(_RUNNER_FILE.parent)
             and all(not out.is_relative_to(compiler.ROOT/name) for name in ('src','tools')),'CPY_RUN_OUTPUT')
        out.mkdir()
    except (OSError,ValueError):raise RunError('CPY_RUN_OUTPUT') from None
    compiled,compile_receipt=compiler.compile_flow(source,checker,source_sha256,checker_sha256,out/'compiled')
    verified=compiler.verify_artifact(compiled.artifact,compiled)
    need(sha(verified)==python_sha256,'CPY_RUN_PYTHON')
    try:
        need(stat.S_ISDIR(out.lstat().st_mode) and stat.S_ISDIR((out/'compiled').lstat().st_mode),'CPY_RUN_CHANGED')
        members=[]
        with os.scandir(out/'compiled') as entries:
            for entry in entries:
                need(len(members)<6 and stat.S_ISREG(entry.stat(follow_symlinks=False).st_mode),'CPY_RUN_CHANGED')
                members.append(Path(entry.path))
        need({p.name for p in members}=={'source.bagaev','program.json','checker.stdout',
          'checker.stderr','artifact.json','receipt.json'},'CPY_RUN_CHANGED')
        retained={str(p.relative_to(out)):read(p,4*LIMIT,'CPY_RUN_CHANGED') for p in members}
    except (OSError,ValueError) as e:
        if isinstance(e,RunError):raise
        raise RunError('CPY_RUN_CHANGED') from None
    need(set(retained)=={'compiled/source.bagaev','compiled/program.json','compiled/checker.stdout',
      'compiled/checker.stderr','compiled/artifact.json','compiled/receipt.json'},'CPY_RUN_CHANGED')
    need(retained['compiled/source.bagaev']==held[source][0] and retained['compiled/program.json']==compiled.program
      and retained['compiled/artifact.json']==compiled.artifact and retained['compiled/receipt.json']==canonical(compile_receipt)
      and retained['compiled/checker.stderr']==b'','CPY_RUN_CHANGED')
    try:compiler.checker_result(retained['compiled/checker.stdout'],sha(compiled.program))
    except compiler.CompileError:raise RunError('CPY_RUN_CHANGED') from None
    def write(name,raw):
        try:
            with (out/name).open('xb') as f:need(f.write(raw)==len(raw),'CPY_RUN_OUTPUT')
        except OSError:raise RunError('CPY_RUN_OUTPUT') from None
        retained[name]=raw
    name='_bagaev_retained_'+str(id(compiled));need(name not in sys.modules,'CPY_RUN_RESULT')
    module=types.ModuleType(name);module.__file__='<bagaev-verified:'+sha(verified)+'>'
    sys.modules[name]=module
    try:
        exec(compile(verified,module.__file__,'exec'),module.__dict__)
        write('arguments.json',held[arguments][0])
        try:result=module.evaluate(held[arguments][0])
        except module.CPythonPreparationError as e:raise RunError(e.code) from None
    finally:
        # Remove only this generated instance, never compiler/project modules.
        if sys.modules.get(name) is module:del sys.modules[name]
    value=result_value(result);write('result.stdout',result)
    def preserved():
        need(read(_RUNNER_FILE,LIMIT,'CPY_RUN_CHANGED')==_RUNNER_SOURCE,'CPY_RUN_CHANGED')
        for p,(b,limit) in held.items():need(read(p,limit,'CPY_RUN_CHANGED')==b,'CPY_RUN_CHANGED')
        try:need(compiler.loaded_closure()==closure,'CPY_RUN_CHANGED')
        except compiler.CompileError:raise RunError('CPY_RUN_CHANGED') from None
        try:
            need(stat.S_ISDIR(out.lstat().st_mode) and stat.S_ISDIR((out/'compiled').lstat().st_mode),'CPY_RUN_CHANGED')
            expected={out/'compiled':stat.S_IFDIR,**{out/n:stat.S_IFREG for n in retained}}
            actual={}
            for directory in (out,out/'compiled'):
                with os.scandir(directory) as entries:
                    for entry in entries:
                        need(len(actual)<len(expected),'CPY_RUN_CHANGED')
                        path=Path(entry.path);kind=stat.S_IFMT(entry.stat(follow_symlinks=False).st_mode)
                        need(path in expected and kind==expected[path],'CPY_RUN_CHANGED')
                        actual[path]=kind
            need(actual==expected,'CPY_RUN_CHANGED')
        except OSError:raise RunError('CPY_RUN_CHANGED') from None
        for n in sorted(retained):need(read(out/n,max(len(retained[n]),1),'CPY_RUN_CHANGED')==retained[n],'CPY_RUN_CHANGED')
    preserved()
    receipt={'schema':'bagaev-record-cpython-run/1','status':'executed','form':'record-form/5',
      'source_sha256':source_sha256,'program_sha256':sha(compiled.program),'arguments_sha256':arguments_sha256,
      'checker_sha256':checker_sha256,'compile_receipt_sha256':sha(retained['compiled/receipt.json']),
      'artifact_sha256':sha(compiled.artifact),'python_sha256':sha(verified),'generator_sha256':compile_receipt['generator_sha256'],
      'runtime_sha256':compile_receipt['runtime_sha256'],'runner_sha256':sha(_RUNNER_SOURCE),
      'result_sha256':sha(result),'result_status':value['status'],'checker_invoked':True,
      'generated_program_invocations':1,'execution_admission':False}
    write('receipt.json',canonical(receipt));preserved();return receipt

HELP='''Run explicitly authorized form5/profile11 source through fresh checked CPython compilation.
Usage: record_cpython_run.py SOURCE --source-sha256 SHA256 --arguments PATH --arguments-sha256 SHA256 --checker PATH --checker-sha256 SHA256 --python-sha256 SHA256 --output NEW_DIRECTORY
Requires -B -S, reviewed source/emitted Python and a separately approved bounded execution profile.
No downloaded artifact or retained receipt is accepted as executable input.
'''
class Usage(ValueError):pass
class Parser(argparse.ArgumentParser):
    def error(self,message):raise Usage()
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv in (['--help'],['-h']):print(HELP,end='');return 0
    try:
        p=Parser(add_help=False,allow_abbrev=False);p.add_argument('source')
        for flag in ('source-sha256','arguments','arguments-sha256','checker','checker-sha256','python-sha256','output'):p.add_argument('--'+flag,required=True)
        a=p.parse_args(argv)
    except Usage:print('CPY_USAGE',file=sys.stderr);return 2
    try:
        receipt=run_flow(a.source,a.arguments,a.checker,source_sha256=a.source_sha256,
          arguments_sha256=a.arguments_sha256,checker_sha256=a.checker_sha256,python_sha256=a.python_sha256,output=a.output)
        try:sys.stdout.buffer.write(canonical(receipt)+b'\n');sys.stdout.buffer.flush()
        except OSError:
            fd=os.open(os.devnull,os.O_WRONLY)
            try:os.dup2(fd,sys.stdout.fileno())
            finally:os.close(fd)
            print('CPY_DELIVERY',file=sys.stderr);return 1
        return 0
    except ValueError as e:
        if type(e).__name__ not in ('RunError','CompileError') or not hasattr(e,'code'):raise
        print(e.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
