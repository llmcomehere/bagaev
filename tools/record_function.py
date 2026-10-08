#!/usr/bin/env python3
"""Fixed data-only form4 function fragment/export replacement tool."""
import json,sys
import record_text as transport
import bagaev_record_function as edit

def main(argv=None):
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False)
        p.add_argument('operation',choices=('extract','replace'));p.add_argument('input')
        p.add_argument('--name');p.add_argument('--replacement');p.add_argument('--base');p.add_argument('--function-pin');p.add_argument('--output',required=True)
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        if a.operation=='extract':
            if a.name is None or any(x is not None for x in (a.replacement,a.base,a.function_pin)):raise transport.Refusal('TOOL_USAGE')
            value=edit.fragment(transport.read_input(a.input),a.name)
        else:
            if a.name is not None or any(x is None for x in (a.replacement,a.base,a.function_pin)):raise transport.Refusal('TOOL_USAGE')
            value=edit.replace(transport.read_input(a.input),transport.read_input(a.replacement),base_sha256=a.base,function_sha256=a.function_pin)
        raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
        if len(raw)>transport.LIMIT:raise transport.Refusal('RECORD_BOUNDS')
        transport.write_output(a.output,raw)
        print(json.dumps({'schema':'bagaev-record-function-tool/1','ok':True,'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')))
        return 0
    except (transport.Refusal,edit.DraftError,edit.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-function-tool/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')))
        return 2
if __name__=='__main__':raise SystemExit(main())
