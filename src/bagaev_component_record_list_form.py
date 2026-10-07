"""Explicit component-form/7 representation over unchanged component-source/2."""
import json,re
import bagaev_component_form as old
import bagaev_component_outcome_form as prior
FormError=old.FormError;need=old.need;bounded=old.bounded
RESERVED=prior.RESERVED|{'let','in','match','fold','with','list','of','capacity'}
TOKEN=re.compile(prior.STRING+r'|(?:0|[1-9][0-9]*)|[A-Za-z][A-Za-z0-9_]*|->|[{}(),:;=.<+*\-]',re.ASCII)
INTRINSICS = {'list.text': None, 'list.len': 1, 'list.at': 2, 'list.contains': 2, 'list.increasing': 1, 'list.unique': 1, 'list.push': 2, 'text.bytes': 1, 'text.scalars': 1, 'text.eq': 2, 'text.lt': 2, 'records.list': None, 'records.len': 1, 'records.at': 2, 'records.push': 2}
class Reader(prior.Reader):
 def __init__(self,source):
  need(type(source) in (str,bytes),'FORM_SYNTAX')
  try:raw=source.encode('utf8') if type(source)is str else source;text=raw.decode('utf8')
  except UnicodeError:raise FormError('FORM_SYNTAX') from None
  need(len(raw)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(not text.startswith('\ufeff'))
  h=re.match(r'\A[ \t\r\n]*bagaev[ \t\r\n]+component-form/([A-Za-z0-9_]+)[ \t\r\n]*;',text);need(h is not None);need(h[1]=='7','FORM_VERSION');pos=h.end();self.tokens=[]
  while pos<len(text):
   if text[pos] in old.WS:pos+=1;continue
   m=TOKEN.match(text,pos);need(m is not None);self.tokens.append(m[0]);need(len(self.tokens)<=old.TOKEN_LIMIT,'FORM_BOUNDS');pos=m.end()
  self.pos=0;self.records={};self.functions={};self.variants={};self.clauses={};self.lists={}
 def read(self):
  self.take('component');name=self.ident();self.take('operation');operation=self.ident();self.take('{')
  while self.peek()!='}':
   kind=self.take()
   if kind in ('record','variant'):
    n=self.ident();need(n not in self.records and n not in self.variants and n not in self.lists,'FORM_DUPLICATE');fields=self.fields(self.ident);(self.records if kind=='record' else self.variants)[n]=fields
   elif kind=='list':
    n=self.ident();need(n not in self.records and n not in self.variants and n not in self.lists,'FORM_DUPLICATE');self.take('of');element=self.ident();self.take('capacity');token=self.take();need(re.fullmatch(r'[0-9]+',token) is not None);need(len(token)==1 and int(token)<=4,'FORM_BOUNDS');self.lists[n]={'element':element,'capacity':int(token)}
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
  result={'schema':'bagaev-component-source/2','program':{'schema':'bagaev-typed-record/10','records':self.records,'lists':self.lists,'variants':self.variants,'entry':entry,'functions':self.functions},'component':{'name':name,'operation':operation,'state_type':state,'request_type':request,'revision_type':revision,'entry':entry,'identity_binding':{'state':identity,'request':req_id},'revision_binding':rev_field,'replace_fields':self.clauses['replace'],'outcome_type':outcome,'error_type':error}}
  bounded(result);return result
 def ident(self):
  value=old.Reader.ident(self);need(value not in RESERVED);return value
 def expression(self,depth=1):
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS')
  if self.peek()=='fold':
   self.take();self.take('(');token=self.take();need(re.fullmatch(r'[0-9]+',token) is not None);need(len(token)<=4 and int(token)<=1024,'FORM_BOUNDS');count=int(token);self.take(',');initial=self.expression(depth+1);self.take(')');self.take('with');self.take('(');index=self.ident();self.take(',');acc=self.ident();need(index!=acc,'FORM_DUPLICATE');self.take(')');self.take('in');body=self.expression(depth+1);return ('fold',count,index,acc,initial,body)
  if self.peek()=='match':
   self.take();self.take('(');value=self.expression(depth+1);self.take(')');self.take('{');arms=[];names=set()
   while self.peek()!='}':
    name=self.ident();need(name not in names,'FORM_DUPLICATE');names.add(name);self.take('(');binder=self.ident();self.take(')');self.take(':');body=self.expression(depth+1);self.take(';');arms.append((name,binder,body))
   self.take('}');return ('match',value,arms)
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
  if self.tokens[self.pos:self.pos+4]==['records','.','list','(']:
   need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');self.take();self.take();self.take();self.take();name=self.ident();values=[]
   while self.peek()==',':
    self.take();values.append(self.expression(depth+1));need(len(values)<=4,'FORM_BOUNDS')
   self.take(')');return ('recordlist',name,values)
  if self.pos+3<len(self.tokens) and self.tokens[self.pos+1]=='.' and self.tokens[self.pos+3]=='(':
   operation=self.tokens[self.pos]+'.'+self.tokens[self.pos+2]
   if operation in INTRINSICS:
    need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');self.take();self.take('.');self.take();self.take('(');args=[]
    if self.peek()!=')':
     while True:
      args.append(self.expression(depth+1))
      if operation=='list.text':need(len(args)<=64,'FORM_BOUNDS')
      if self.peek()!=',':break
      self.take(',')
    self.take(')');arity=INTRINSICS[operation];need(arity is None or len(args)==arity);return ('builtin',operation,args)
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS')
  if self.peek()=='-':
   self.take();token=self.take();need(re.fullmatch(r'[0-9]+',token) is not None);need(len(token)<=19,'FORM_LITERAL');value=-int(token);need(-(1<<63)<=value<(1<<63),'FORM_LITERAL');return ('int',value)
  return super().atom(depth)
 def lower(self,node,scope=frozenset(),depth=1):
  need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');kind=node[0]
  child=lambda x:self.lower(x,scope,depth+1)
  if kind in ('int','text','bool'):return list(node)
  if kind=='arg':return ['use' if node[1] in scope else 'arg',node[1]]
  if kind=='recordlist':
   need(node[1] in self.lists,'FORM_REFERENCE');need(len(node[2])<=self.lists[node[1]]['capacity'],'FORM_BOUNDS');return ['records.list',node[1],*[child(x) for x in node[2]]]
  if kind=='fold':return ['loop',node[1],node[2],node[3],child(node[4]),self.lower(node[5],scope|{node[2],node[3]},depth+1)]
  if kind=='builtin':return [node[1],*[child(x) for x in node[2]]]
  if kind=='match':return ['match',child(node[1]),[[name,binder,self.lower(body,scope|{binder},depth+1)] for name,binder,body in node[2]]]
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
 shape(p,['schema','records','lists','variants','entry','functions']);need(p['schema']=='bagaev-typed-record/10' and type(p['lists'])is dict,'FORM_PROFILE')
 shape(m,['name','operation','state_type','request_type','revision_type','entry','identity_binding','revision_binding','replace_fields','outcome_type','error_type']);shape(m['identity_binding'],['state','request']);need(p['entry']==m['entry'],'FORM_PROFILE')
 need(type(p['records'])is dict and type(p['variants'])is dict and type(p['functions'])is dict and type(m['replace_fields'])is list and m['replace_fields'],'FORM_PROFILE');need(not(set(p['records'])&set(p['variants'])),'FORM_PROFILE')
 need(not(set(p['lists'])&(set(p['records'])|set(p['variants']))),'FORM_PROFILE')
 for name,d in p['lists'].items():
  ident(name);shape(d,['element','capacity']);ident(d['element']);need(type(d['capacity'])is int and 0<=d['capacity']<=4,'FORM_PROFILE')
 for defs in (p['records'],p['variants']):
  for n,fields in defs.items():
   ident(n);need(type(fields)is dict,'FORM_PROFILE')
   for k,v in fields.items():ident(k);ident(v)
 def expr(x):
  need(type(x)is list and x,'FORM_PROFILE');op=x[0];need(type(op)is str,'FORM_PROFILE')
  if op=='records.list':
   need(len(x)>=2,'FORM_PROFILE');name=ident(x[1]);need(name in p['lists'] and len(x)-2<=p['lists'][name]['capacity'],'FORM_PROFILE');return 'records.list('+name+('' if len(x)==2 else ', '+', '.join(expr(a) for a in x[2:]))+')'
  if op=='loop' and len(x)==6:
   need(type(x[1])is int and 0<=x[1]<=1024,'FORM_PROFILE');index=ident(x[2]);acc=ident(x[3]);need(index!=acc,'FORM_PROFILE');return 'fold ('+str(x[1])+', ('+expr(x[4])+')) with ('+index+', '+acc+') in ('+expr(x[5])+')'
  if op=='int' and len(x)==2:need(type(x[1])is int and -(1<<63)<=x[1]<(1<<63),'FORM_PROFILE');return str(x[1])
  if op=='bool' and len(x)==2:need(type(x[1])is bool,'FORM_PROFILE');return 'true' if x[1] else 'false'
  if op=='text' and len(x)==2:need(type(x[1])is str and not any(0xd800<=ord(c)<=0xdfff for c in x[1]),'FORM_PROFILE');return json.dumps(x[1],ensure_ascii=False)
  if op in ('arg','use') and len(x)==2:return ident(x[1])
  if op in ('add','sub','mul') and len(x)==3:return '('+expr(x[1])+' '+{'add':'+','sub':'-','mul':'*'}[op]+' '+expr(x[2])+')'
  if op in INTRINSICS:
   arity=INTRINSICS[op];need((len(x)-1<=64) if arity is None else len(x)==arity+1,'FORM_PROFILE');return op+'('+', '.join(expr(a) for a in x[1:])+')'
  if op=='match' and len(x)==3:
   need(type(x[2])is list,'FORM_PROFILE');arms=[]
   for arm in x[2]:
    need(type(arm)is list and len(arm)==3,'FORM_PROFILE');arms.append(ident(arm[0])+'('+ident(arm[1])+'): '+expr(arm[2])+';')
   return 'match ('+expr(x[1])+') { '+' '.join(arms)+' }'
  if op=='let' and len(x)==4:return 'let '+ident(x[1])+' = ('+expr(x[2])+') in ('+expr(x[3])+')'
  if op=='field' and len(x)==3:need(type(x[1])is list and x[1] and x[1][0] in ('arg','use','field'),'FORM_PROFILE');return expr(x[1])+'.'+ident(x[2])
  if op=='list.unique' and len(x)==2:return 'list.unique('+expr(x[1])+')'
  if op=='call' and len(x)>=2:return ident(x[1])+'('+', '.join(expr(a) for a in x[2:])+')'
  if op=='lt' and len(x)==3:return '('+expr(x[1])+' < '+expr(x[2])+')'
  if op=='if' and len(x)==4:return 'if ('+expr(x[1])+') then ('+expr(x[2])+') else ('+expr(x[3])+')'
  if op=='variant' and len(x)==4:
   n=ident(x[1]);alt=ident(x[2]);need(n+'.'+alt not in INTRINSICS,'FORM_PROFILE');need(n in p['variants'] and alt in p['variants'][n],'FORM_PROFILE');return n+'.'+alt+'('+expr(x[3])+')'
  if op=='record' and len(x)>=2:
   n=ident(x[1]);need(n in p['records'],'FORM_PROFILE');fields=sorted(p['records'][n]);need(len(x)==len(fields)+2,'FORM_PROFILE');return n+' { '+', '.join(k+': '+expr(a) for k,a in zip(fields,x[2:]))+' }'
  raise FormError('FORM_PROFILE')
 lines=['bagaev component-form/7;','component '+ident(m['name'])+' operation '+ident(m['operation'])+' {']
 for kind,defs in [('record',p['records']),('variant',p['variants'])]:
  for n in sorted(defs):lines.append('  '+kind+' '+n+' { '+', '.join(k+': '+defs[n][k] for k in sorted(defs[n]))+' };')
 for name,d in sorted(p['lists'].items()):lines.append('  list '+name+' of '+d['element']+' capacity '+str(d['capacity'])+';')
 lines+=['','  state '+ident(m['state_type'])+' identity '+ident(m['identity_binding']['state'])+';','  request '+ident(m['request_type'])+' identity '+ident(m['identity_binding']['request'])+' revision '+ident(m['revision_binding'])+': '+ident(m['revision_type'])+';','  replace '+', '.join(ident(x) for x in m['replace_fields'])+';','  outcome '+ident(m['outcome_type'])+' error '+ident(m['error_type'])+';','  entry '+ident(m['entry'])+';','']
 for n in sorted(p['functions']):
  f=p['functions'][n];shape(f,['params','result','body']);need(type(f['params'])is list,'FORM_PROFILE');params=[]
  for pair in f['params']:need(type(pair)is list and len(pair)==2,'FORM_PROFILE');params.append(ident(pair[0])+': '+ident(pair[1]))
  lines.append('  fn '+ident(n)+'('+', '.join(params)+') -> '+ident(f['result'])+' = '+expr(f['body'])+';')
 lines.append('}');out=('\n'.join(lines)+'\n').encode();need(len(out)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(json.dumps(decode(out),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)==json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False),'FORM_PROFILE');return out
