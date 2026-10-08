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
        p.add_argument('--preserve-layout',action='store_true');p.add_argument('--source-sha256');p.add_argument('--replacement-source');p.add_argument('--callee-context',action='store_true')
        a=p.parse_args(sys.argv[1:] if argv is None else argv)
        if (a.preserve_layout != (a.source_sha256 is not None)) or (a.preserve_layout and a.form != '5'):
            raise transport.Refusal('TOOL_USAGE')
        if a.replacement_source is not None and not a.preserve_layout:raise transport.Refusal('TOOL_USAGE')
        if a.callee_context and a.replacement_source is None:raise transport.Refusal('TOOL_USAGE')
        original=transport.read_input(a.original);packet=transport.parse_json(transport.read_input(a.draft))
        replacement=None
        if a.replacement_source is not None:
            replacement=transport.read_input(a.replacement_source)
            emit=export.export_source_with_contextual_fragment_layout if a.callee_context else export.export_source_with_fragment_layout
            raw=emit(original,packet,replacement,base_sha256=a.base,target_sha256=a.target,source_sha256=a.source_sha256)
        elif a.preserve_layout:
            raw=export.export_source_preserving_layout(original,packet,base_sha256=a.base,target_sha256=a.target,source_sha256=a.source_sha256)
        else:
            raw=export.export_source(original,packet,base_sha256=a.base,target_sha256=a.target,form_version=a.form)
        transport.write_output(a.output,raw)
        print(json.dumps({'schema':'bagaev-record-export/1','ok':True,'form':'record-form/'+a.form,'source_sha256':hashlib.sha256(raw).hexdigest(),'target':a.target,**({'callee_context_base':a.base} if a.callee_context else {}),**({'input_source_sha256':a.source_sha256,'preservation_scope':'outside-changed-function-body'} if a.preserve_layout else {}),**({'replacement_source_sha256':hashlib.sha256(replacement).hexdigest(),'replacement_scope':'body-expression'} if replacement is not None else {}),'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')));return 0
    except (transport.Refusal,export.DraftError,export.narrow.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-export/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')));return 2
if __name__=='__main__':raise SystemExit(main())
