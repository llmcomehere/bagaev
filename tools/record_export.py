#!/usr/bin/env python3
"""Export a validated focused draft as inert source; no execution."""
import json,sys,hashlib
import record_text as transport
import bagaev_record_export as export

def main(argv=None):
    try:
        p=transport.Parser(add_help=False,allow_abbrev=False)
        p.add_argument('original');p.add_argument('--draft',required=True)
        p.add_argument('--base',required=True);p.add_argument('--target',required=True)
        p.add_argument('--form',choices=('4','5'),default='4');p.add_argument('--output',required=True)
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        raw=export.export_source(transport.read_input(a.original),transport.parse_json(transport.read_input(a.draft)),base_sha256=a.base,target_sha256=a.target,form_version=a.form)
        transport.write_output(a.output,raw)
        print(json.dumps({'schema':'bagaev-record-export/1','ok':True,'form':'record-form/'+a.form,'source_sha256':hashlib.sha256(raw).hexdigest(),'target':a.target,'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')));return 0
    except (transport.Refusal,export.DraftError,export.narrow.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-export/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')));return 2
if __name__=='__main__':raise SystemExit(main())
