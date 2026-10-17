#!/usr/bin/env python3
"""Offline consistency only. No source, checker or reference execution."""
import hashlib,json,os,re,stat,sys
from pathlib import Path
import record_text as transport
import record_source_run as run
class VerifyError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise VerifyError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def exact(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b
def read(path,limit):
    try:
        need(stat.S_ISREG(path.lstat().st_mode),'RUN_VERIFY_PATH')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode),'RUN_VERIFY_PATH')
            raw=stream.read(limit+1)
        need(len(raw)<=limit,'RUN_VERIFY_BOUNDS');return raw
    except OSError:raise VerifyError('RUN_VERIFY_PATH') from None
def verify(directory,receipt_sha256):
    need(pin(receipt_sha256),'RUN_VERIFY_PIN');root=Path(directory).absolute()
    try:
        need(stat.S_ISDIR(root.lstat().st_mode),'RUN_VERIFY_PATH');names=set()
        with os.scandir(root) as entries:
            for item in entries:
                names.add(item.name);need(len(names)<=7,'RUN_VERIFY_PATH')
    except OSError:raise VerifyError('RUN_VERIFY_PATH') from None
    expected={'source.bagaev','arguments.json','program.json','invocation.json','reference.stdout','reference.stderr','receipt.json'}
    need(names==expected,'RUN_VERIFY_PATH')
    data={name:read(root/name,4096 if name=='reference.stderr' else run.LIMIT) for name in sorted(expected)}
    need(sha(data['receipt.json'])==receipt_sha256,'RUN_VERIFY_PIN')
    try:
        receipt=transport.parse_json(data['receipt.json'])
        canonical(receipt)
    except (transport.Refusal,UnicodeError,ValueError,RecursionError):raise VerifyError('RUN_VERIFY_RECEIPT') from None
    fields={'schema','status','source_sha256','arguments_sha256','program_sha256','invocation_sha256',
      'result_sha256','reference_sha256','runtime_status','reason','location','work','reference_invoked',
      'execution_admission','result_authentication','application_expectation_checked'}
    need(type(receipt) is dict,'RUN_VERIFY_RECEIPT')
    form6=receipt.get('schema')=='bagaev-record-source-run/2'
    need(set(receipt)==fields|({'form'} if form6 else set()),'RUN_VERIFY_RECEIPT')
    need(not form6 or receipt['form']=='record-form/6','RUN_VERIFY_RECEIPT')
    need(receipt['schema']==('bagaev-record-source-run/2' if form6 else 'bagaev-record-source-run/1') and receipt['status']=='completed'
      and receipt['reference_invoked'] is True and receipt['execution_admission'] is False
      and receipt['result_authentication'] is False and receipt['application_expectation_checked'] is False,'RUN_VERIFY_RECEIPT')
    for key in ('source','arguments','program','invocation','result','reference'):
        need(pin(receipt[key+'_sha256']),'RUN_VERIFY_RECEIPT')
    need(type(receipt['runtime_status']) is str and type(receipt['work']) is int
      and (receipt['reason'] is None or type(receipt['reason']) is str)
      and (receipt['location'] is None or type(receipt['location']) is str),'RUN_VERIFY_RECEIPT')
    need(sha(data['source.bagaev'])==receipt['source_sha256'],'RUN_VERIFY_SOURCE')
    codec=run.form;profile=11
    if form6:
        import bagaev_record_json_bool_form as codec
        profile=12
    try:
        decoded=codec.decode(data['source.bagaev']);entry=decoded['functions'].get(decoded['entry'])
        need(entry is not None and all(p[1]=='Json' for p in entry['params']),'RUN_VERIFY_SOURCE')
        program=canonical(decoded)
    except (run.form.FormError,UnicodeError,ValueError,RecursionError) as error:
        if isinstance(error,VerifyError):raise
        raise VerifyError('RUN_VERIFY_SOURCE') from None
    need(data['program.json']==program and sha(program)==receipt['program_sha256'],'RUN_VERIFY_SOURCE')
    arguments=data['arguments.json'];need(sha(arguments)==receipt['arguments_sha256'],'RUN_VERIFY_ARGUMENTS')
    try:run.preparation.arguments(arguments,len(entry['params']))
    except transport.Refusal:raise VerifyError('RUN_VERIFY_ARGUMENTS') from None
    invocation=('{"schema":"bagaev-typed-record-invocation/'+str(profile)+'","program":').encode()+program+b',"arguments":'+arguments+b'}'
    need(len(invocation)<=run.LIMIT,'RUN_VERIFY_BOUNDS')
    need(data['invocation.json']==invocation and sha(invocation)==receipt['invocation_sha256'],'RUN_VERIFY_INVOCATION')
    stdout=data['reference.stdout']
    need(data['reference.stderr']==b'' and sha(stdout)==receipt['result_sha256'],'RUN_VERIFY_RESULT')
    try:result=run.result_value(stdout,profile)
    except run.RunError:raise VerifyError('RUN_VERIFY_RESULT') from None
    for key in ('status','reason','location','work'):
        need(exact(result[key],receipt['runtime_status' if key=='status' else key]),'RUN_VERIFY_RESULT')
    report={'schema':'bagaev-record-run-verification/1','status':'consistent','receipt_sha256':receipt_sha256,
      'source_sha256':sha(data['source.bagaev']),'arguments_sha256':sha(arguments),'program_sha256':sha(program),
      'invocation_sha256':sha(invocation),'result_sha256':sha(stdout),'claimed_reference_sha256':receipt['reference_sha256'],
      'runtime_status':result['status'],'reason':result['reason'],'location':result['location'],'work':result['work'],
      'fresh_run':False,'reference_invoked':False,'result_authentication':False,
      'execution_admission':False,'application_expectation_checked':False}
    if form6:report.update(schema='bagaev-record-run-verification/2',form='record-form/6')
    return report
def main(argv=None):
    try:
        parser=transport.Parser(add_help=False,allow_abbrev=False);parser.add_argument('directory')
        parser.add_argument('--receipt-sha256',required=True);parser.add_argument('--output',required=True)
        a=parser.parse_args(argv)
        try:need(not Path(a.output).resolve().is_relative_to(Path(a.directory).resolve()),'RUN_VERIFY_OUTPUT')
        except (OSError,ValueError,RuntimeError) as error:
            if isinstance(error,VerifyError):raise
            raise VerifyError('RUN_VERIFY_OUTPUT') from None
        result=verify(a.directory,a.receipt_sha256);raw=canonical(result)
        need(len(raw)<=run.LIMIT,'RUN_VERIFY_BOUNDS')
        try:transport.write_output(a.output,raw)
        except transport.Refusal:raise VerifyError('RUN_VERIFY_OUTPUT') from None
        return 0
    except (transport.Refusal,VerifyError) as error:
        print(error.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
