"""Pure bounded readable component data codec. Never evaluates source text."""
import re
BYTE_LIMIT=1048576;TOKEN_LIMIT=32768;VALUE_LIMIT=10000;DEPTH_LIMIT=128
IDENT=re.compile(r'[A-Za-z][A-Za-z0-9_]*\Z',re.ASCII)
TOKEN=re.compile(r'[A-Za-z][A-Za-z0-9_]*|->|[{}(),:;=.]',re.ASCII)
WS=' \t\r\n'
class FormError(ValueError):
 def __init__(self,code):self.code=code;super().__init__(code)
def need(ok,code='FORM_SYNTAX'):
 if not ok:raise FormError(code)
def bounded(value):
 stack=[(value,1,frozenset())];count=0
 while stack:
  v,depth,parents=stack.pop();count+=1;need(count<=VALUE_LIMIT and depth<=DEPTH_LIMIT,'FORM_BOUNDS')
  need(type(v) in (dict,list,str,int,bool,type(None)),'FORM_PROFILE')
  if type(v) in (dict,list):
   need(id(v) not in parents,'FORM_PROFILE');ps=parents|{id(v)}
   if type(v)is dict:need(all(type(k)is str for k in v),'FORM_PROFILE')
   stack.extend((x,depth+1,ps) for x in (v.values() if type(v)is dict else v))
class Reader:
 def __init__(self,source):
  need(type(source) in (str,bytes),'FORM_SYNTAX')
  try:raw=source.encode('utf8') if type(source)is str else source;text=raw.decode('utf8')
  except UnicodeError:raise FormError('FORM_SYNTAX') from None
  need(len(raw)<=BYTE_LIMIT,'FORM_BOUNDS');need(not text.startswith('\ufeff'))
  h=re.match(r'\A[ \t\r\n]*bagaev[ \t\r\n]+component-form/([A-Za-z0-9_]+)[ \t\r\n]*;',text)
  need(h is not None);need(h[1]=='1','FORM_VERSION');pos=h.end();self.tokens=[]
  while pos<len(text):
   if text[pos] in WS:pos+=1;continue
   m=TOKEN.match(text,pos);need(m is not None);self.tokens.append(m[0]);need(len(self.tokens)<=TOKEN_LIMIT,'FORM_BOUNDS');pos=m.end()
  self.pos=0;self.records={};self.functions={};self.clauses={}
 def peek(self):return self.tokens[self.pos] if self.pos<len(self.tokens) else None
 def take(self,token=None):
  v=self.peek();need(v is not None and (token is None or v==token));self.pos+=1;return v
 def ident(self):v=self.take();need(IDENT.fullmatch(v) is not None);return v
 def fields(self,values):
  self.take('{');out={}
  if self.peek()!='}':
   while True:
    k=self.ident();need(k not in out,'FORM_DUPLICATE');self.take(':');out[k]=values()
    if self.peek()!=',':break
    self.take(',')
  self.take('}');return out
 def expression(self,depth=1):
  need(depth<=DEPTH_LIMIT,'FORM_BOUNDS');name=self.ident()
  if self.peek()=='{':node=('record',name,self.fields(lambda:self.expression(depth+1)))
  else:
   parts=[name]
   while self.peek()=='.':self.take('.');parts.append(self.ident())
   if self.peek()=='(':
    self.take('(');args=[]
    if self.peek()!=')':
     while True:
      args.append(self.expression(depth+1))
      if self.peek()!=',':break
      self.take(',')
    self.take(')')
    if parts==['list','unique']:need(len(args)==1);node=('unique',args[0])
    else:need(len(parts)==1);node=('call',name,args)
   else:
    node=('arg',name)
    for field in parts[1:]:node=('field',node,field)
  return node
 def lower(self,node):
  kind=node[0]
  if kind=='arg':return ['arg',node[1]]
  if kind=='field':return ['field',self.lower(node[1]),node[2]]
  if kind=='unique':return ['list.unique',self.lower(node[1])]
  if kind=='call':return ['call',node[1],*[self.lower(x) for x in node[2]]]
  need(kind=='record');name=node[1];need(name in self.records,'FORM_REFERENCE');need(set(node[2])==set(self.records[name]),'FORM_RECORD_FIELDS')
  return ['record',name,*[self.lower(node[2][k]) for k in sorted(self.records[name])]]
 def read(self):
  self.take('component');name=self.ident();self.take('operation');operation=self.ident();self.take('{')
  while self.peek()!='}':
   kind=self.take()
   if kind=='record':
    n=self.ident();need(n not in self.records,'FORM_DUPLICATE');self.records[n]=self.fields(self.ident)
   elif kind=='fn':
    n=self.ident();need(n not in self.functions,'FORM_DUPLICATE');self.take('(');params=[]
    if self.peek()!=')':
     while True:
      p=self.ident();self.take(':');params.append([p,self.ident()])
      if self.peek()!=',':break
      self.take(',')
    self.take(')');self.take('->');result=self.ident();self.take('=');self.functions[n]={'params':params,'result':result,'body':self.expression()}
   else:
    need(kind in ('state','request','replace','entry'));need(kind not in self.clauses,'FORM_DUPLICATE')
    if kind=='state':
     ty=self.ident();self.take('identity');self.clauses[kind]=(ty,self.ident())
    elif kind=='request':
     ty=self.ident();self.take('identity');identity=self.ident();self.take('revision');field=self.ident();self.take(':');self.clauses[kind]=(ty,identity,field,self.ident())
    elif kind=='entry':self.clauses[kind]=self.ident()
    else:
     fields=[self.ident()]
     while self.peek()==',':self.take(',');fields.append(self.ident())
     self.clauses[kind]=fields
   self.take(';')
  self.take('}');need(self.peek() is None);need(set(self.clauses)=={'state','request','replace','entry'},'FORM_SHAPE')
  for f in self.functions.values():f['body']=self.lower(f['body'])
  state,identity=self.clauses['state'];request,req_id,rev_field,revision=self.clauses['request'];entry=self.clauses['entry']
  result={'schema':'bagaev-component-source/1','program':{'schema':'bagaev-typed-record/10','records':self.records,'lists':{},'variants':{},'entry':entry,'functions':self.functions},'component':{'name':name,'operation':operation,'state_type':state,'request_type':request,'revision_type':revision,'entry':entry,'identity_binding':{'state':identity,'request':req_id},'revision_binding':rev_field,'replace_fields':self.clauses['replace']}}
  bounded(result);return result
def decode(source):
 try:return Reader(source).read()
 except RecursionError:raise FormError('FORM_BOUNDS') from None
def encode(value):
 bounded(value)
 def shape(v,keys):need(type(v)is dict and set(v)==set(keys),'FORM_PROFILE')
 def ident(v):need(type(v)is str and IDENT.fullmatch(v) is not None,'FORM_PROFILE');return v
 shape(value,['schema','program','component']);need(value['schema']=='bagaev-component-source/1','FORM_PROFILE');p=value['program'];m=value['component']
 shape(p,['schema','records','lists','variants','entry','functions']);need(p['schema']=='bagaev-typed-record/10' and p['lists']=={} and p['variants']=={},'FORM_PROFILE')
 shape(m,['name','operation','state_type','request_type','revision_type','entry','identity_binding','revision_binding','replace_fields']);shape(m['identity_binding'],['state','request']);need(p['entry']==m['entry'],'FORM_PROFILE')
 need(type(p['records'])is dict and type(p['functions'])is dict and type(m['replace_fields'])is list and m['replace_fields'],'FORM_PROFILE')
 for n,fields in p['records'].items():
  ident(n);need(type(fields)is dict,'FORM_PROFILE')
  for k,v in fields.items():ident(k);ident(v)
 def expr(x):
  need(type(x)is list and x,'FORM_PROFILE');op=x[0]
  if op=='arg' and len(x)==2:return ident(x[1])
  if op=='field' and len(x)==3:
   need(type(x[1])is list and x[1] and x[1][0] in ('arg','field'),'FORM_PROFILE');return expr(x[1])+'.'+ident(x[2])
  if op=='list.unique' and len(x)==2:return 'list.unique('+expr(x[1])+')'
  if op=='call' and len(x)>=2:return ident(x[1])+'('+', '.join(expr(a) for a in x[2:])+')'
  if op=='record' and len(x)>=2:
   name=ident(x[1]);need(name in p['records'],'FORM_PROFILE');fields=sorted(p['records'][name]);need(len(x)==len(fields)+2,'FORM_PROFILE');return name+' { '+', '.join(k+': '+expr(a) for k,a in zip(fields,x[2:]))+' }'
  raise FormError('FORM_PROFILE')
 lines=['bagaev component-form/1;','component '+ident(m['name'])+' operation '+ident(m['operation'])+' {']
 for n in sorted(p['records']):lines.append('  record '+n+' { '+', '.join(k+': '+p['records'][n][k] for k in sorted(p['records'][n]))+' };')
 lines+=['','  state '+ident(m['state_type'])+' identity '+ident(m['identity_binding']['state'])+';','  request '+ident(m['request_type'])+' identity '+ident(m['identity_binding']['request'])+' revision '+ident(m['revision_binding'])+': '+ident(m['revision_type'])+';','  replace '+', '.join(ident(x) for x in m['replace_fields'])+';','  entry '+ident(m['entry'])+';','']
 for n in sorted(p['functions']):
  ident(n);f=p['functions'][n];shape(f,['params','result','body']);need(type(f['params'])is list,'FORM_PROFILE');params=[]
  for pair in f['params']:need(type(pair)is list and len(pair)==2,'FORM_PROFILE');params.append(ident(pair[0])+': '+ident(pair[1]))
  lines.append('  fn '+n+'('+', '.join(params)+') -> '+ident(f['result'])+' = '+expr(f['body'])+';')
 lines.append('}');out=('\n'.join(lines)+'\n').encode();need(len(out)<=BYTE_LIMIT,'FORM_BOUNDS');return out
