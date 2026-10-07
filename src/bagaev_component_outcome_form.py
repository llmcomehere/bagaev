"""Explicit bounded component-form/2 data codec. Never evaluates source text."""
import json,re
import bagaev_component_form as old
FormError=old.FormError;need=old.need;bounded=old.bounded
RESERVED={'if','then','else','true','false'}
STRING=r'"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9A-Fa-f]{4}))*"'
TOKEN=re.compile(STRING+r'|-?(?:0|[1-9][0-9]*)|[A-Za-z][A-Za-z0-9_]*|->|[{}(),:;=.<]',re.ASCII)
class Reader(old.Reader):
 def __init__(self,source):
  need(type(source) in (str,bytes),'FORM_SYNTAX')
  try:raw=source.encode('utf8') if type(source)is str else source;text=raw.decode('utf8')
  except UnicodeError:raise FormError('FORM_SYNTAX') from None
  need(len(raw)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(not text.startswith('\ufeff'))
  h=re.match(r'\A[ \t\r\n]*bagaev[ \t\r\n]+component-form/([A-Za-z0-9_]+)[ \t\r\n]*;',text);need(h is not None);need(h[1]=='2','FORM_VERSION');pos=h.end();self.tokens=[]
  while pos<len(text):
   if text[pos] in old.WS:pos+=1;continue
   m=TOKEN.match(text,pos);need(m is not None);self.tokens.append(m[0]);need(len(self.tokens)<=old.TOKEN_LIMIT,'FORM_BOUNDS');pos=m.end()
  self.pos=0;self.records={};self.functions={};self.variants={};self.clauses={}
 def ident(self):
  value=super().ident();need(value not in RESERVED);return value
 def expression(self,depth=1):
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS')
  if self.peek()=='if':
   self.take();condition=self.expression(depth+1);self.take('then');yes=self.expression(depth+1);self.take('else');no=self.expression(depth+1);return ('if',condition,yes,no)
  left=self.atom(depth)
  if self.peek()=='<':
   self.take();right=self.atom(depth+1);need(self.peek()!='<');return ('lt',left,right)
  return left
 def atom(self,depth):
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');token=self.peek();need(token is not None)
  if token=='(':
   self.take();v=self.expression(depth+1);self.take(')');return v
  if token in ('true','false'):self.take();return ('bool',token=='true')
  if token.startswith('"'):
   self.take()
   try:v=json.loads(token)
   except ValueError:raise FormError('FORM_SYNTAX') from None
   need(not any(0xd800<=ord(c)<=0xdfff for c in v));return ('text',v)
  if re.fullmatch(r'-?[0-9]+',token):
   self.take();need(len(token)<=20,'FORM_LITERAL');v=int(token);need(-(1<<63)<=v<(1<<63),'FORM_LITERAL');return ('int',v)
  name=self.ident()
  if self.peek()=='{':return ('record',name,self.fields(lambda:self.expression(depth+1)))
  parts=[name]
  while self.peek()=='.':self.take();parts.append(self.ident())
  if self.peek()=='(':
   self.take();args=[]
   if self.peek()!=')':
    while True:
     args.append(self.expression(depth+1))
     if self.peek()!=',':break
     self.take(',')
   self.take(')')
   if parts==['list','unique']:need(len(args)==1);return ('unique',args[0])
   if len(parts)==2:need(len(args)==1);return ('variant',parts[0],parts[1],args[0])
   need(len(parts)==1);return ('call',name,args)
  node=('arg',name)
  for field in parts[1:]:node=('field',node,field)
  return node
 def lower(self,node):
  if node[0] in ('int','text','bool'):return list(node)
  if node[0]=='if':return ['if',*[self.lower(n) for n in node[1:]]]
  if node[0]=='lt':return ['lt',self.lower(node[1]),self.lower(node[2])]
  if node[0]=='variant':
   need(node[1] in self.variants and node[2] in self.variants[node[1]],'FORM_REFERENCE');return ['variant',node[1],node[2],self.lower(node[3])]
  return super().lower(node)
 def read(self):
  self.take('component');name=self.ident();self.take('operation');operation=self.ident();self.take('{')
  while self.peek()!='}':
   kind=self.take()
   if kind in ('record','variant'):
    n=self.ident();need(n not in self.records and n not in self.variants,'FORM_DUPLICATE');fields=self.fields(self.ident);(self.records if kind=='record' else self.variants)[n]=fields
   elif kind=='fn':
    n=self.ident();need(n not in self.functions,'FORM_DUPLICATE');self.take('(');params=[]
    if self.peek()!=')':
     while True:
      p=self.ident();self.take(':');params.append([p,self.ident()])
      if self.peek()!=',':break
      self.take(',')
    self.take(')');self.take('->');result=self.ident();self.take('=');self.functions[n]={'params':params,'result':result,'body':self.expression()}
   else:
    need(kind in ('state','request','replace','entry','outcome'));need(kind not in self.clauses,'FORM_DUPLICATE')
    if kind=='state':
     ty=self.ident();self.take('identity');self.clauses[kind]=(ty,self.ident())
    elif kind=='request':
     ty=self.ident();self.take('identity');identity=self.ident();self.take('revision');field=self.ident();self.take(':');self.clauses[kind]=(ty,identity,field,self.ident())
    elif kind=='outcome':
     ty=self.ident();self.take('error');self.clauses[kind]=(ty,self.ident())
    elif kind=='entry':self.clauses[kind]=self.ident()
    else:
     fields=[self.ident()]
     while self.peek()==',':self.take();fields.append(self.ident())
     self.clauses[kind]=fields
   self.take(';')
  self.take('}');need(self.peek() is None);need(set(self.clauses)=={'state','request','replace','entry','outcome'},'FORM_SHAPE')
  for f in self.functions.values():f['body']=self.lower(f['body'])
  state,identity=self.clauses['state'];request,req_id,rev_field,revision=self.clauses['request'];entry=self.clauses['entry'];outcome,error=self.clauses['outcome']
  result={'schema':'bagaev-component-source/2','program':{'schema':'bagaev-typed-record/10','records':self.records,'lists':{},'variants':self.variants,'entry':entry,'functions':self.functions},'component':{'name':name,'operation':operation,'state_type':state,'request_type':request,'revision_type':revision,'entry':entry,'identity_binding':{'state':identity,'request':req_id},'revision_binding':rev_field,'replace_fields':self.clauses['replace'],'outcome_type':outcome,'error_type':error}}
  bounded(result);return result
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
  if op=='arg' and len(x)==2:return ident(x[1])
  if op=='field' and len(x)==3:need(type(x[1])is list and x[1] and x[1][0] in ('arg','field'),'FORM_PROFILE');return expr(x[1])+'.'+ident(x[2])
  if op=='list.unique' and len(x)==2:return 'list.unique('+expr(x[1])+')'
  if op=='call' and len(x)>=2:return ident(x[1])+'('+', '.join(expr(a) for a in x[2:])+')'
  if op=='lt' and len(x)==3:return '('+expr(x[1])+' < '+expr(x[2])+')'
  if op=='if' and len(x)==4:return 'if ('+expr(x[1])+') then ('+expr(x[2])+') else ('+expr(x[3])+')'
  if op=='variant' and len(x)==4:
   n=ident(x[1]);alt=ident(x[2]);need(n in p['variants'] and alt in p['variants'][n],'FORM_PROFILE');return n+'.'+alt+'('+expr(x[3])+')'
  if op=='record' and len(x)>=2:
   n=ident(x[1]);need(n in p['records'],'FORM_PROFILE');fields=sorted(p['records'][n]);need(len(x)==len(fields)+2,'FORM_PROFILE');return n+' { '+', '.join(k+': '+expr(a) for k,a in zip(fields,x[2:]))+' }'
  raise FormError('FORM_PROFILE')
 lines=['bagaev component-form/2;','component '+ident(m['name'])+' operation '+ident(m['operation'])+' {']
 for kind,defs in [('record',p['records']),('variant',p['variants'])]:
  for n in sorted(defs):lines.append('  '+kind+' '+n+' { '+', '.join(k+': '+defs[n][k] for k in sorted(defs[n]))+' };')
 lines+=['','  state '+ident(m['state_type'])+' identity '+ident(m['identity_binding']['state'])+';','  request '+ident(m['request_type'])+' identity '+ident(m['identity_binding']['request'])+' revision '+ident(m['revision_binding'])+': '+ident(m['revision_type'])+';','  replace '+', '.join(ident(x) for x in m['replace_fields'])+';','  outcome '+ident(m['outcome_type'])+' error '+ident(m['error_type'])+';','  entry '+ident(m['entry'])+';','']
 for n in sorted(p['functions']):
  f=p['functions'][n];shape(f,['params','result','body']);need(type(f['params'])is list,'FORM_PROFILE');params=[]
  for pair in f['params']:need(type(pair)is list and len(pair)==2,'FORM_PROFILE');params.append(ident(pair[0])+': '+ident(pair[1]))
  lines.append('  fn '+ident(n)+'('+', '.join(params)+') -> '+ident(f['result'])+' = '+expr(f['body'])+';')
 lines.append('}');out=('\n'.join(lines)+'\n').encode();need(len(out)<=old.BYTE_LIMIT,'FORM_BOUNDS');return out
