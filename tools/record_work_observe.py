#!/usr/bin/env python3
"""Bounded data-only source/work/argument observation. Does not execute a program."""
import hashlib
import json
import sys
from record_text import Parser,Refusal,LIMIT,read_input,parse_json,write_output,form
from bagaev_record_draft import DraftError
from bagaev_record_work_observation import observe_source
SCHEMA='bagaev-record-work-observe-tool/1'


def convert(argv):
    parser=Parser(allow_abbrev=False)
    parser.add_argument('source')
    parser.add_argument('--form',choices=('5',),required=True)
    parser.add_argument('--program',required=True)
    parser.add_argument('--bounds',required=True)
    parser.add_argument('--arguments',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    source=read_input(args.source);bounds=read_input(args.bounds);values=read_input(args.arguments)
    observation=observe_source(source,parse_json(bounds),parse_json(values),program_sha256=args.program)
    observation['argument_bounds_file_sha256']=hashlib.sha256(bounds).hexdigest()
    observation['arguments_file_sha256']=hashlib.sha256(values).hexdigest()
    raw=json.dumps(observation,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(raw)>LIMIT:raise Refusal('RECORD_BOUNDS')
    write_output(args.output,raw)
    return {'output_bytes':len(raw),'output_sha256':hashlib.sha256(raw).hexdigest(),
            'semantic_check':False,'execution_admission':False}


def main(argv=None):
    try:
        result=convert(sys.argv[1:] if argv is None else argv)
        data={'schema':SCHEMA,'ok':True,'result':result};code=0
    except (Refusal,DraftError,form.FormError) as error:
        data={'schema':SCHEMA,'ok':False,'error':{'code':error.code}};code=2
    print(json.dumps(data,sort_keys=True,separators=(',',':')))
    return code

if __name__=='__main__':raise SystemExit(main())
