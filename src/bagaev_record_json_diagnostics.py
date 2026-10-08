"""Optional data-only record-form/4 context spans; original codec behavior is unchanged."""
import hashlib
import codecs
import re
import bagaev_record_json_form as form
HEADER=re.compile(r'\A[ \t\r\n]*bagaev[ \t\r\n]+record-form/([A-Za-z0-9_]+)[ \t\r\n]*;')
SCHEMA='record-form-diagnostic/1'
def _span(text,start,end,kind):
 def point(i):
  return text.count('\n',0,i)+1,i-(text.rfind('\n',0,i)+1)+1
 sl,sc=point(start);el,ec=point(end)
 return {'kind':kind,'start_byte':len(text[:start].encode('utf8')),'end_byte':len(text[:end].encode('utf8')),'start_line':sl,'start_column':sc,'end_line':el,'end_column':ec}
class _Reader(form.Reader):
 def __init__(self,source):
  super().__init__(source)
  self.phase='parsing'
 def lower(self,node,scope=frozenset(),depth=1):
  self.phase='lowering'
  return super().lower(node,scope,depth)
def diagnose(source):
 pin=None
 def result(code=None,phase=None,span=None):
  return {'schema':SCHEMA,'form':'record-form/4','valid_form':code is None,'source_sha256':pin,'semantic_check':False,'execution_admission':False,'error':None if code is None else {'code':code,'phase':phase,'span':span}}
 if type(source) not in (str,bytes):
  return result('FORM_SYNTAX','transport')
 if len(source)>form.old.BYTE_LIMIT:
  # Preserve the original codec's encoding-before-size refusal order without
  # allocating an unbounded encoded/decoded copy.
  if type(source)is str:
   if re.search('[\ud800-\udfff]',source):return result('FORM_SYNTAX','transport')
  else:
   decoder=codecs.getincrementaldecoder('utf8')()
   try:
    for start in range(0,len(source),65536):decoder.decode(source[start:start+65536],final=False)
    decoder.decode(b'',final=True)
   except UnicodeError:return result('FORM_SYNTAX','transport')
  return result('FORM_BOUNDS','transport')
 try:raw=source.encode('utf8') if type(source)is str else source
 except UnicodeError:return result('FORM_SYNTAX','transport')
 if len(raw)>form.old.BYTE_LIMIT:
  return result('FORM_BOUNDS','transport')
 pin=hashlib.sha256(raw).hexdigest()
 try:text=raw.decode('utf8')
 except UnicodeError:return result('FORM_SYNTAX','transport')
 h=HEADER.match(text)
 if h is None:return result('FORM_SYNTAX','header')
 if h[1]!='4':return result('FORM_VERSION','header',_span(text,h.start(1),h.end(1),'token'))
 pos=h.end();spans=[]
 while pos<len(text):
  if text[pos] in form.old.WS:pos+=1;continue
  m=form.TOKEN.match(text,pos)
  if m is None:return result('FORM_SYNTAX','lexical',_span(text,pos,pos+1,'token'))
  spans.append((m.start(),m.end()))
  if len(spans)>form.old.TOKEN_LIMIT:return result('FORM_BOUNDS','lexical',_span(text,m.start(),m.end(),'token'))
  pos=m.end()
 reader=_Reader(raw)
 try:reader.read()
 except (form.FormError,RecursionError) as error:
  code=error.code if isinstance(error,form.FormError) else 'FORM_BOUNDS'
  if reader.phase=='lowering':return result(code,'lowering')
  cursor=reader.pos
  start=spans[cursor-1][0] if cursor else (spans[0][0] if spans else len(text))
  end=spans[cursor][1] if cursor<len(spans) else len(text)
  return result(code,'parsing',_span(text,start,end,'context'))
 return result()
