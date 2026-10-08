"""Data-only readable record-form/5 over the separately selected typed-record/11 subset."""
import json,re
import bagaev_component_record_list_form as prior
old=prior.old
FormError=prior.FormError;need=prior.need;bounded=prior.bounded
TOKEN=prior.TOKEN;RESERVED=prior.RESERVED|{'omit_none'};INTRINSICS={**prior.INTRINSICS,'none.int':0,'some.int':1,'option.is_some':1,'option.or':2,'json.kind':1,'json.len':1,'json.int':1,'json.is_text':1,'json.at':2,'json.text_or':2,'json.field':2,'record.field':2,'text.byte_at':2,'int.eq':2,'int.le':2,'bool.not':1,'bool.and':2,'bool.or':2}
class Reader(prior.Reader):
 def __init__(self,source):
  need(type(source) in (str,bytes),'FORM_SYNTAX')
  try:raw=source.encode('utf8') if type(source)is str else source;text=raw.decode('utf8')
  except UnicodeError:raise FormError('FORM_SYNTAX') from None
  need(len(raw)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(not text.startswith('\ufeff'))
  h=re.match(r'\A[ \t\r\n]*bagaev[ \t\r\n]+record-form/([A-Za-z0-9_]+)[ \t\r\n]*;',text);need(h is not None);need(h[1]=='5','FORM_VERSION');pos=h.end();self.tokens=[]
  while pos<len(text):
   if text[pos] in old.WS:pos+=1;continue
   m=TOKEN.match(text,pos);need(m is not None);self.tokens.append(m[0]);need(len(self.tokens)<=old.TOKEN_LIMIT,'FORM_BOUNDS');pos=m.end()
  self.pos=0;self.records={};self.functions={};self.variants={};self.clauses={};self.lists={}
 def ident(self):
  value=super().ident();need(value!='omit_none');return value
 def field_type(self):
  value=self.ident()
  if self.peek()=='omit_none':
   self.take();need(value=='OptionInt64','FORM_PROFILE');return {'type':'OptionInt64','omit_none':True}
  return value
 def atom(self,depth):
  if self.pos+3<len(self.tokens) and self.tokens[self.pos+1]=='(' and self.tokens[self.pos+3]==':':
   need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');name=self.ident();self.take('(');args={}
   while True:
    key=self.ident();need(key not in args,'FORM_DUPLICATE');self.take(':');args[key]=self.expression(depth+1);need(len(args)<=8,'FORM_BOUNDS')
    if self.peek()!=',':break
    self.take(',')
   self.take(')');return ('namedcall',name,args)
  if self.tokens[self.pos:self.pos+4]==['records','.','list','(']:
   need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');self.take();self.take();self.take();self.take();name=self.ident();values=[]
   while self.peek()==',':
    self.take();values.append(self.expression(depth+1));need(len(values)<=16,'FORM_BOUNDS')
   self.take(')');return ('recordlist',name,values)
  if self.pos+3<len(self.tokens) and self.tokens[self.pos+1]=='.' and self.tokens[self.pos+3]=='(':
   operation=self.tokens[self.pos]+'.'+self.tokens[self.pos+2]
   if operation in INTRINSICS and operation not in prior.INTRINSICS:
    need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');self.take();self.take('.');self.take();self.take('(');args=[]
    if self.peek()!=')':
     while True:
      args.append(self.expression(depth+1));need(len(args)<=2)
      if self.peek()!=',':break
      self.take(',')
    self.take(')');need(len(args)==INTRINSICS[operation]);return ('builtin',{'int.eq':'eq','int.le':'le','bool.not':'not'}.get(operation,operation),args)
  return super().atom(depth)
 def lower(self,node,scope=frozenset(),depth=1):
  if node[0]=='namedcall':
   need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');name=node[1];need(name in self.functions,'FORM_REFERENCE');params=[p[0] for p in self.functions[name]['params']]
   need(len(set(params))==len(params),'FORM_DUPLICATE');need(set(node[2])==set(params),'FORM_ARGUMENTS')
   return ['call',name,*[self.lower(node[2][p],scope,depth+1) for p in params]]
  if node[0]=='builtin' and node[1] in ('bool.and','bool.or'):
   need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');args=node[2];need(len(args)==2,'FORM_PROFILE');child=lambda x:self.lower(x,scope,depth+1)
   left=child(args[0]);right=child(args[1]);literal=child(('bool',node[1]=='bool.or'))
   return ['if',left,right,literal] if node[1]=='bool.and' else ['if',left,literal,right]
  if node[0]=='builtin' and node[1] in ('json.field','record.field'):
   need(depth<=old.DEPTH_LIMIT,'FORM_BOUNDS');args=node[2];need(len(args)==2 and args[1][0]=='text','FORM_PROFILE');key=args[1][1];need(len(key.encode('utf8'))<=64,'FORM_BOUNDS');return ['field' if node[1]=='record.field' else 'json.field',self.lower(args[0],scope,depth+1),key]
  return super().lower(node,scope,depth)
 def read(self):
  self.take('program');self.take('{');entry=None
  while self.peek()!='}':
   kind=self.take()
   if kind in ('record','variant'):
    n=self.ident();need(n not in self.records and n not in self.variants and n not in self.lists,'FORM_DUPLICATE');fields=self.fields(self.field_type if kind=='record' else self.ident);(self.records if kind=='record' else self.variants)[n]=fields
   elif kind=='list':
    n=self.ident();need(n not in self.records and n not in self.variants and n not in self.lists,'FORM_DUPLICATE');self.take('of');element=self.ident();self.take('capacity');token=self.take();need(re.fullmatch(r'[0-9]+',token) is not None);need(len(token)<=2 and int(token)<=16,'FORM_BOUNDS');self.lists[n]={'element':element,'capacity':int(token)}
   elif kind=='fn':
    n=self.ident();need(n not in self.functions,'FORM_DUPLICATE');self.take('(');params=[]
    if self.peek()!=')':
     while True:
      p=self.ident();self.take(':');params.append([p,self.ident()])
      if self.peek()!=',':break
      self.take(',')
    self.take(')');self.take('->');result=self.ident();self.take('=');self.functions[n]={'params':params,'result':result,'body':self.expression()}
   elif kind=='entry':
    need(entry is None,'FORM_DUPLICATE');entry=self.ident()
   else:need(False)
   self.take(';')
  self.take('}');need(self.peek() is None);need(entry is not None,'FORM_SHAPE')
  for f in self.functions.values():f['body']=self.lower(f['body'])
  result={'schema':'bagaev-typed-record/11','records':self.records,'lists':self.lists,'variants':self.variants,'entry':entry,'functions':self.functions}
  bounded(result);return result
def decode(source):
 try:return Reader(source).read()
 except RecursionError:raise FormError('FORM_BOUNDS') from None
def encode(value):
 return _encode(value,False)
def encode_named(value):
 return _encode(value,True)
def _encode(value,named_calls):
 bounded(value)
 def shape(v,keys):need(type(v)is dict and set(v)==set(keys),'FORM_PROFILE')
 def ident(v):need(type(v)is str and old.IDENT.fullmatch(v) is not None and v not in RESERVED,'FORM_PROFILE');return v
 p=value;shape(p,['schema','records','lists','variants','entry','functions']);need(p['schema']=='bagaev-typed-record/11','FORM_PROFILE')
 need(all(type(p[k])is dict for k in ['records','lists','variants','functions']),'FORM_PROFILE');need(not(set(p['records'])&set(p['variants'])),'FORM_PROFILE')
 need(not(set(p['lists'])&(set(p['records'])|set(p['variants']))),'FORM_PROFILE')
 for name,d in p['lists'].items():
  ident(name);shape(d,['element','capacity']);ident(d['element']);need(type(d['capacity'])is int and 0<=d['capacity']<=16,'FORM_PROFILE')
 for defs in (p['records'],p['variants']):
  for n,fields in defs.items():
   ident(n);need(type(fields)is dict,'FORM_PROFILE')
   for k,v in fields.items():
    ident(k)
    if type(v)is dict:
     need(defs is p['records'],'FORM_PROFILE');shape(v,['type','omit_none']);need(v['type']=='OptionInt64' and v['omit_none'] is True,'FORM_PROFILE')
    else:ident(v)
 def operand(x):
  rendered=expr(x)
  return '('+rendered+')' if x[0] in ('loop','if','let','match') else rendered
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
  if op in ('add','sub','mul') and len(x)==3:return '('+operand(x[1])+' '+{'add':'+','sub':'-','mul':'*'}[op]+' '+operand(x[2])+')'
  if op=='json.field':
   need(len(x)==3 and type(x[2])is str and not any(0xd800<=ord(c)<=0xdfff for c in x[2]),'FORM_PROFILE');need(len(x[2].encode('utf8'))<=64,'FORM_BOUNDS');return 'json.field('+expr(x[1])+', '+json.dumps(x[2],ensure_ascii=False)+')'
  if op in ('eq','le','not'):
   need(len(x)==(2 if op=='not' else 3),'FORM_PROFILE');return {'eq':'int.eq','le':'int.le','not':'bool.not'}[op]+'('+', '.join(expr(a) for a in x[1:])+')'
  if op in INTRINSICS:
   arity=INTRINSICS[op];need((len(x)-1<=64) if arity is None else len(x)==arity+1,'FORM_PROFILE');return op+'('+', '.join(expr(a) for a in x[1:])+')'
  if op=='match' and len(x)==3:
   need(type(x[2])is list,'FORM_PROFILE');arms=[]
   for arm in x[2]:
    need(type(arm)is list and len(arm)==3,'FORM_PROFILE');arms.append(ident(arm[0])+'('+ident(arm[1])+'): '+expr(arm[2])+';')
   return 'match ('+expr(x[1])+') { '+' '.join(arms)+' }'
  if op=='let' and len(x)==4:return 'let '+ident(x[1])+' = ('+expr(x[2])+') in ('+expr(x[3])+')'
  if op=='field' and len(x)==3:return 'record.field('+expr(x[1])+', '+json.dumps(ident(x[2]))+')'
  if op=='list.unique' and len(x)==2:return 'list.unique('+expr(x[1])+')'
  if op=='call' and len(x)>=2:
   name=ident(x[1])
   if not named_calls:return name+'('+', '.join(expr(a) for a in x[2:])+')'
   need(name in p['functions'],'FORM_PROFILE');callee=p['functions'][name];shape(callee,['params','result','body']);params=callee['params'];need(type(params)is list and len(params)<=8,'FORM_PROFILE');labels=[]
   for pair in params:need(type(pair)is list and len(pair)==2,'FORM_PROFILE');labels.append(ident(pair[0]));ident(pair[1])
   need(len(set(labels))==len(labels) and len(x)==len(labels)+2,'FORM_PROFILE')
   return name+'('+', '.join(label+': '+expr(a) for label,a in zip(labels,x[2:]))+')'
  if op=='lt' and len(x)==3:return '('+operand(x[1])+' < '+operand(x[2])+')'
  if op=='if' and len(x)==4:return 'if ('+expr(x[1])+') then ('+expr(x[2])+') else ('+expr(x[3])+')'
  if op=='variant' and len(x)==4:
   n=ident(x[1]);alt=ident(x[2]);need(n+'.'+alt not in INTRINSICS,'FORM_PROFILE');need(n in p['variants'] and alt in p['variants'][n],'FORM_PROFILE');return n+'.'+alt+'('+expr(x[3])+')'
  if op=='record' and len(x)>=2:
   n=ident(x[1]);need(n in p['records'],'FORM_PROFILE');fields=sorted(p['records'][n]);need(len(x)==len(fields)+2,'FORM_PROFILE');return n+' { '+', '.join(k+': '+expr(a) for k,a in zip(fields,x[2:]))+' }'
  raise FormError('FORM_PROFILE')
 lines=['bagaev record-form/5;','program {']
 for kind,defs in [('record',p['records']),('variant',p['variants'])]:
  for n in sorted(defs):lines.append('  '+kind+' '+n+' { '+', '.join(k+': '+('OptionInt64 omit_none' if type(defs[n][k])is dict else defs[n][k]) for k in sorted(defs[n]))+' };')
 for name,d in sorted(p['lists'].items()):lines.append('  list '+name+' of '+d['element']+' capacity '+str(d['capacity'])+';')
 lines+=['','  entry '+ident(p['entry'])+';','']
 for n in sorted(p['functions']):
  f=p['functions'][n];shape(f,['params','result','body']);need(type(f['params'])is list,'FORM_PROFILE');params=[]
  for pair in f['params']:need(type(pair)is list and len(pair)==2,'FORM_PROFILE');params.append(ident(pair[0])+': '+ident(pair[1]))
  lines.append('  fn '+ident(n)+'('+', '.join(params)+') -> '+ident(f['result'])+' = '+expr(f['body'])+';')
 lines.append('}');out=('\n'.join(lines)+'\n').encode();need(len(out)<=old.BYTE_LIMIT,'FORM_BOUNDS');need(json.dumps(decode(out),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)==json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False),'FORM_PROFILE');return out
