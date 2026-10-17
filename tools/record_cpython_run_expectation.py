"""Compare pinned application expectations with retained CPython data only."""
import argparse,re,stat,sys
from pathlib import Path
import record_cpython_run_verify as run
import record_run_expectation as spec
LIMIT=1048576
REPORT_LIMIT=8*LIMIT
FIELDS={'status','value_type','value','reason','location'}
class ExpectError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise ExpectError(code)
def syntax(receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256,expectation_sha256,case_id):
    for value in (receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256,expectation_sha256):
        need(run.pin(value),'CPY_EXPECT_PIN')
    need(type(case_id) is str and re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}',case_id) is not None,'CPY_EXPECT_CASE')
def read_expectation(path):
    try:
        for p in reversed(path.parents):need(stat.S_ISDIR(p.lstat().st_mode),'CPY_EXPECT_PATH')
        return run.read(path,LIMIT)
    except run.VerifyError as e:
        raise ExpectError('CPY_EXPECT_BOUNDS' if e.code=='CPY_VERIFY_BOUNDS' else 'CPY_EXPECT_PATH') from None
    except (OSError,ValueError) as e:
        if isinstance(e,ExpectError):raise
        raise ExpectError('CPY_EXPECT_PATH') from None
def document(raw):
    try:value=spec.document(raw)
    except spec.ExpectError:raise ExpectError('CPY_EXPECT_DOCUMENT') from None
    need(value['schema']=='bagaev-record-run-expectations/2' and value['form']=='record-form/5','CPY_EXPECT_DOCUMENT')
    return value
def report_bytes(report):
    try:raw=run.canonical(report)
    except (ValueError,TypeError,UnicodeError,RecursionError):raise ExpectError('CPY_EXPECT_REPORT') from None
    need(len(raw)<=REPORT_LIMIT,'CPY_EXPECT_BOUNDS');return raw
def preserved(path,raw,root,data):
    try:need(read_expectation(path)==raw,'CPY_EXPECT_CHANGED')
    except (ExpectError,OSError,ValueError):raise ExpectError('CPY_EXPECT_CHANGED') from None
    run.preserved(root,data)
def verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256,expectations,expectation_sha256,case_id):
    syntax(receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256,expectation_sha256,case_id)
    try:path=Path(expectations).absolute()
    except (TypeError,ValueError,OSError):raise ExpectError('CPY_EXPECT_PATH') from None
    raw=read_expectation(path);need(run.sha(raw)==expectation_sha256,'CPY_EXPECT_DIGEST')
    expected_document=document(raw);case=next((x for x in expected_document['cases'] if x['id']==case_id),None)
    need(case is not None,'CPY_EXPECT_CASE')
    inner,root,data=run.verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256)
    need(data['arguments.json']==case['arguments_raw'].encode('utf-8'),'CPY_EXPECT_ARGUMENTS')
    try:observed=run.runtime.result_value(data['result.stdout'])
    except run.runtime.RunError:raise run.VerifyError('CPY_VERIFY_RESULT') from None
    actual={k:observed[k] for k in sorted(FIELDS)};expected=case['expected']
    report={'schema':'bagaev-record-cpython-expectation-verification/1',
      'status':'matched' if spec.bundle.exact(expected,actual) else 'mismatched','form':'record-form/5',
      'expectation_sha256':expectation_sha256,'case':case_id,'argument_comparison':'raw-utf8','arguments_match':True,
      'expected':expected,'actual':actual,'run':inner,'application_expectation_checked':True,
      'independent_oracle_verified':False,'result_authentication':False,'execution_admission':False,
      'fresh_run':False,'checker_invoked':False,'generated_program_invocations':0}
    encoded=report_bytes(report);preserved(path,raw,root,data)
    return report,encoded,path,raw,root,data
def verify(directory,*,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256,expectations,expectation_sha256,case_id):
    return verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256,expectations,expectation_sha256,case_id)[0]
HELP='''Compare a retained CPython run with a pinned raw-argument expectation offline.
Usage: record_cpython_run_expectation.py DIRECTORY --receipt-sha256 SHA256 --source-sha256 SHA256 --program-sha256 SHA256 --arguments-sha256 SHA256 --runner-sha256 SHA256 --expectations FILE --expectation-sha256 SHA256 --case CASE --output NEW_REPORT
Exit zero means comparison completed; inspect matched or mismatched status.
No execution, authentication, admission or independent-oracle claim.
'''
class Usage(ValueError):pass
class Parser(argparse.ArgumentParser):
    def error(self,message):raise Usage()
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv in (['--help'],['-h']):print(HELP,end='');return 0
    try:
        p=Parser(add_help=False,allow_abbrev=False);p.add_argument('directory')
        for name in ('receipt-sha256','source-sha256','program-sha256','arguments-sha256','runner-sha256','expectations','expectation-sha256','case','output'):p.add_argument('--'+name,required=True)
        a=p.parse_args(argv)
    except Usage:print('CPY_USAGE',file=sys.stderr);return 2
    pins=(a.receipt_sha256,a.source_sha256,a.program_sha256,a.arguments_sha256,a.runner_sha256)
    try:
        syntax(*pins,a.expectation_sha256,a.case)
        try:
            target=Path(a.output).absolute()
            need(not target.resolve().is_relative_to(Path(a.directory).resolve()) and target.resolve()!=Path(a.expectations).resolve(),'CPY_EXPECT_OUTPUT')
            try:target.lstat()
            except FileNotFoundError:pass
            else:raise ExpectError('CPY_EXPECT_OUTPUT')
        except (OSError,ValueError,RuntimeError) as e:
            if isinstance(e,ExpectError):raise
            raise ExpectError('CPY_EXPECT_OUTPUT') from None
        report,encoded,path,raw,root,data=verify_data(a.directory,*pins,a.expectations,a.expectation_sha256,a.case)
        try:
            with target.open('xb') as f:need(f.write(encoded)==len(encoded),'CPY_EXPECT_OUTPUT')
        except (OSError,ValueError) as e:
            if isinstance(e,ExpectError):raise
            raise ExpectError('CPY_EXPECT_OUTPUT') from None
        preserved(path,raw,root,data)
        try:need(run.read(target,REPORT_LIMIT)==encoded,'CPY_EXPECT_OUTPUT')
        except run.VerifyError:raise ExpectError('CPY_EXPECT_OUTPUT') from None
        return 0
    except (ExpectError,run.VerifyError) as e:print(e.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
