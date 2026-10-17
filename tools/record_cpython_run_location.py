"""Describe a retained profile11 failure in pinned source; never execute code."""
import argparse,re,sys
from pathlib import Path
import record_cpython_run_verify as run
# The runner's import profile removes the first search path. Restore only this
# checkout's source directory before loading the data-only source mapper.
sys.path.insert(0, str(Path(__file__).absolute().parents[1] / 'src'))
import bagaev_record_wide_spans as spans
REPORT_LIMIT=65536
HEADER={'schema','form','source_sha256','program_pin','semantic_check','execution_admission','locations'}
ROW={'program_pointer','operation','precision','start_byte','end_byte','start_line','start_column','end_line','end_column'}
class LocationError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code):
    if not ok:raise LocationError(code)
def pointer_valid(pointer):
    try:
        need(type(pointer) is str and len(pointer.encode('utf8'))<=4096 and pointer.startswith('/program/functions/'),'CPY_LOCATION_POINTER')
        need(not any(ord(c)<32 or ord(c)==127 for c in pointer) and re.search(r'~(?![01])',pointer) is None,'CPY_LOCATION_POINTER')
    except UnicodeError:raise LocationError('CPY_LOCATION_POINTER') from None
def point(text):
    return text.count('\n')+1,len(text.rsplit('\n',1)[-1])+1
def locate(raw,program_sha256,pointer):
    pointer_valid(pointer)
    try:
        mapped=spans.source_map(raw)
        need(type(mapped) is dict and set(mapped)==HEADER,'CPY_LOCATION_MAP')
        need(all(type(mapped[key]) is str for key in ('schema','form','source_sha256','program_pin')),'CPY_LOCATION_MAP')
        need(mapped['schema']=='bagaev-record-source-map/1' and mapped['form']=='record-form/5' and mapped['source_sha256']==run.sha(raw) and mapped['program_pin']=='sha256:'+program_sha256,'CPY_LOCATION_MAP')
        need(mapped['semantic_check'] is False and mapped['execution_admission'] is False,'CPY_LOCATION_MAP')
        rows=mapped['locations'];need(type(rows) is list and len(rows)<=2048,'CPY_LOCATION_MAP')
        selected=[]
        for row in rows:
            need(type(row) is dict and type(row.get('program_pointer')) is str,'CPY_LOCATION_MAP')
            row['program_pointer'].encode('utf8')
            if row['program_pointer']==pointer:selected.append(row)
        need(len(selected)<=1,'CPY_LOCATION_MAP')
        if not selected:return None,None,False
        row=selected[0];need(set(row)==ROW,'CPY_LOCATION_MAP')
        operation=row['operation']
        need(type(operation) is str and 0<len(operation)<=64,'CPY_LOCATION_MAP');operation.encode('utf8')
        need(type(row['precision']) is str and row['precision'] in ('exact-expression','enclosing-expression'),'CPY_LOCATION_MAP')
        for key in ROW-{'program_pointer','operation','precision'}:
            need(type(row[key]) is int,'CPY_LOCATION_MAP')
        start,end=row['start_byte'],row['end_byte']
        need(0<=start<end<=len(raw),'CPY_LOCATION_MAP')
        for key in ('start_line','start_column','end_line','end_column'):need(row[key]>0,'CPY_LOCATION_MAP')
        before=raw[:start].decode('utf8');through=raw[:end].decode('utf8');excerpt=raw[start:end].decode('utf8')
        need(point(before)==(row['start_line'],row['start_column']) and point(through)==(row['end_line'],row['end_column']),'CPY_LOCATION_MAP')
        return dict(row),excerpt[:256],len(excerpt)>256
    except (spans.form.FormError,UnicodeError,ValueError,TypeError,KeyError,IndexError,RecursionError) as error:
        if isinstance(error,LocationError):raise
        raise LocationError('CPY_LOCATION_MAP') from None
def report_bytes(report):
    try:encoded=run.canonical(report)
    except (ValueError,UnicodeError,TypeError,RecursionError):raise LocationError('CPY_LOCATION_REPORT') from None
    need(len(encoded)<=REPORT_LIMIT,'CPY_LOCATION_BOUNDS');return encoded
def verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256):
    inner,root,data=run.verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256)
    try:result=run.runtime.result_value(data['result.stdout'])
    except run.runtime.RunError:raise run.VerifyError('CPY_VERIFY_RESULT') from None
    need(result['status']!='success','CPY_LOCATION_STATUS')
    location,excerpt,truncated=locate(data['compiled/source.bagaev'],program_sha256,result['location'])
    report={'schema':'bagaev-record-cpython-run-location/1','status':'mapped' if location is not None else 'unmapped',
        'form':'record-form/5','source_sha256':source_sha256,'program_sha256':program_sha256,'arguments_sha256':arguments_sha256,
        'runtime_status':result['status'],'reason':result['reason'],'work':result['work'],'runtime_pointer':result['location'],
        'location':location,'excerpt':excerpt,'excerpt_truncated':truncated,'run':inner,
        'semantic_check':False,'result_authentication':False,'execution_admission':False,'fresh_run':False,
        'checker_invoked':False,'generated_program_invocations':0}
    encoded=report_bytes(report);run.preserved(root,data)
    return report,encoded,root,data
def verify(directory,*,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256):
    return verify_data(directory,receipt_sha256,source_sha256,program_sha256,arguments_sha256,runner_sha256)[0]
HELP='''Locate a retained profile11 CPython failure in its pinned form5 source without execution.
Usage: record_cpython_run_location.py DIRECTORY --receipt-sha256 SHA256 --source-sha256 SHA256 --program-sha256 SHA256 --arguments-sha256 SHA256 --runner-sha256 SHA256 --output NEW_REPORT
Mapped source is descriptive; it does not authenticate the recorded failure or grant execution authority.
Unmapped pointers remain explicit; excerpts contain at most256 Unicode scalars.
'''
class Usage(ValueError):pass
class Parser(argparse.ArgumentParser):
    def error(self,message):raise Usage()
def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv in (['--help'],['-h']):print(HELP,end='');return 0
    try:
        parser=Parser(add_help=False,allow_abbrev=False);parser.add_argument('directory')
        for name in ('receipt-sha256','source-sha256','program-sha256','arguments-sha256','runner-sha256','output'):parser.add_argument('--'+name,required=True)
        args=parser.parse_args(argv)
    except Usage:print('CPY_USAGE',file=sys.stderr);return 2
    pins=(args.receipt_sha256,args.source_sha256,args.program_sha256,args.arguments_sha256,args.runner_sha256)
    try:
        run.pins(pins)
        try:
            target=Path(args.output).absolute()
            need(not target.resolve().is_relative_to(Path(args.directory).resolve()),'CPY_LOCATION_OUTPUT')
            try:target.lstat()
            except FileNotFoundError:pass
            else:raise LocationError('CPY_LOCATION_OUTPUT')
        except (OSError,ValueError,RuntimeError) as error:
            if isinstance(error,LocationError):raise
            raise LocationError('CPY_LOCATION_OUTPUT') from None
        report,encoded,root,data=verify_data(args.directory,*pins)
        try:
            with target.open('xb') as stream:
                need(stream.write(encoded)==len(encoded),'CPY_LOCATION_OUTPUT');stream.flush()
        except (OSError,ValueError) as error:
            if isinstance(error,LocationError):raise
            raise LocationError('CPY_LOCATION_OUTPUT') from None
        run.preserved(root,data)
        try:need(run.read(target,REPORT_LIMIT)==encoded,'CPY_LOCATION_OUTPUT')
        except run.VerifyError:raise LocationError('CPY_LOCATION_OUTPUT') from None
        return 0
    except (LocationError,run.VerifyError) as error:print(error.code,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
