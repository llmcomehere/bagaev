#!/usr/bin/env python3
"""Offline comparison to caller-pinned expectations; no execution or admission."""
import re,sys
from pathlib import Path
import record_text as transport
import record_run_verify as bundle
import record_source_run as run
LIMIT=1048576
FIELDS={'status','value_type','value','reason','location'}
ID=re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')
class ExpectError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise ExpectError(code)
def syntax(receipt_pin,expectation_pin,case):
    need(bundle.pin(receipt_pin) and bundle.pin(expectation_pin),'EXPECT_PIN')
    need(type(case) is str and ID.fullmatch(case) is not None,'EXPECT_CASE')
def read(path):
    try:return transport.read_input(str(path))
    except transport.Refusal as error:
        raise ExpectError('EXPECT_BOUNDS' if error.code=='RECORD_BOUNDS' else 'EXPECT_PATH') from None
def document(raw):
    try:
        value=transport.parse_json(raw)
        need(type(value) is dict and set(value)=={'schema','form','cases'},'EXPECT_DOCUMENT')
        need(value['schema'] in ('bagaev-record-run-expectations/1','bagaev-record-run-expectations/2') and value['form'] in ('record-form/5','record-form/6'),'EXPECT_DOCUMENT')
        raw_mode=value['schema']=='bagaev-record-run-expectations/2'
        cases=value['cases'];need(type(cases) is list and 1<=len(cases)<=256,'EXPECT_DOCUMENT')
        names=set();profile=11 if value['form']=='record-form/5' else 12
        for case in cases:
            need(type(case) is dict and set(case)==({'id','arguments_raw','argument_count','expected'} if raw_mode else {'id','arguments','expected'}),'EXPECT_DOCUMENT')
            name=case['id'];need(type(name) is str and ID.fullmatch(name) is not None and name not in names,'EXPECT_DOCUMENT');names.add(name)
            if raw_mode:
                need(type(case['arguments_raw']) is str and type(case['argument_count']) is int and 0<=case['argument_count']<=8,'EXPECT_DOCUMENT')
                arguments_raw=case['arguments_raw'].encode('utf-8')
                need(len(arguments_raw)<=LIMIT,'EXPECT_DOCUMENT')
                run.preparation.arguments(arguments_raw,case['argument_count'])
            else:need(type(case['arguments']) is list,'EXPECT_DOCUMENT')
            expected=case['expected'];need(type(expected) is dict and set(expected)==FIELDS,'EXPECT_DOCUMENT')
            need(expected['status']!='invalid-ir','EXPECT_DOCUMENT')
            run.result_value(bundle.canonical(dict(expected,schema='bagaev-typed-record-result/'+str(profile),work=1)),profile)
        bundle.canonical(value) # reject unencodable strings, including argument keys
        return value
    except (transport.Refusal,run.RunError,UnicodeError,RecursionError,TypeError,ValueError) as error:
        if isinstance(error,ExpectError):raise
        raise ExpectError('EXPECT_DOCUMENT') from None

def verify(directory,receipt_sha256,expectations,expectation_sha256,case_id):
    syntax(receipt_sha256,expectation_sha256,case_id)
    raw=read(expectations);need(bundle.sha(raw)==expectation_sha256,'EXPECT_DIGEST')
    spec=document(raw);selected=next((c for c in spec['cases'] if c['id']==case_id),None)
    need(selected is not None,'EXPECT_CASE')
    try:
        root=Path(directory).absolute();need('\0' not in str(root),'EXPECT_PATH')
        verified=bundle.verify(root,receipt_sha256)
        arguments=bundle.read(root/'arguments.json',LIMIT);result=bundle.read(root/'reference.stdout',LIMIT)
    except (OSError,TypeError,ValueError) as error:
        if isinstance(error,(ExpectError,bundle.VerifyError)):raise
        raise ExpectError('EXPECT_PATH') from None
    need(bundle.sha(arguments)==verified['arguments_sha256'] and bundle.sha(result)==verified['result_sha256'],'EXPECT_CHANGED')
    actual_form=verified.get('form','record-form/5');need(actual_form==spec['form'],'EXPECT_FORM')
    raw_mode=spec['schema']=='bagaev-record-run-expectations/2'
    if raw_mode:
        need(arguments==selected['arguments_raw'].encode('utf-8'),'EXPECT_ARGUMENTS')
    else:
        try:args=transport.parse_json(arguments)
        except transport.Refusal:raise ExpectError('EXPECT_ARGUMENTS_DOMAIN') from None
        need(bundle.exact(args,selected['arguments']),'EXPECT_ARGUMENTS')
    try:observed=run.result_value(result,11 if actual_form=='record-form/5' else 12)
    except run.RunError:raise bundle.VerifyError('RUN_VERIFY_RESULT') from None
    actual={k:observed[k] for k in sorted(FIELDS)};expected=selected['expected']
    report={'schema':'bagaev-record-run-expectation-verification/1',
      'status':'matched' if bundle.exact(expected,actual) else 'mismatched',
      'form':actual_form,'expectation_sha256':expectation_sha256,'case':case_id,
      'arguments_match':True,'expected':expected,'actual':actual,'run':verified,
      'application_expectation_checked':True,'independent_oracle_verified':False,
      'result_authentication':False,'execution_admission':False,'fresh_run':False}
    if raw_mode:report.update(schema='bagaev-record-run-expectation-verification/2',argument_comparison='raw-utf8')
    return report

def main(argv=None):
    try:
        parser=transport.Parser(add_help=False,allow_abbrev=False)
        parser.add_argument('directory');parser.add_argument('--receipt-sha256',required=True)
        parser.add_argument('--expectations',required=True);parser.add_argument('--expectation-sha256',required=True)
        parser.add_argument('--case',required=True);parser.add_argument('--output',required=True)
        a=parser.parse_args(argv);syntax(a.receipt_sha256,a.expectation_sha256,a.case)
        try:
            output=transport.path_value(a.output)
            need(not output.resolve().is_relative_to(transport.path_value(a.directory).resolve()),'EXPECT_OUTPUT')
            need(not output.exists() and not output.is_symlink(),'EXPECT_OUTPUT')
        except (OSError,ValueError,RuntimeError,transport.Refusal) as error:
            if isinstance(error,ExpectError):raise
            raise ExpectError('EXPECT_OUTPUT') from None
        report=verify(a.directory,a.receipt_sha256,a.expectations,a.expectation_sha256,a.case)
        raw=bundle.canonical(report);need(len(raw)<=LIMIT,'EXPECT_BOUNDS')
        try:transport.write_output(a.output,raw)
        except transport.Refusal:raise ExpectError('EXPECT_OUTPUT') from None
        return 0
    except (transport.Refusal,ExpectError,bundle.VerifyError,run.RunError) as error:
        print(error.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
