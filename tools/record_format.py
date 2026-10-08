#!/usr/bin/env python3
"""Format explicit form4/form5 source as data; preserve its exact graph."""
import json,sys,hashlib
import record_text as transport
import bagaev_record_format as default_formatter
import bagaev_record_wide_format as wide_formatter

def main(argv=None):
    formatter=default_formatter
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False);p.add_argument('--form',choices=('4','5'),default='4');p.add_argument('input');p.add_argument('--output',required=True)
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        formatter=wide_formatter if a.form=='5' else default_formatter
        source=transport.read_input(a.input);out=formatter.format_source(source);transport.write_output(a.output,out)
        print(json.dumps({'schema':'bagaev-record-format/1','ok':True,'form':'record-form/'+a.form,'output_sha256':hashlib.sha256(out).hexdigest(),'graph_preserved':True,'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')));return 0
    except (transport.Refusal,formatter.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-format/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')));return 2
if __name__=='__main__':raise SystemExit(main())
