#!/usr/bin/env python3
"""Format explicit form4/form5 source as data; preserve its exact graph."""
import json,sys,hashlib
import record_text as transport
import bagaev_record_format as default_formatter
import bagaev_record_wide_format as wide_formatter

def main(argv=None):
    formatter=default_formatter
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False);p.add_argument('--form',choices=('4','5'),default='4');p.add_argument('--width');p.add_argument('input');p.add_argument('--output',required=True)
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        if a.width is not None and (a.form!='5' or not a.width.isascii() or not a.width.isdigit() or len(a.width)>3 or not 40<=int(a.width)<=120):raise transport.Refusal('TOOL_USAGE')
        formatter=wide_formatter if a.form=='5' else default_formatter
        source=transport.read_input(a.input);out=formatter.format_source(source) if a.width is None else formatter.format_source_wrapped(source,width=int(a.width));transport.write_output(a.output,out)
        print(json.dumps({'schema':'bagaev-record-format/1','ok':True,'form':'record-form/'+a.form,'output_sha256':hashlib.sha256(out).hexdigest(),'graph_preserved':True,**({'soft_width':int(a.width)} if a.width is not None else {}),'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')));return 0
    except (transport.Refusal,formatter.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-format/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')));return 2
if __name__=='__main__':raise SystemExit(main())
