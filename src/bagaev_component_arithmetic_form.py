"""Explicit component-form/3 representation over unchanged component-source/2."""
import json,re
import bagaev_component_form as old
import bagaev_component_outcome_form as prior
FormError=old.FormError;need=old.need;bounded=old.bounded
RESERVED=prior.RESERVED|{'let','in'}
TOKEN=re.compile(prior.STRING+r'|(?:0|[1-9][0-9]*)|[A-Za-z][A-Za-z0-9_]*|->|[{}(),:;=.<+*\-]',re.ASCII)
class Reader(prior.Reader):
 def __init__(self,source):
  need(type(source) in (str,bytes),'FORM_SYNTAX')
  try:raw=source.encode('utf8') if type(source)is str else source;text=raw.decode('utf8')
  except UnicodeError:raise FormError('FORM_SYNTAX') from None
  need(len(raw)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(not text.startswith('\ufeff'))
  h=re.match(r'\A[ \t\r\n]*bagaev[ \t\r\n]+component-form/([A-Za-z0-9_]+)[ \t\r\n]*;',text);need(h is not None);need(h[1]=='3','FORM_VERSION');pos=h.end();self.tokens=[]
  while pos<len(text):
   if text[pos] in old.WS:pos+=1;continue
   m=TOKEN.match(text,pos);need(m is not None);self.tokens.append(m[0]);need(len(self.tokens)<=old.TOKEN_LIMIT,'FORM_BOUNDS');pos=m.end()
  self.pos=0;self.records={};self.functions={};self.variants={};self.clauses={}
 def ident(self):
  value=old.Reader.ident(self);need(value not in RESERVED);return value
 def expression(self,depth=1):
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS')
  if self.peek()=='let':
   self.take();name=self.ident();self.take('=');initial=self.expression(depth+1);self.take('in');body=self.expression(depth+1);return ('let',name,initial,body)
  if self.peek()=='if':
   self.take();condition=self.expression(depth+1);self.take('then');yes=self.expression(depth+1);self.take('else');no=self.expression(depth+1);return ('if',condition,yes,no)
  left=self.sum(depth)
  if self.peek()=='<':
   self.take();right=self.sum(depth+1);need(self.peek()!='<');return ('lt',left,right)
  return left
 def sum(self,depth):
  left=self.product(depth)
  while self.peek() in ('+','-'):
   op=self.take();left=('add' if op=='+' else 'sub',left,self.product(depth+1))
  return left
 def product(self,depth):
  left=self.atom(depth)
  while self.peek()=='*':self.take();left=('mul',left,self.atom(depth+1))
  return left
 def atom(self,depth):
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS')
  if self.peek()=='-':
   self.take();token=self.take();need(re.fullmatch(r'[0-9]+',token) is not None);need(len(token)<=19,'FORM_LITERAL');value=-int(token);need(-(1<<63)<=value<(1<<63),'FORM_LITERAL');return ('int',value)
  return super().atom(depth)
 def lower(self,node,scope=frozenset(),depth=1):
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');kind=node[0]
  child=lambda x:self.lower(x,scope,depth+1)
  if kind in ('int','text','bool'):return list(node)
  if kind=='arg':return ['use' if node[1] in scope else 'arg',node[1]]
  if kind=='let':return ['let',node[1],child(node[2]),self.lower(node[3],scope|{node[1]},depth+1)]
  if kind in ('add','sub','mul','lt'):return [kind,child(node[1]),child(node[2])]
  if kind=='if':return ['if',*[child(x) for x in node[1:]]]
  if kind=='field':return ['field',child(node[1]),node[2]]
  if kind=='unique':return ['list.unique',child(node[1])]
  if kind=='call':return ['call',node[1],*[child(x) for x in node[2]]]
  if kind=='variant':
   need(node[1] in self.variants and node[2] in self.variants[node[1]],'FORM_REFERENCE');return ['variant',node[1],node[2],child(node[3])]
  need(kind=='record');name=node[1];need(name in self.records,'FORM_REFERENCE');need(set(node[2])==set(self.records[name]),'FORM_RECORD_FIELDS');return ['record',name,*[child(node[2][k]) for k in sorted(self.records[name])]]
def decode(source):
 try:return Reader(source).read()
 except RecursionError:raise FormError('FORM_BOUNDS') from None
def encode(value):
 bounded(value)
 def shape(v,keys):need(type(v)is dict and set(v)==set(keys),'FORM_PROFILE')
 def ident(v):need(type(v)is str and old.IDENT.fullmatch(v) is not None and v not in RESERVED,'FORM_PROFILE');return v
 shape(value,['schema','program','component']);need(value['schema']=='bagaev-component-source/2','FORM_PROFILE');p=value['program'];m=value['component']
 shape(p,['schema','records','lists','variants','entry','functions']);need(p['schema']=='bagaev-typed-record/10' and p['lists']=={},'FORM_PROFILE')
 shape(m,['name','operation','state_type','request_type','revision_type','entry','identity_binding','revision_binding','replace_fields','outcome_type','error_type']);shape(m['identity_binding'],['state','request']);need(p['entry']==m['entry'],'FORM_PROFILE')
 need(type(p['records'])is dict and type(p['variants'])is dict and type(p['functions'])is dict and type(m['replace_fields'])is list and m['replace_fields'],'FORM_PROFILE');need(not(set(p['records'])&set(p['variants'])),'FORM_PROFILE')
 for defs in (p['records'],p['variants']):
  for n,fields in defs.items():
   ident(n);need(type(fields)is dict,'FORM_PROFILE')
   for k,v in fields.items():ident(k);ident(v)
 def expr(x):
  need(type(x)is list and x,'FORM_PROFILE');op=x[0]
  if op=='int' and len(x)==2:need(type(x[1])is int and -(1<<63)<=x[1]<(1<<63),'FORM_PROFILE');return str(x[1])
  if op=='bool' and len(x)==2:need(type(x[1])is bool,'FORM_PROFILE');return 'true' if x[1] else 'false'
  if op=='text' and len(x)==2:need(type(x[1])is str and not any(0xd800<=ord(c)<=0xdfff for c in x[1]),'FORM_PROFILE');return json.dumps(x[1],ensure_ascii=False)
  if op in ('arg','use') and len(x)==2:return ident(x[1])
  if op in ('add','sub','mul') and len(x)==3:return '('+expr(x[1])+' '+{'add':'+','sub':'-','mul':'*'}[op]+' '+expr(x[2])+')'
  if op=='let' and len(x)==4:return 'let '+ident(x[1])+' = ('+expr(x[2])+') in ('+expr(x[3])+')'
  if op=='field' and len(x)==3:need(type(x[1])is list and x[1] and x[1][0] in ('arg','use','field'),'FORM_PROFILE');return expr(x[1])+'.'+ident(x[2])
  if op=='list.unique' and len(x)==2:return 'list.unique('+expr(x[1])+')'
  if op=='call' and len(x)>=2:return ident(x[1])+'('+', '.join(expr(a) for a in x[2:])+')'
  if op=='lt' and len(x)==3:return '('+expr(x[1])+' < '+expr(x[2])+')'
  if op=='if' and len(x)==4:return 'if ('+expr(x[1])+') then ('+expr(x[2])+') else ('+expr(x[3])+')'
  if op=='variant' and len(x)==4:
   n=ident(x[1]);alt=ident(x[2]);need(n in p['variants'] and alt in p['variants'][n],'FORM_PROFILE');return n+'.'+alt+'('+expr(x[3])+')'
  if op=='record' and len(x)>=2:
   n=ident(x[1]);need(n in p['records'],'FORM_PROFILE');fields=sorted(p['records'][n]);need(len(x)==len(fields)+2,'FORM_PROFILE');return n+' { '+', '.join(k+': '+expr(a) for k,a in zip(fields,x[2:]))+' }'
  raise FormError('FORM_PROFILE')
 lines=['bagaev component-form/3;','component '+ident(m['name'])+' operation '+ident(m['operation'])+' {']
 for kind,defs in [('record',p['records']),('variant',p['variants'])]:
  for n in sorted(defs):lines.append('  '+kind+' '+n+' { '+', '.join(k+': '+defs[n][k] for k in sorted(defs[n]))+' };')
 lines+=['','  state '+ident(m['state_type'])+' identity '+ident(m['identity_binding']['state'])+';','  request '+ident(m['request_type'])+' identity '+ident(m['identity_binding']['request'])+' revision '+ident(m['revision_binding'])+': '+ident(m['revision_type'])+';','  replace '+', '.join(ident(x) for x in m['replace_fields'])+';','  outcome '+ident(m['outcome_type'])+' error '+ident(m['error_type'])+';','  entry '+ident(m['entry'])+';','']
 for n in sorted(p['functions']):
  f=p['functions'][n];shape(f,['params','result','body']);need(type(f['params'])is list,'FORM_PROFILE');params=[]
  for pair in f['params']:need(type(pair)is list and len(pair)==2,'FORM_PROFILE');params.append(ident(pair[0])+': '+ident(pair[1]))
  lines.append('  fn '+ident(n)+'('+', '.join(params)+') -> '+ident(f['result'])+' = '+expr(f['body'])+';')
 lines.append('}');out=('\n'.join(lines)+'\n').encode();need(len(out)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(json.dumps(decode(out),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)==json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False),'FORM_PROFILE');return out
