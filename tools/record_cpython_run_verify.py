"""Offline retained-run consistency, never checking or executing artifact code."""
import argparse,hashlib,json,os,re,stat,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).absolute().parents[1]/'src'))
import bagaev_record_wide_form as form
import bagaev_record_json_view as view
import record_cpython_run as runtime
LIMIT=1048576
FILES={'arguments.json':LIMIT,'compiled/artifact.json':4*LIMIT,'compiled/checker.stderr':4096,
 'compiled/checker.stdout':LIMIT,'compiled/program.json':LIMIT,'compiled/receipt.json':65536,
 'compiled/source.bagaev':LIMIT,'receipt.json':65536,'result.stdout':8*LIMIT}
DIGESTS={'source_sha256','program_sha256','arguments_sha256','checker_sha256','compile_receipt_sha256',
 'artifact_sha256','python_sha256','generator_sha256','runtime_sha256','runner_sha256','result_sha256'}
RUN_FIELDS=DIGESTS|{'schema','status','form','result_status','checker_invoked','generated_program_invocations','execution_admission'}
COMPILE_DIGESTS={'source_sha256','program_sha256','checker_sha256','artifact_sha256','python_sha256','generator_sha256','runtime_sha256'}
COMPILE_FIELDS=COMPILE_DIGESTS|{'schema','status','form','checker_invoked','generated_code_executed','execution_admission'}
STATUSES={'success','integer-overflow','list-index','work-limit','record-list-bound','list-bound'}
class VerifyError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise VerifyError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def pin(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def pins(values):
    for value in values:need(pin(value),'CPY_VERIFY_PIN')
def metadata(raw,code,canonical_required=True):
    def pairs(items):
        obj={}
        for k,v in items:
            if k in obj:raise ValueError('duplicate key')
            obj[k]=v
        return obj
    def bad(_):raise ValueError('noninteger number')
    try:
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_float=bad,parse_constant=bad)
        need(type(value) is dict,code)
        pending=[value]
        while pending:
            item=pending.pop()
            if type(item) is str:item.encode('utf-8')
            elif type(item) is list:pending.extend(item)
            elif type(item) is dict:pending.extend(item.keys());pending.extend(item.values())
        if canonical_required:need(canonical(value)==raw,code)
        return value
    except (ValueError,UnicodeError,TypeError,RecursionError) as e:
        if isinstance(e,VerifyError):raise
        raise VerifyError(code) from None

def scan(root):
    try:
        for parent in reversed((root,*root.parents)):need(stat.S_ISDIR(parent.lstat().st_mode),'CPY_VERIFY_PATH')
        def names(path,expected):
            found=set()
            with os.scandir(path) as entries:
                for item in entries:
                    found.add(item.name);need(len(found)<=len(expected),'CPY_VERIFY_PATH')
            need(found==expected,'CPY_VERIFY_PATH')
        names(root,{'compiled','arguments.json','result.stdout','receipt.json'})
        need(stat.S_ISDIR((root/'compiled').lstat().st_mode),'CPY_VERIFY_PATH')
        for n in ('arguments.json','result.stdout','receipt.json'):need(stat.S_ISREG((root/n).lstat().st_mode),'CPY_VERIFY_PATH')
        names(root/'compiled',{'source.bagaev','program.json','checker.stdout','checker.stderr','artifact.json','receipt.json'})
        for n in sorted(FILES):need(stat.S_ISREG((root/n).lstat().st_mode),'CPY_VERIFY_PATH')
    except (OSError,ValueError) as e:
        if isinstance(e,VerifyError):raise
        raise VerifyError('CPY_VERIFY_PATH') from None

def read(path,limit):
    try:
        need(stat.S_ISREG(path.lstat().st_mode),'CPY_VERIFY_PATH')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            need(stat.S_ISREG(os.fstat(f.fileno()).st_mode),'CPY_VERIFY_PATH');raw=f.read(limit+1)
        need(len(raw)<=limit,'CPY_VERIFY_BOUNDS');return raw
    except (OSError,ValueError) as e:
        if isinstance(e,VerifyError):raise
        raise VerifyError('CPY_VERIFY_PATH') from None

def preserved(root,data):
    try:
        scan(root)
        for n in sorted(FILES):need(read(root/n,FILES[n])==data[n],'CPY_VERIFY_CHANGED')
    except (VerifyError,OSError,ValueError):raise VerifyError('CPY_VERIFY_CHANGED') from None

def metrics(value):
    count=depth=0;pending=[(value,1)]
    while pending:
        item,level=pending.pop();count+=1;depth=max(depth,level)
        if type(item) is list:pending.extend((v,level+1) for v in item)
        elif type(item) is dict:pending.extend((v,level+1) for v in item.values())
    return count,depth

def verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256):
    pins((receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256))
    try:root=Path(directory).absolute()
    except (TypeError,ValueError,OSError):raise VerifyError('CPY_VERIFY_PATH') from None
    scan(root);data={n:read(root/n,FILES[n]) for n in sorted(FILES)}
    need(sha(data['receipt.json'])==receipt_sha256,'CPY_VERIFY_PIN')
    receipt=metadata(data['receipt.json'],'CPY_VERIFY_RECEIPT')
    need(set(receipt)==RUN_FIELDS and all(pin(receipt[n]) for n in DIGESTS),'CPY_VERIFY_RECEIPT')
    need(receipt['schema']=='bagaev-record-cpython-run/1' and receipt['status']=='executed' and receipt['form']=='record-form/5'
      and receipt['checker_invoked'] is True and type(receipt['generated_program_invocations']) is int
      and receipt['generated_program_invocations']==1 and receipt['execution_admission'] is False
      and type(receipt['result_status']) is str and receipt['result_status'] in STATUSES,'CPY_VERIFY_RECEIPT')
    for key,want in [('source_sha256',source_sha256),('program_sha256',program_sha256),('arguments_sha256',arguments_sha256),('runner_sha256',runner_sha256)]:
        need(receipt[key]==want,'CPY_VERIFY_PIN')
    source=data['compiled/source.bagaev'];program_raw=data['compiled/program.json']
    need(sha(source)==source_sha256 and sha(program_raw)==program_sha256,'CPY_VERIFY_SOURCE')
    try:
        program=form.decode(source);entry=program['functions'].get(program['entry'])
        need(program['schema']=='bagaev-typed-record/11' and entry is not None and all(p[1]=='Json' for p in entry['params']),'CPY_VERIFY_SOURCE')
        need(canonical(program)==program_raw,'CPY_VERIFY_SOURCE');sv,sd=metrics(program)
    except (ValueError,UnicodeError,TypeError,KeyError,AttributeError,RecursionError) as e:
        if isinstance(e,VerifyError):raise
        raise VerifyError('CPY_VERIFY_SOURCE') from None
    need(sv<=8192 and sd<=128,'CPY_VERIFY_BOUNDS')
    arguments=data['arguments.json'];need(sha(arguments)==arguments_sha256,'CPY_VERIFY_ARGUMENTS')
    need(70+len(program_raw)+len(arguments)<=LIMIT,'CPY_VERIFY_BOUNDS')
    try:observed=view.parse(arguments)
    except view.JsonInputError as e:raise VerifyError('CPY_VERIFY_BOUNDS' if e.code=='JP_BOUNDS' else 'CPY_VERIFY_ARGUMENTS') from None
    try:av,ad=metrics(json.loads(arguments.decode('utf-8'),parse_int=lambda _:None,parse_float=lambda _:None))
    except (ValueError,UnicodeError,RecursionError):raise VerifyError('CPY_VERIFY_ARGUMENTS') from None
    need(sv+av+2<=16384 and 1+max(sd,ad,1)<=132,'CPY_VERIFY_BOUNDS')
    need(observed.kind()=='array' and observed.length()==len(entry['params']),'CPY_VERIFY_ARGUMENTS')
    raw=data['compiled/receipt.json'];need(sha(raw)==receipt['compile_receipt_sha256'],'CPY_VERIFY_RECEIPT')
    compilation=metadata(raw,'CPY_VERIFY_RECEIPT')
    need(set(compilation)==COMPILE_FIELDS and all(pin(compilation[n]) for n in COMPILE_DIGESTS),'CPY_VERIFY_RECEIPT')
    need(compilation['schema']=='bagaev-record-cpython-compile/1' and compilation['status']=='compiled'
      and compilation['form']=='record-form/5' and compilation['checker_invoked'] is True
      and compilation['generated_code_executed'] is False and compilation['execution_admission'] is False,'CPY_VERIFY_RECEIPT')
    need(all(compilation[n]==receipt[n] for n in COMPILE_DIGESTS),'CPY_VERIFY_RECEIPT')
    report=metadata(data['compiled/checker.stdout'],'CPY_VERIFY_CHECKER',False)
    need(report=={'schema':'bagaev-record-source-check/11','status':'checked','input_sha256':program_sha256,
      'program_sha256':program_sha256,'reason':None,'location':None,'execution_admission':False}
      and report['execution_admission'] is False and data['compiled/checker.stderr']==b'','CPY_VERIFY_CHECKER')
    raw=data['compiled/artifact.json'];need(sha(raw)==receipt['artifact_sha256'],'CPY_VERIFY_ARTIFACT')
    artifact=metadata(raw,'CPY_VERIFY_ARTIFACT')
    need(set(artifact)=={'schema','profile','program_sha256','generator_sha256','runtime_sha256','python'},'CPY_VERIFY_ARTIFACT')
    need(artifact['schema']=='bagaev-record-cpython/1' and artifact['profile']=='bagaev-typed-record/11'
      and all(pin(artifact[n]) and artifact[n]==receipt[n] for n in ('program_sha256','generator_sha256','runtime_sha256'))
      and type(artifact['python']) is str,'CPY_VERIFY_ARTIFACT')
    python=artifact['python'].encode('utf-8');need(len(python)<=LIMIT and sha(python)==receipt['python_sha256'],'CPY_VERIFY_ARTIFACT')
    raw=data['result.stdout'];need(sha(raw)==receipt['result_sha256'],'CPY_VERIFY_RESULT')
    try:result=runtime.result_value(raw)
    except runtime.RunError:raise VerifyError('CPY_VERIFY_RESULT') from None
    need(result['status']==receipt['result_status'],'CPY_VERIFY_RESULT')
    output={'schema':'bagaev-record-cpython-run-verification/1','status':'consistent',
      'receipt_sha256':receipt_sha256,'source_sha256':source_sha256,'program_sha256':program_sha256,
      'arguments_sha256':arguments_sha256,'runner_sha256':runner_sha256,'artifact_sha256':receipt['artifact_sha256'],
      'result_sha256':receipt['result_sha256'],'claimed_checker_sha256':receipt['checker_sha256'],
      'result_status':result['status'],'work':result['work'],'fresh_run':False,'checker_invoked':False,
      'generated_program_invocations':0,'result_authentication':False,'execution_admission':False,
      'application_expectation_checked':False}
    preserved(root,data);return output,root,data

def verify(directory,*,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256):
    return verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256)[0]

HELP='''Verify retained CPython run consistency without executing code or invoking a checker.
Usage: record_cpython_run_verify.py DIRECTORY --receipt-sha256 SHA256 --source-sha256 SHA256 --program-sha256 SHA256 --arguments-sha256 SHA256 --runner-sha256 SHA256 --output NEW_REPORT
Consistency is not authentication, freshness, admission or application acceptance.
'''
class Usage(ValueError):pass
class Parser(argparse.ArgumentParser):
    def error(self,message):raise Usage()
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv in (['--help'],['-h']):print(HELP,end='');return 0
    try:
        p=Parser(add_help=False,allow_abbrev=False);p.add_argument('directory')
        for n in ('receipt-sha256','source-sha256','program-sha256','arguments-sha256','runner-sha256','output'):p.add_argument('--'+n,required=True)
        a=p.parse_args(argv)
    except Usage:print('CPY_USAGE',file=sys.stderr);return 2
    try:
        values=(a.receipt_sha256,a.source_sha256,a.program_sha256,a.arguments_sha256,a.runner_sha256);pins(values)
        try:
            target=Path(a.output).absolute();need(not target.resolve().is_relative_to(Path(a.directory).resolve()),'CPY_VERIFY_OUTPUT')
            try:target.lstat()
            except FileNotFoundError:pass
            else:raise VerifyError('CPY_VERIFY_OUTPUT')
        except (OSError,ValueError,RuntimeError) as e:
            if isinstance(e,VerifyError):raise
            raise VerifyError('CPY_VERIFY_OUTPUT') from None
        report,root,data=verify_data(a.directory,*values);raw=canonical(report);need(len(raw)<=65536,'CPY_VERIFY_BOUNDS')
        try:
            with target.open('xb') as f:need(f.write(raw)==len(raw),'CPY_VERIFY_OUTPUT')
        except (OSError,ValueError) as e:
            if isinstance(e,VerifyError):raise
            raise VerifyError('CPY_VERIFY_OUTPUT') from None
        preserved(root,data)
        try:need(read(target,65536)==raw,'CPY_VERIFY_OUTPUT')
        except VerifyError:raise VerifyError('CPY_VERIFY_OUTPUT') from None
        return 0
    except VerifyError as e:print(e.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
