"""Actual pinned checking, deterministic artifact data, and in-process verification."""
import ast,hashlib,json,os,re,stat,sys
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).absolute().parents[1]

LIMIT=1048576
PIN=re.compile(r'[0-9a-f]{64}\Z')
RUNTIMES={'src/bagaev_record_json_view.py':'5649655d5a11c11f8172c4ddcca612ca36a8afe2db40d78a2e628d322ac1a2f9',
          'src/bagaev_record_cpython_runtime.py':'29a82b43abf8e04f061da7a742b8e537589cf97df2354e769ae62bcedc703031'}
_MARKER=object()


class CompileError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)


def need(ok,code):
    if not ok:raise CompileError(code)


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return backend.canonical(value)


def read(path,limit,code='CPY_INPUT'):
    try:
        need(stat.S_ISREG(path.lstat().st_mode),code)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            need(stat.S_ISREG(info.st_mode) and info.st_size<=limit,code)
            raw=stream.read(limit+1)
        need(len(raw)<=limit,code)
        return raw
    except (OSError,ValueError) as error:
        if isinstance(error,CompileError):raise
        raise CompileError(code) from None


def closure():
    modules={}
    try:
        need(all(stat.S_ISDIR(p.lstat().st_mode) for p in (ROOT,*ROOT.parents)),'CPY_INPUT')
        for directory in ('src','tools'):
            base=ROOT/directory;need(stat.S_ISDIR(base.lstat().st_mode),'CPY_INPUT')
            for path in sorted(base.glob('*.py')):
                name=path.stem
                need(name not in modules and name not in sys.stdlib_module_names,'CPY_INPUT')
                modules[name]=str(path.relative_to(ROOT))
        pending=['record_source_cpython'];files={}
        while pending:
            name=pending.pop();need(name in modules,'CPY_INPUT');relative=modules[name]
            if relative in files:continue
            raw=read(ROOT/relative,LIMIT);files[relative]=raw
            need(len(files)<=64 and sum(map(len,files.values()))<=8*LIMIT,'CPY_INPUT')
            tree=ast.parse(raw.decode('utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):names=[item.name for item in node.names]
                elif isinstance(node,ast.ImportFrom):
                    need(node.level==0 and node.module is not None,'CPY_INPUT');names=[node.module]
                else:continue
                for imported in names:
                    top=imported.split('.')[0]
                    if top in modules:
                        need(imported==top,'CPY_INPUT');pending.append(top)
                    else:need(top in sys.stdlib_module_names,'CPY_INPUT')
        for relative,pin in RUNTIMES.items():
            raw=read(ROOT/relative,LIMIT);need(sha(raw)==pin,'CPY_PIN');files[relative]=raw
        need(len(files)<=64 and sum(map(len,files.values()))<=8*LIMIT,'CPY_INPUT')
        # Runtime imports are covered too, even though their source is embedded
        # as data rather than imported by this compiler operation.
        for raw in files.values():
            for node in ast.walk(ast.parse(raw.decode('utf-8'))):
                if isinstance(node,ast.Import):names=[item.name for item in node.names]
                elif isinstance(node,ast.ImportFrom):
                    need(node.level==0 and node.module is not None,'CPY_INPUT');names=[node.module]
                else:continue
                for imported in names:
                    top=imported.split('.')[0]
                    if top in modules:need(imported==top and modules[top] in files,'CPY_INPUT')
                    else:need(top in sys.stdlib_module_names,'CPY_INPUT')
        return files
    except (OSError,UnicodeError,SyntaxError,ValueError,RecursionError) as error:
        if isinstance(error,CompileError):raise
        raise CompileError('CPY_INPUT') from None


# Explicit fresh-source-load profile: no cached project modules or bytecode.
# A caller still must authorize and pin this source before importing it.
need(sys.dont_write_bytecode and not sys.flags.optimize,'CPY_INPUT')
_INITIAL_FILES=closure()
for relative in _INITIAL_FILES:
    name=Path(relative).stem
    need(name not in sys.modules or sys.modules[name] is sys.modules.get(__name__),'CPY_INPUT')
for directory in (ROOT/'src',ROOT/'tools'):
    need(not (directory/'__pycache__').exists() and not (directory/'__pycache__').is_symlink()
         and not list(directory.glob('*.pyc')),'CPY_INPUT')
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'src'))
import bagaev_record_wide_form as form
import bagaev_record_cpython_backend as backend
import record_source_check as checking
import record_text as transport


def loaded_closure(code='CPY_CHANGED'):
    try:
        current=closure();need(current==_INITIAL_FILES,code)
        for relative in current:
            module=sys.modules.get(Path(relative).stem)
            if module is not None:
                need(Path(module.__file__).absolute()==ROOT/relative,code)
        return current
    except (CompileError,OSError,ValueError,TypeError,AttributeError):
        raise CompileError(code) from None


loaded_closure('CPY_INPUT')


def checker_result(raw,program_hash):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('duplicate key')
            value[key]=item
        return value
    def constant(_):raise ValueError('non-JSON constant')
    try:
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=constant)
        need(type(value) is dict and set(value)=={'schema','status','input_sha256','program_sha256',
             'reason','location','execution_admission'},'CPY_CHECKER')
        for item in value.values():
            if type(item) is str:item.encode('utf-8')
        need(type(value['schema']) is str and value['schema']=='bagaev-record-source-check/11'
             and type(value['input_sha256']) is str and value['input_sha256']==program_hash
             and value['execution_admission'] is False and type(value['status']) is str,'CPY_CHECKER')
        if value['status']=='checked':
            need(type(value['program_sha256']) is str and value['program_sha256']==program_hash
                 and value['reason'] is None and value['location'] is None,'CPY_CHECKER')
            return
        if value['status']=='refused':
            need(value['program_sha256'] is None and type(value['reason']) is str
                 and value['reason'] in {'RR_JSON','RR_VERSION','RR_SHAPE','RR_BOUNDS','RR_REFERENCE','RR_CYCLE','RR_TYPE'}
                 and type(value['location']) is str and (value['location']=='' or value['location'].startswith('/')),'CPY_CHECKER')
            raise CompileError('CPY_CHECK_REFUSED')
        raise CompileError('CPY_CHECKER')
    except (ValueError,UnicodeError,RecursionError) as error:
        if isinstance(error,CompileError):raise
        raise CompileError('CPY_CHECKER') from None


def artifact(program_raw,files):
    try:
        program=json.loads(program_raw)
        python=backend.lower_checked(program,files['src/bagaev_record_json_view.py'],
                                     files['src/bagaev_record_cpython_runtime.py'])
        ast.parse(python.decode('utf-8'))
        generator=sha(canonical({name:sha(raw) for name,raw in files.items() if name not in RUNTIMES}))
        runtime=sha(canonical({name:sha(files[name]) for name in RUNTIMES}))
        result=canonical({'schema':'bagaev-record-cpython/1','profile':'bagaev-typed-record/11',
                          'program_sha256':sha(program_raw),'generator_sha256':generator,
                          'runtime_sha256':runtime,'python':python.decode('utf-8')})
        need(len(python)<=LIMIT and len(result)<=4*LIMIT,'CPY_ARTIFACT_BOUNDS')
        return result,python,generator,runtime
    except backend.LoweringError as error:raise CompileError(error.code) from None
    except (UnicodeError,SyntaxError,ValueError,TypeError,KeyError,RecursionError) as error:
        if isinstance(error,CompileError):raise
        raise CompileError('CPY_UNSUPPORTED') from None


@dataclass(frozen=True)
class _Compiled:
    program: bytes
    artifact: bytes
    python: bytes
    marker: object


def compile_flow(source_path,checker_path,source_sha256,checker_sha256,output):
    for pin in (source_sha256,checker_sha256):need(type(pin) is str and PIN.fullmatch(pin),'CPY_PIN')
    try:source,checker,out=[Path(p).absolute() for p in (source_path,checker_path,output)]
    except (TypeError,ValueError):raise CompileError('CPY_INPUT') from None
    source_raw=read(source,LIMIT);need(sha(source_raw)==source_sha256,'CPY_PIN')
    checker_raw=read(checker,32*LIMIT);need(sha(checker_raw)==checker_sha256,'CPY_PIN')
    try:
        program_raw=canonical(form.decode(source_raw))
        need(len(program_raw)<=LIMIT,'CPY_PROFILE')
    except (ValueError,UnicodeError,RecursionError):raise CompileError('CPY_PROFILE') from None
    files=loaded_closure()
    try:out.mkdir()
    except (OSError,ValueError):raise CompileError('CPY_OUTPUT') from None
    retained={}
    def write(name,raw):
        try:
            with (out/name).open('xb') as stream:need(stream.write(raw)==len(raw),'CPY_OUTPUT')
        except OSError:raise CompileError('CPY_OUTPUT') from None
        retained[name]=raw
    write('source.bagaev',source_raw);write('program.json',program_raw)
    try:captured=checking.capture([str(checker),'check','--input',str(out/'program.json')])
    except (checking.FlowError,OSError):raise CompileError('CPY_CHECKER') from None
    need(type(captured) is tuple and len(captured)==3,'CPY_CHECKER')
    code,stdout,stderr=captured
    need(type(stdout) is bytes and type(stderr) is bytes
         and len(stdout)<=LIMIT and len(stderr)<=4096,'CPY_CHECKER')
    write('checker.stdout',stdout);write('checker.stderr',stderr)
    need(type(code) is int and code==0 and stderr==b'','CPY_CHECKER')
    checker_result(stdout,sha(program_raw))
    result,python,generator,runtime=artifact(program_raw,files)
    write('artifact.json',result)
    def preserved():
        try:
            need(read(source,LIMIT)==source_raw and read(checker,32*LIMIT)==checker_raw,'CPY_CHANGED')
            need(loaded_closure()==files,'CPY_CHANGED')
            need(stat.S_ISDIR(out.lstat().st_mode) and {p.name for p in out.iterdir()}==set(retained),'CPY_CHANGED')
            for name,raw in retained.items():need(read(out/name,max(len(raw),1),'CPY_CHANGED')==raw,'CPY_CHANGED')
        except (CompileError,OSError):raise CompileError('CPY_CHANGED') from None
    preserved()
    receipt={'schema':'bagaev-record-cpython-compile/1','status':'compiled','form':'record-form/5',
             'source_sha256':source_sha256,'program_sha256':sha(program_raw),'checker_sha256':checker_sha256,
             'generator_sha256':generator,'runtime_sha256':runtime,'artifact_sha256':sha(result),
             'python_sha256':sha(python),'checker_invoked':True,'generated_code_executed':False,'execution_admission':False}
    write('receipt.json',canonical(receipt));preserved()
    return _Compiled(program_raw,result,python,_MARKER),receipt


def verify_artifact(raw,compiled):
    try:
        need(type(raw) is bytes and len(raw)<=4*LIMIT and type(compiled) is _Compiled
             and compiled.marker is _MARKER,'CPY_ARTIFACT')
        files=loaded_closure();expected,python,_,_=artifact(compiled.program,files)
        need(raw==expected==compiled.artifact and python==compiled.python,'CPY_ARTIFACT')
        return python
    except (CompileError,OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
        raise CompileError('CPY_ARTIFACT') from None
