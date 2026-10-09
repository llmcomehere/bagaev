#!/usr/bin/env python3
"""Bounded scalar capture data comparison. Does not execute or authenticate runs."""
import hashlib,json,sys
from record_text import Parser,Refusal,LIMIT,read_input,parse_json,write_output
from bagaev_record_draft import DraftError
from bagaev_record_capture_compare import compare_captures
SCHEMA='bagaev-record-capture-compare-tool/1'

def convert(argv):
    p=Parser(allow_abbrev=False);p.add_argument('before');p.add_argument('after')
    p.add_argument('--base',required=True);p.add_argument('--target',required=True)
    p.add_argument('--arguments-sha256',required=True);p.add_argument('--output',required=True)
    a=p.parse_args(argv);before=read_input(a.before);after=read_input(a.after)
    result=compare_captures(parse_json(before),parse_json(after),base_sha256=a.base,target_sha256=a.target,arguments_sha256=a.arguments_sha256)
    result['before_file_sha256']=hashlib.sha256(before).hexdigest();result['after_file_sha256']=hashlib.sha256(after).hexdigest()
    raw=json.dumps(result,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(raw)>LIMIT:raise Refusal('RECORD_BOUNDS')
    write_output(a.output,raw)
    return {'output_bytes':len(raw),'output_sha256':hashlib.sha256(raw).hexdigest(),'capture_authentication':False,'execution_admission':False}

def main(argv=None):
    try:
        result=convert(sys.argv[1:] if argv is None else argv);data={'schema':SCHEMA,'ok':True,'result':result};code=0
    except (Refusal,DraftError) as e:
        data={'schema':SCHEMA,'ok':False,'error':{'code':e.code}};code=2
    print(json.dumps(data,sort_keys=True,separators=(',',':')));return code

if __name__=='__main__':raise SystemExit(main())
