#!/usr/bin/env python3
"""Format explicit form4 source as data; preserve its exact graph."""
import json,sys,hashlib
import record_text as transport
import bagaev_record_format as formatter

def main(argv=None):
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False);p.add_argument('input');p.add_argument('--output',required=True)
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        source=transport.read_input(a.input);out=formatter.format_source(source);transport.write_output(a.output,out)
        print(json.dumps({'schema':'bagaev-record-format/1','ok':True,'form':'record-form/4','output_sha256':hashlib.sha256(out).hexdigest(),'graph_preserved':True,'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')));return 0
    except (transport.Refusal,formatter.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-format/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')));return 2
if __name__=='__main__':raise SystemExit(main())
