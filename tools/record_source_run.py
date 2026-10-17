#!/usr/bin/env python3
"""Retain one explicitly authorized pure run. Identity pins are not authority."""
import hashlib,json,re,sys
from pathlib import Path
import record_text as transport
import record_json_prepare as preparation
import record_source_check as capture_tools
import bagaev_record_wide_form as form

LIMIT=1048576
NAME=re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}')
KEYS={'schema','status','value_type','value','work','reason','location'}
INVALID={'RR_JSON','RR_VERSION','RR_SHAPE','RR_BOUNDS','RR_REFERENCE','RR_CYCLE','RR_TYPE','RR_ARGUMENT'}
FAILURES={'integer-overflow':{'RR_OVERFLOW'},'list-index':{'RR_INDEX'},'work-limit':{'RR_WORK'},
          'record-list-bound':{'RR_RECORD_LIST_ITEMS'},'list-bound':{'RR_LIST_ITEMS','RR_LIST_BYTES'}}
class RunError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise RunError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def integer(value):return type(value) is int and -(2**63)<=value<2**63
def text_value(value):
    return type(value) is str and len(value)<=256 and len(value.encode('utf-8'))<=1024
def result_value(raw,profile=11):
    """Validate wire and coarse value shape, not nominal declarations or expectations."""
    need(type(profile) is int and profile in (11,12),'RUN_FLOW_RESULT')
    need(type(raw) is bytes and len(raw)<=LIMIT,'RUN_FLOW_RESULT')
    try:value=transport.parse_json(raw)
    except transport.Refusal:raise RunError('RUN_FLOW_RESULT') from None
    pending=[value]
    try:
        while pending:
            item=pending.pop()
            if type(item) is str:item.encode('utf-8')
            elif type(item) is list:pending.extend(item)
            elif type(item) is dict:pending.extend(item.keys());pending.extend(item.values())
    except UnicodeError:raise RunError('RUN_FLOW_RESULT') from None
    need(type(value) is dict and set(value)==KEYS,'RUN_FLOW_RESULT')
    need(value['schema']=='bagaev-typed-record-result/'+str(profile) and type(value['status']) is str
         and type(value['work']) is int and 0<=value['work']<=65536,'RUN_FLOW_RESULT')
    status=value['status'];reason=value['reason'];location=value['location'];payload=value['value'];tag=value['value_type']
    if status!='success':
        need(payload is None and tag is None and type(reason) is str and type(location) is str,'RUN_FLOW_RESULT')
        if status=='invalid-ir':
            need(reason in INVALID and value['work']==0 and (location=='' or location.startswith('/')),'RUN_FLOW_RESULT')
        else:
            need(status in FAILURES and reason in FAILURES[status] and value['work']>=1
                 and location.startswith('/program/functions/'),'RUN_FLOW_RESULT')
        return value
    need(reason is None and location is None and value['work']>=1 and type(tag) is str,'RUN_FLOW_RESULT')
    if tag=='Int64':good=integer(payload)
    elif tag=='Bool':good=type(payload) is bool
    elif tag=='Text':good=text_value(payload)
    elif tag=='OptionInt64':good=payload is None or integer(payload)
    elif tag=='TextList':
        good=(type(payload) is list and len(payload)<=64 and all(text_value(x) for x in payload)
              and sum(len(x.encode('utf-8')) for x in payload)<=4096)
    else:
        match=re.fullmatch(r'(Record|RecordList|Variant):([A-Za-z][A-Za-z0-9_]{0,31})',tag)
        need(match is not None,'RUN_FLOW_RESULT')
        if match[1]=='Record':good=type(payload) is dict and len(payload)<=8
        elif match[1]=='RecordList':good=type(payload) is list and len(payload)<=16 and all(type(x) is dict and len(x)<=8 for x in payload)
        else:good=(type(payload) is dict and set(payload)=={'case','value'} and type(payload['case']) is str and NAME.fullmatch(payload['case']) is not None)
    need(good,'RUN_FLOW_RESULT');return value
def write_file(path,raw):
    try:
        with path.open('xb') as stream:need(stream.write(raw)==len(raw),'RUN_FLOW_OUTPUT')
    except OSError:raise RunError('RUN_FLOW_OUTPUT') from None
def input_bytes(path,code):
    try:return transport.read_input(str(path))
    except transport.Refusal:raise RunError(code) from None
def reference_bytes(path,code):
    try:return capture_tools.binary_bytes(path)
    except (capture_tools.FlowError,OSError,ValueError):raise RunError(code) from None
def run_flow(source,arguments,reference,*,source_sha256,arguments_sha256,reference_sha256,output,form_version='5'):
    need(form_version in ('5','6'),'TOOL_USAGE')
    codec=form;profile=11
    if form_version=='6':
        import bagaev_record_json_bool_form as codec
        profile=12
    for pin in (source_sha256,arguments_sha256,reference_sha256):
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}',pin) is not None,'RUN_FLOW_PIN')
    source,arguments,reference,out=[Path(p).absolute() for p in (source,arguments,reference,output)]
    source_raw=input_bytes(source,'RUN_FLOW_INPUT');arguments_raw=input_bytes(arguments,'RUN_FLOW_INPUT')
    need(sha(source_raw)==source_sha256 and sha(arguments_raw)==arguments_sha256,'RUN_FLOW_PIN')
    need(sha(reference_bytes(reference,'RUN_FLOW_PIN'))==reference_sha256,'RUN_FLOW_PIN')
    try:
        decoded=codec.decode(source_raw);entry=decoded['functions'].get(decoded['entry'])
        need(entry is not None and all(param[1]=='Json' for param in entry['params']),'RUN_FLOW_SOURCE')
        program=canonical(decoded)
    except (form.FormError,UnicodeError,ValueError,RecursionError) as error:
        if isinstance(error,RunError):raise
        raise RunError('RUN_FLOW_SOURCE') from None
    try:preparation.arguments(arguments_raw,len(entry['params']))
    except transport.Refusal:raise RunError('RUN_FLOW_ARGUMENTS') from None
    invocation=('{"schema":"bagaev-typed-record-invocation/'+str(profile)+'","program":').encode()+program+b',"arguments":'+arguments_raw+b'}'
    need(len(program)<=LIMIT and len(invocation)<=LIMIT,'RUN_FLOW_INPUT')
    try:out.mkdir()
    except (OSError,ValueError):raise RunError('RUN_FLOW_OUTPUT') from None
    retained={}
    def retain(name,raw):
        write_file(out/name,raw);retained[name]=raw
    for name,raw in [('source.bagaev',source_raw),('arguments.json',arguments_raw),('program.json',program),('invocation.json',invocation)]:
        retain(name,raw)
    try:code,stdout,stderr=capture_tools.capture([str(reference),'run','--input',str(out/'invocation.json')])
    except capture_tools.FlowError as error:
        raise RunError('RUN_FLOW_RESULT' if error.code=='CHECK_FLOW_RESULT' else 'RUN_FLOW_PROCESS') from None
    need(type(stdout) is bytes and len(stdout)<=LIMIT,'RUN_FLOW_RESULT')
    need(type(stderr) is bytes and len(stderr)<=4096,'RUN_FLOW_PROCESS')
    retain('reference.stdout',stdout);retain('reference.stderr',stderr)
    need(type(code) is int and code==0 and stderr==b'','RUN_FLOW_PROCESS')
    result=result_value(stdout,profile)
    need(input_bytes(source,'RUN_FLOW_PRESERVATION')==source_raw
         and input_bytes(arguments,'RUN_FLOW_PRESERVATION')==arguments_raw,'RUN_FLOW_PRESERVATION')
    need(sha(reference_bytes(reference,'RUN_FLOW_PRESERVATION'))==reference_sha256,'RUN_FLOW_PRESERVATION')
    for name,raw in retained.items():
        need(input_bytes(out/name,'RUN_FLOW_PRESERVATION')==raw,'RUN_FLOW_PRESERVATION')
    receipt={'schema':'bagaev-record-source-run/1','status':'completed',
        'source_sha256':source_sha256,'arguments_sha256':arguments_sha256,'program_sha256':sha(program),
        'invocation_sha256':sha(invocation),'result_sha256':sha(stdout),'reference_sha256':reference_sha256,
        'runtime_status':result['status'],'reason':result['reason'],'location':result['location'],'work':result['work'],
        'reference_invoked':True,'execution_admission':False,'result_authentication':False,'application_expectation_checked':False}
    if form_version=='6':receipt.update(schema='bagaev-record-source-run/2',form='record-form/6')
    receipt_raw=canonical(receipt);need(len(receipt_raw)<=LIMIT,'RUN_FLOW_OUTPUT')
    write_file(out/'receipt.json',receipt_raw);return receipt
def main(argv=None):
    try:
        parser=transport.Parser(add_help=False,allow_abbrev=False)
        parser.add_argument('source')
        parser.add_argument('--form',choices=('5','6'),default='5')
        for flag in ('source-sha256','arguments','arguments-sha256','reference','reference-sha256','output'):
            parser.add_argument('--'+flag,required=True)
        a=parser.parse_args(argv)
        receipt=run_flow(a.source,a.arguments,a.reference,source_sha256=a.source_sha256,
                         arguments_sha256=a.arguments_sha256,reference_sha256=a.reference_sha256,output=a.output,form_version=a.form)
        try:print(canonical(receipt).decode('utf-8'),flush=True)
        except (OSError,UnicodeError):raise RunError('RUN_FLOW_DELIVERY') from None
        return 0
    except (transport.Refusal,RunError) as error:
        try:print(error.code,file=sys.stderr)
        except (OSError,UnicodeError):pass
        return 1
if __name__=='__main__':raise SystemExit(main())
