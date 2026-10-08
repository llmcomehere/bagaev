#!/usr/bin/env python3
"""Data-only syntax context diagnostics; no semantic check or execution."""
import json,sys
import record_text as transport
import bagaev_record_diagnostics as diagnostics

def main(argv=None):
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False)
        p.add_argument('input');p.add_argument('--output',required=True)
        p.add_argument('--form',choices=('1','4','5'),default='1')
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        raw=transport.read_input(a.input)
        codec=diagnostics
        if a.form=='4':
            import bagaev_record_json_diagnostics
            codec=bagaev_record_json_diagnostics
        if a.form=='5':
            import bagaev_record_wide_diagnostics
            codec=bagaev_record_wide_diagnostics
        value=codec.diagnose(raw)
        data=json.dumps(value,sort_keys=True,separators=(',',':')).encode('utf8')
        transport.write_output(a.output,data)
        print(json.dumps({'schema':'bagaev-record-diagnose/1','ok':True,'diagnostic':value},sort_keys=True,separators=(',',':')))
        return 0
    except transport.Refusal as e:
        print(json.dumps({'schema':'bagaev-record-diagnose/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')))
        return 2
if __name__=='__main__':raise SystemExit(main())
