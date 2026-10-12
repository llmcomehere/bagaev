"""Pure form6 authored-body splice; no command-line or execution route."""
from bagaev_record_json_bool_change import form,digest,need,DraftError,export_source_preserving_layout
from bagaev_record_json_bool_callee import replace_in_context
from bagaev_record_wide_function import _context_reader
import bagaev_record_json_bool_spans as spans

def export_authored(original,packet,replacement,*,base_sha256,target_sha256,source_sha256):
    validated=export_source_preserving_layout(original,packet,base_sha256=base_sha256,target_sha256=target_sha256,source_sha256=source_sha256)
    raw=original.encode('utf8') if type(original) is str else original
    need(type(replacement) in (str,bytes),'EXPORT_LAYOUT')
    try:fragment=replacement.encode('utf8') if type(replacement) is str else replacement
    except UnicodeError:raise DraftError('EXPORT_LAYOUT') from None
    before,after=form.decode(raw),form.decode(validated)
    changed=[n for n in before['functions'] if before['functions'][n]!=after['functions'][n]]
    need(len(changed)==1,'EXPORT_SCOPE');name=changed[0]
    rebuilt=replace_in_context(raw,fragment,base_sha256=base_sha256,function_sha256=digest(before['functions'][name]))
    need(digest(rebuilt)==digest(packet),'EXPORT_FRAGMENT')
    try:part=_context_reader(form.Reader,before)(fragment).read()
    except RecursionError:raise form.FormError('FORM_BOUNDS') from None
    mapped=spans.prior._source_map(fragment,part,_context_reader(spans._Reader,before))
    pointer='/program/functions/'+name+'/body'
    def bounds(mapping,source):
        rows=[r for r in mapping['locations'] if r['program_pointer']==pointer]
        need(len(rows)==1 and rows[0]['precision']=='exact-expression','EXPORT_LAYOUT')
        a,b=rows[0]['start_byte'],rows[0]['end_byte']
        need(0<=a<b<=len(source),'EXPORT_LAYOUT');return a,b
    a,b=bounds(spans.source_map(raw),raw);x,y=bounds(mapped,fragment)
    result=raw[:a]+fragment[x:y]+raw[b:]
    need(len(result)<=form.prior.old.BYTE_LIMIT,'EXPORT_BOUNDS')
    decoded=form.decode(result)
    need(decoded==after and digest(decoded)==target_sha256,'EXPORT_LAYOUT')
    return result
