"""Data-only token formatting for explicit record-form/5."""
import json
import bagaev_record_wide_form as form

def format_source(source):
    before=form.decode(source)
    tokens=[token for token,_,_,_ in form.Reader(source).token_items]
    lines=['bagaev record-form/5;'];line='';stack=[];size=len(lines[0])+1
    def flush():
        nonlocal line,size
        if line:
            text='  '*min(stack.count('{'),32)+line.rstrip()
            size+=len(text.encode('utf8'))+1
            form.need(size<=form.old.BYTE_LIMIT,'FORM_BOUNDS')
            lines.append(text);line=''
    for token in tokens:
        if token.startswith('//'):
            flush();line=token;flush();continue
        if token=='}':
            flush()
            if stack and stack[-1]=='{':stack.pop()
            line='}'
        elif token=='{':
            line+=(' ' if line else '')+'{'
            flush();stack.append('{')
        elif token==';':
            line+=';';flush()
        elif token==',':
            line+=','
            if stack and stack[-1]=='{':flush()
            else:line+=' '
        elif token=='(':
            line+='(';stack.append('(')
        elif token==')':
            line+=')'
            if stack and stack[-1]=='(':stack.pop()
        elif token=='.':line+='.'
        elif token==':':line+=': '
        else:
            if token in ('then','else','in') and line:flush()
            if line and not line.endswith((' ','.','(',':')):line+=' '
            line+=token
    flush()
    out=('\n'.join(lines)+'\n').encode('utf8')
    form.need(len(out)<=form.old.BYTE_LIMIT,'FORM_BOUNDS')
    after=form.decode(out)
    canonical=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    form.need(canonical(before)==canonical(after),'FORM_PROFILE')
    return out
