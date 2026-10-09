"""Compare supplied, pinned scalar capture data. No authentication or execution."""
import re
from bagaev_record_draft import need,digest
RESULT_KEYS={'schema','status','value_type','value','work','reason','location'}
FAILURES={'integer-overflow':'RR_OVERFLOW','list-index':'RR_INDEX',
          'work-limit':'RR_WORK','record-list-bound':'RR_RECORD_LIST_ITEMS'}

def _result(value):
    need(type(value) is dict and set(value)==RESULT_KEYS,'CAPTURE_RESULT')
    need(value['schema']=='bagaev-typed-record-result/11' and
         type(value['status']) is str and type(value['work']) is int and
         0<=value['work']<=65536,'CAPTURE_RESULT')
    if value['status']=='success':
        good=(value['value_type']=='Int64' and type(value['value']) is int and -(2**63)<=value['value']<2**63 or
              value['value_type']=='Bool' and type(value['value']) is bool)
        need(good and value['reason'] is None and value['location'] is None,'CAPTURE_RESULT')
    else:
        need(value['status'] in FAILURES and value['reason']==FAILURES[value['status']] and
             value['value_type'] is None and value['value'] is None and
             type(value['location']) is str and value['location'].startswith('/program/') and
             len(value['location'])<=4096,'CAPTURE_RESULT')
    try:return digest(value)
    except (TypeError,ValueError,UnicodeError,RecursionError):need(False,'CAPTURE_RESULT')

def compare_captures(before,after,*,base_sha256,target_sha256,arguments_sha256):
    """Equality of supplied envelopes is not proof of a run or all-input equivalence."""
    for pin in (base_sha256,target_sha256,arguments_sha256):
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}',pin) is not None,'CAPTURE_PIN')
    hashes=[]
    for capture,program in ((before,base_sha256),(after,target_sha256)):
        need(type(capture) is dict and set(capture)=={'program_sha256','arguments_sha256','result'},'CAPTURE_SHAPE')
        need(capture['program_sha256']==program,'CAPTURE_PROGRAM')
        need(capture['arguments_sha256']==arguments_sha256,'CAPTURE_ARGUMENTS')
        hashes.append(_result(capture['result']))
    a,b=before['result'],after['result'];both_success=a['status']==b['status']=='success'
    both_failure=a['status']!='success' and b['status']!='success'
    return {'schema':'bagaev-record-capture-comparison/1','status':'comparison',
            'base':base_sha256,'target':target_sha256,'arguments_sha256':arguments_sha256,
            'before_result_sha256':hashes[0],'after_result_sha256':hashes[1],
            'same_result':hashes[0]==hashes[1],
            'same_success_value':(a['value_type']==b['value_type'] and a['value']==b['value']) if both_success else None,
            'same_failure':all(a[k]==b[k] for k in ('status','reason','location')) if both_failure else None,
            'work_delta':b['work']-a['work'],'source_check':False,
            'capture_authentication':False,'equivalence_check':False,'execution_admission':False}
