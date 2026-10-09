#!/usr/bin/env python3
"""Explicit form5 data-only work comparison, with bounded file transport."""
import hashlib
import json
import sys
from record_text import Parser,Refusal,LIMIT,read_input,parse_json,write_output,form
from bagaev_record_draft import DraftError
from bagaev_record_work_compare import compare

SCHEMA='bagaev-record-work-compare-tool/1'


def convert(argv):
    parser=Parser(allow_abbrev=False)
    parser.add_argument('original')
    parser.add_argument('candidate')
    parser.add_argument('--form',choices=('5',),required=True)
    parser.add_argument('--bounds',required=True)
    parser.add_argument('--base',required=True)
    parser.add_argument('--target',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    old=read_input(args.original)
    new=read_input(args.candidate)
    raw_bounds=read_input(args.bounds)
    value=compare(old,new,parse_json(raw_bounds),base_sha256=args.base,target_sha256=args.target)
    value['argument_bounds_file_sha256']=hashlib.sha256(raw_bounds).hexdigest()
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(raw)>LIMIT:
        raise Refusal('RECORD_BOUNDS')
    write_output(args.output,raw)
    return {'output_bytes':len(raw),'output_sha256':hashlib.sha256(raw).hexdigest(),
            'semantic_check':False,'execution_admission':False,'equivalence_check':False}


def main(argv=None):
    try:
        result=convert(sys.argv[1:] if argv is None else argv)
        observation={'schema':SCHEMA,'ok':True,'result':result};code=0
    except (Refusal,DraftError,form.FormError) as error:
        observation={'schema':SCHEMA,'ok':False,'error':{'code':error.code}};code=2
    print(json.dumps(observation,sort_keys=True,separators=(',',':')))
    return code

if __name__=='__main__':raise SystemExit(main())
