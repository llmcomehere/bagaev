#!/usr/bin/env python3
"""Prepare a detached function draft from two pure sources; no execution."""
import json,sys
import record_text as transport
import bagaev_record_draft as edit

def main(argv=None):
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False)
        p.add_argument('original');p.add_argument('candidate')
        p.add_argument('--base',required=True);p.add_argument('--target',required=True)
        p.add_argument('--output',required=True)
        p.add_argument('--form',choices=('1','4'),default='1')
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        codec=edit
        if a.form=='4':
            import bagaev_record_json_draft
            codec=bagaev_record_json_draft
        v=codec.draft(transport.read_input(a.original),transport.read_input(a.candidate),base_sha256=a.base,target_sha256=a.target)
        raw=json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
        if len(raw)>transport.LIMIT:raise transport.Refusal('RECORD_BOUNDS')
        transport.write_output(a.output,raw)
        print(json.dumps({'schema':'bagaev-record-draft-tool/1','ok':True,'base':v['base'],'target':v['target'],'delta':v['delta'],'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')))
        return 0
    except (transport.Refusal,edit.DraftError,edit.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-draft-tool/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')))
        return 2
if __name__=='__main__':raise SystemExit(main())
