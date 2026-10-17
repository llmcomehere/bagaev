#!/usr/bin/env python3
"""Explicit data-only form4/form5/form6 function fragment replacement tool."""
import argparse,json,sys
import record_text as transport
import bagaev_record_function as default_edit
import bagaev_record_wide_function as wide_edit

def main(argv=None):
    edit=default_edit
    try:
        p=transport.Parser(prog='record_function.py',add_help=False,allow_abbrev=False,
                           formatter_class=lambda prog:argparse.HelpFormatter(prog,width=88))
        p.add_argument('operation',choices=('extract','context','replace'));p.add_argument('input')
        p.add_argument('--callee-context',action='store_true');p.add_argument('--source-body',action='store_true');p.add_argument('--locations',action='store_true');p.add_argument('--form',choices=('4','5','6'),default='4');p.add_argument('--name');p.add_argument('--replacement');p.add_argument('--base');p.add_argument('--function-pin');p.add_argument('--output',required=True)
        p.add_argument('--compact',action='store_true')
        arguments=list(sys.argv[1:] if argv is None else argv)
        if arguments in (['--help'],['-h']):
            print(p.format_help(),end='')
            print('\nUse --help or -h alone; no input/output is read or written for help.\n'
                  'Default form: 4. Select --form 5 or --form 6 explicitly.\n'
                  'extract/context require --name; replace requires --replacement, --base and --function-pin.\n'
                  '--source-body and --locations apply to context in form5/form6.\n'
                  '--compact requires context --form 5 --source-body and excludes --locations.\n'
                  '--callee-context applies only to replace in form5/form6.\n'
                  'All normal commands require --output pointing to a new file.\n'
                  'Extraction/context are data views; replacement creates a draft, not applied source.\n'
                  'No semantic check or execution admission is granted by these outputs.')
            return 0
        a=p.parse_args(arguments)
        if a.compact and (a.operation!='context' or a.form!='5' or not a.source_body or a.locations):raise transport.Refusal('TOOL_USAGE')
        edit=wide_edit if a.form=='5' else default_edit
        if a.form=='6':
            if a.operation=='replace':
                import bagaev_record_json_bool_change
                edit=bagaev_record_json_bool_change
            else:
                import bagaev_record_json_bool_context
                edit=bagaev_record_json_bool_context
        if a.callee_context and (a.operation!='replace' or a.form not in ('5','6')):raise transport.Refusal('TOOL_USAGE')
        if (a.locations or a.source_body) and (a.operation!='context' or a.form not in ('5','6')):raise transport.Refusal('TOOL_USAGE')
        if a.operation in ('extract','context'):
            if a.name is None or any(x is not None for x in (a.replacement,a.base,a.function_pin)):raise transport.Refusal('TOOL_USAGE')
            source=transport.read_input(a.input)
            value=edit.fragment(source,a.name) if a.operation=='extract' else (edit.compact_source_context(source,a.name) if a.compact else edit.source_context(source,a.name) if a.source_body else edit.located_context(source,a.name) if a.locations else edit.context(source,a.name))
        else:
            if a.name is not None or any(x is None for x in (a.replacement,a.base,a.function_pin)):raise transport.Refusal('TOOL_USAGE')
            if a.callee_context and a.form=='6':
                import bagaev_record_json_bool_callee
                replace=bagaev_record_json_bool_callee.replace_in_context
            else:
                replace=edit.replace_in_context if a.callee_context else edit.replace
            value=replace(transport.read_input(a.input),transport.read_input(a.replacement),base_sha256=a.base,function_sha256=a.function_pin)
        raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf8')
        if len(raw)>transport.LIMIT:raise transport.Refusal('RECORD_BOUNDS')
        transport.write_output(a.output,raw)
        print(json.dumps({'schema':'bagaev-record-function-tool/1','ok':True,**({'callee_context_base':a.base} if a.callee_context else {}),'semantic_check':False,'execution_admission':False},sort_keys=True,separators=(',',':')))
        return 0
    except (transport.Refusal,edit.DraftError,edit.form.FormError) as e:
        print(json.dumps({'schema':'bagaev-record-function-tool/1','ok':False,'error':{'code':e.code}},sort_keys=True,separators=(',',':')))
        return 2
if __name__=='__main__':raise SystemExit(main())
